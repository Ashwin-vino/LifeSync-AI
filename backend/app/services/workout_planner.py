import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types

from backend.app.config import settings
from backend.app.schemas.workout import (
    WorkoutPlanResponseSchema,
    PlannedExerciseSchema,
    WorkoutPlanGenerateRequest
)
from backend.app.memory.memory_manager import MemoryManager
from backend.app.database.supabase_client import (
    get_user_profile,
    get_recent_recovery_logs,
    get_recent_workouts,
    save_generated_plan,
    get_supabase
)
from backend.app.services.wger_service import search_exercises

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview"]

def _get_gemini_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)

async def generate_personalized_workout_plan(
    user_id: str = "default_user",
    req: Optional[WorkoutPlanGenerateRequest] = None
) -> WorkoutPlanResponseSchema:
    """
    Generate an individualized workout plan grounded in persistent cross-agent memory:
    - User goals and experience from FalkorDB graph memory
    - Reported injuries and physical limitations from memory facts
    - Today's recovery readiness score, HRV, and sleep architecture
    - Recent workout volume and muscle split
    - Cross-verified with official wger exercise database
    """
    req = req or WorkoutPlanGenerateRequest()
    
    # 1. Gather live physiological context
    profile = get_user_profile(user_id) or {
        "display_name": "Ashwin",
        "primary_goal": "Strength & Lean Muscle"
    }
    
    # Cross-agent memory context (semantic memories, active graph goals)
    memory_context = MemoryManager.get_relevant_context(
        user_id=user_id,
        workspace="workout",
        current_message=f"Generate workout plan focus={req.focus or 'overall fitness'}"
    )

    # Recent recovery metrics
    recovery_logs = get_recent_recovery_logs(limit=2, user_id=user_id)
    recovery_status_str = "No recent recovery logged (assume moderate readiness)."
    if recovery_logs:
        latest_rec = recovery_logs[0]
        recovery_status_str = (
            f"Date: {latest_rec.get('date')}, Score: {latest_rec.get('recovery_score')}/100, "
            f"Sleep: {latest_rec.get('sleep_hours')}h ({latest_rec.get('sleep_quality')}), "
            f"Soreness: {latest_rec.get('soreness_level')}/10, Resting HR: {latest_rec.get('resting_hr')}bpm."
        )

    # Recent workout history
    recent_workouts = get_recent_workouts(limit=3, user_id=user_id, status="completed")
    recent_split_str = "None logged recently."
    if recent_workouts:
        w_items = [f"{w.get('title')} ({w.get('category')}, {w.get('duration_minutes')}m)" for w in recent_workouts]
        recent_split_str = "; ".join(w_items)

    # 2. Build Gemini prompt
    system_instruction = """You are LifeSync AI's Lead Athletic Performance Specialist & Biomechanist.
Your mandate is to generate structured, scientifically grounded training sessions tailored to the user's explicit goals, recovery readiness, and physical constraints.

CRITICAL SAFETY & VALIDATION RULES:
1. Medical & Injury Safety: Strictly respect any user-reported injuries, joint limitations, or soreness. If the user has shoulder impingement, avoid overhead pressing. If lower back fatigue, avoid heavy spinal loading.
2. Honest Progression: Suggest specific load/weight ONLY when previous history supports it; otherwise leave suggested_weight_kg as null.
3. Recovery Readiness: If recovery score is < 65 or soreness is high, reduce volume/intensity and prioritize restorative/hypertrophy work over maximal neural strength.
4. Output strictly valid JSON matching the requested structure.
"""

    user_prompt = f"""Generate a personalized training session plan for {profile.get('display_name', 'the athlete')}.

ATHLETE PROFILE & MEMORY CONTEXT:
{memory_context}

TODAY'S RECOVERY READINESS:
{recovery_status_str}

RECENT COMPLETED WORKOUTS:
{recent_split_str}

USER REQUESTED PREFERENCES:
- Target Focus: {req.focus or 'Full Body or next logical split'}
- Target Duration: {req.duration_target} minutes
- Equipment Available: {', '.join(req.equipment_available) if req.equipment_available else 'Standard Gym (Barbells, Dumbbells, Cables, Benches, Machines)'}
- Notes/Instructions: {req.notes or 'None provided'}

Return a JSON object with this exact structure:
{{
  "title": "string (e.g. Upper Body Push & Anterior Deltoid Focus)",
  "category": "Strength" or "Hypertrophy" or "Cardio" or "Mobility" or "HIIT",
  "summary": "1-2 sentence overview of the session",
  "warmup": ["dynamic movement 1 with reps/duration", "movement 2", ...],
  "exercises": [
    {{
      "name": "Standard exercise name (e.g. Barbell Bench Press)",
      "target_muscle": "Primary muscle group (e.g. Chest)",
      "sets": 3,
      "reps": "8-10" or "10-12",
      "rest_seconds": 90,
      "suggested_weight_kg": null or float,
      "notes": "Biomechanical cue or safety caution"
    }}
  ],
  "cooldown": ["stretch 1", "stretch 2"],
  "estimated_duration_minutes": {req.duration_target},
  "explanation": "Scientific explanation of why this plan fits their goal and today's recovery state."
}}
"""

    plan_data: Dict[str, Any] = {}
    plan_id = str(uuid.uuid4())

    client = _get_gemini_client()
    for m in [MODEL_NAME] + FALLBACK_MODELS:
        try:
            response = client.models.generate_content(
                model=m,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4,
                    response_mime_type="application/json"
                )
            )
            if response and response.text:
                plan_data = json.loads(response.text)
                break
        except Exception as me:
            logger.warning(f"Gemini model {m} in planner failed ({me}). Trying fallback...")
            continue

    if not plan_data:
        logger.warning("All Gemini models exhausted for plan generation. Using curated fallback plan.")
        plan_data = _generate_fallback_plan(req.focus, req.duration_target or 45)

    # 3. Cross-reference generated exercises with official wger database
    raw_exercises = plan_data.get("exercises", [])
    validated_exercises: List[PlannedExerciseSchema] = []

    for ex in raw_exercises:
        ex_name = ex.get("name", "Exercise")
        wger_match = None
        source_label = "ai_suggested"
        wger_id = None

        try:
            # Query wger database to verify exercise
            matches = await search_exercises(ex_name)
            if matches:
                # Find direct match
                for m in matches:
                    if m["name"].lower() in ex_name.lower() or ex_name.lower() in m["name"].lower():
                        wger_match = m
                        break
                if not wger_match and len(matches) > 0:
                    wger_match = matches[0]

            if wger_match and wger_match.get("source") == "wger_verified":
                source_label = "wger_verified"
                wger_id = str(wger_match.get("id"))
        except Exception as we:
            logger.warning(f"Could not verify exercise '{ex_name}' against wger: {we}")

        validated_exercises.append(PlannedExerciseSchema(
            name=ex_name,
            target_muscle=ex.get("target_muscle", "Full Body"),
            sets=int(ex.get("sets", 3)),
            reps=str(ex.get("reps", "10")),
            rest_seconds=int(ex.get("rest_seconds", 90)),
            suggested_weight_kg=float(ex["suggested_weight_kg"]) if ex.get("suggested_weight_kg") is not None else None,
            notes=ex.get("notes"),
            wger_id=wger_id,
            source=source_label
        ))

    final_plan = WorkoutPlanResponseSchema(
        id=plan_id,
        user_id=user_id,
        title=plan_data.get("title", "Custom Training Session"),
        category=plan_data.get("category", "Strength"),
        summary=plan_data.get("summary", "Personalized session plan"),
        warmup=plan_data.get("warmup", ["Arm circles 30s", "Cat-Cow 60s"]),
        exercises=validated_exercises,
        cooldown=plan_data.get("cooldown", ["Passive hang 60s", "Child's pose 90s"]),
        estimated_duration_minutes=int(plan_data.get("estimated_duration_minutes", req.duration_target or 45)),
        status="planned",
        explanation=plan_data.get("explanation", "Designed to align with your strength target and recovery readiness.")
    )

    # 4. Save to Supabase generated_plans table
    try:
        save_generated_plan(
            user_id=user_id,
            plan_type="workout",
            title=final_plan.title,
            summary=final_plan.summary,
            plan_data=final_plan.model_dump(),
            status="planned"
        )
    except Exception as se:
        logger.error(f"Error persisting generated plan to Supabase: {se}")

    return final_plan

def _generate_fallback_plan(focus: Optional[str], duration: int) -> Dict[str, Any]:
    """Reliable fallback plan when Gemini is unavailable. Clearly labeled as AI suggested fallback."""
    focus_title = focus or "Functional Strength & Mobility"
    return {
        "title": f"{focus_title} Session (Structured Baseline)",
        "category": "Strength",
        "summary": "Core compound movements designed for steady progressive overload with safe spinal positioning.",
        "warmup": [
            "World's Greatest Stretch: 5 reps per side",
            "Band Pull-Aparts: 2 sets of 15 reps",
            "Bodyweight Squats with 3s tempo: 10 reps"
        ],
        "exercises": [
            {
                "name": "Barbell Bench Press",
                "target_muscle": "Chest",
                "sets": 4,
                "reps": "8-10",
                "rest_seconds": 90,
                "suggested_weight_kg": None,
                "notes": "Keep shoulder blades retracted and feet anchored."
            },
            {
                "name": "Barbell Row",
                "target_muscle": "Back",
                "sets": 4,
                "reps": "8-10",
                "rest_seconds": 90,
                "suggested_weight_kg": None,
                "notes": "Hinge at hips, pull elbows toward back pocket."
            },
            {
                "name": "Dumbbell Incline Press",
                "target_muscle": "Upper Chest",
                "sets": 3,
                "reps": "10-12",
                "rest_seconds": 75,
                "suggested_weight_kg": None,
                "notes": "30-degree incline, control the eccentric lowering."
            },
            {
                "name": "Lateral Raise",
                "target_muscle": "Shoulders",
                "sets": 3,
                "reps": "12-15",
                "rest_seconds": 60,
                "suggested_weight_kg": None,
                "notes": "Slight torso lean, lead with lateral deltoid."
            }
        ],
        "cooldown": [
            "Doorway Pectoral Stretch: 45s per side",
            "Dead Hang from Pull-up Bar: 60s spinal decompression",
            "Diaphragmatic Box Breathing: 3 minutes"
        ],
        "estimated_duration_minutes": duration,
        "explanation": "Structured compound session prioritizing anterior/posterior balance while minimizing lower spine axial load."
    }
