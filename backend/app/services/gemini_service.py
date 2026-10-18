import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from backend.app.config import settings
from backend.app.database.falkordb_client import get_user_memory_context, add_memory_fact
from backend.app.database.supabase_client import get_user_profile, get_recent_recovery_logs, get_recent_workouts, get_meals_by_date
from datetime import date

logger = logging.getLogger(__name__)

_client: Optional[genai.Client] = None

def get_gemini_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview"]

SYSTEM_PROMPTS = {
    "home": """You are LifeSync AI, a world-class personal wellness and human performance assistant.
You maintain a grounded, intentional, highly knowledgeable tone—concise, precise, and supportive.
Avoid corporate jargon, fluffy generic disclaimers, or excessive enthusiasm. Provide clear, actionable advice across workouts, nutrition, recovery, and holistic daily balance.
You have real-time access to the user's connected memory graph, biometric recovery logs, training history, and macro nutrition data.""",

    "workout": """You are the LifeSync AI Strength & Conditioning Specialist.
Your focus is athletic performance, progressive overload, biomechanics, exercise selection, and training programming.
Give direct, structured, data-informed feedback on exercise technique, set/rep schemes, and recovery between sessions. Keep responses practical and focused.""",

    "nutrition": """You are the LifeSync AI Performance Nutritionist.
Your focus is macronutrient adherence, energy balance, meal timing, micronutrient density, and metabolic fueling.
Provide exact macro calculations, food recommendations based on real nutritional science, and practical meal structuring without fads or dogmatism.""",

    "recovery": """You are the LifeSync AI Recovery & Sleep Scientist.
Your focus is autonomic nervous system balance, sleep architecture, heart rate variability, systemic fatigue, and restorative protocols (hydration, mobility, active rest).
Help the user interpret their recovery score and provide concrete recommendations to optimize next-day readiness."""
}

def build_context_block(workspace: str, user_id: str = "default_user") -> str:
    """Gather live data from FalkorDB and Supabase to ground the AI's response."""
    lines = []
    
    # 1. User Profile
    profile = get_user_profile(user_id) or {
        "display_name": "Ashwin",
        "calorie_target": 2200,
        "protein_target": 160,
        "carbs_target": 220,
        "fat_target": 65,
        "water_target_liters": 3.0,
        "sleep_target_hours": 8.0,
        "primary_goal": "Strength & Lean Muscle"
    }
    lines.append(f"USER PROFILE: Name={profile.get('display_name')}, Goal={profile.get('primary_goal')}, Calorie Target={profile.get('calorie_target')}kcal, Protein Target={profile.get('protein_target')}g, Sleep Target={profile.get('sleep_target_hours')}h.")
    
    # 2. FalkorDB Memory Graph Context
    memories = get_user_memory_context(user_id, limit=8)
    if memories:
        mem_strs = [f"- [{m.get('label')}] {m.get('content')}" for m in memories if m.get('content')]
        if mem_strs:
            lines.append("PERSISTENT GRAPH MEMORY:\n" + "\n".join(mem_strs))

    # 3. Today's Recovery State
    today_str = date.today().isoformat()
    recent_recovery = get_recent_recovery_logs(limit=3, user_id=user_id)
    if recent_recovery:
        latest = recent_recovery[0]
        lines.append(f"LATEST RECOVERY LOG ({latest.get('date')}): Score={latest.get('recovery_score')}/100, Sleep={latest.get('sleep_hours')}h (Quality: {latest.get('sleep_quality')}), Resting HR={latest.get('resting_hr')}bpm, Hydration={latest.get('hydration_liters')}L, Soreness={latest.get('soreness_level')}/10.")

    # 4. Today's Meals & Nutrition
    meals = get_meals_by_date(today_str, user_id=user_id)
    if meals:
        total_cals = sum(float(m.get("calories", 0)) for m in meals)
        total_protein = sum(float(m.get("protein", 0)) for m in meals)
        total_carbs = sum(float(m.get("carbs", 0)) for m in meals)
        total_fat = sum(float(m.get("fat", 0)) for m in meals)
        lines.append(f"TODAY'S NUTRITION INTAKE: {len(meals)} meals logged. Total Calories: {round(total_cals)}kcal, Protein: {round(total_protein, 1)}g, Carbs: {round(total_carbs, 1)}g, Fat: {round(total_fat, 1)}g.")

    # 5. Recent Workouts
    recent_workouts = get_recent_workouts(limit=2, user_id=user_id)
    if recent_workouts:
        w_strs = []
        for w in recent_workouts:
            ex_count = len(w.get("workout_exercises", []))
            w_strs.append(f"- {w.get('title')} ({w.get('category')}, {w.get('duration_minutes')} min, {ex_count} exercises)")
        lines.append("RECENT WORKOUTS:\n" + "\n".join(w_strs))

    return "\n\n".join(lines)

from backend.app.memory.memory_manager import MemoryManager

async def generate_chat_response(
    message: str,
    workspace: str = "home",
    history: Optional[List[Dict[str, str]]] = None,
    user_id: str = "default_user"
) -> Dict[str, Any]:
    """Generate workspace-aware AI response grounded in persistent cross-agent memory."""
    client = get_gemini_client()
    base_prompt = SYSTEM_PROMPTS.get(workspace, SYSTEM_PROMPTS["home"])
    
    # 1. Retrieve hybrid semantic + graph + biometric context
    context_data = MemoryManager.get_relevant_context(user_id, workspace, message)
    
    full_instruction = f"""{base_prompt}

CURRENT LIVE CONTEXT & PERSISTENT MEMORY:
{context_data}

Instructions:
- Address the user's question directly with high clarity.
- Explicitly acknowledge their confirmed goals, injuries, or past activities when relevant.
- Distinguish confirmed user facts from suggestions or inferences.
- Keep formatting clean using GitHub markdown (bullet points, bold text).
"""

    contents = []
    # Include recent history (up to last 6 messages)
    if history:
        for h in history[-6:]:
            role = "user" if h.get("role") in ["user", "human"] else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=h.get("content", ""))]
            ))

    # Append current message
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)]
    ))

    response = None
    used_model = MODEL_NAME
    last_err = None

    for m in [MODEL_NAME] + FALLBACK_MODELS:
        try:
            response = client.models.generate_content(
                model=m,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=full_instruction,
                    temperature=0.7,
                    max_output_tokens=1200
                )
            )
            if response and response.text:
                used_model = m
                break
        except Exception as me:
            last_err = me
            logger.warning(f"Gemini model {m} call failed ({me}). Trying next fallback model...")
            continue

    if response and response.text:
        reply_text = response.text
        # 2. Extract and persist confirmed facts from user message
        try:
            MemoryManager.process_incoming_user_message(user_id=user_id, message=message)
        except Exception as pe:
            logger.warning(f"Error persisting extracted facts: {pe}")

        return {
            "reply": reply_text,
            "workspace": workspace,
            "model": used_model
        }
    else:
        logger.error(f"All Gemini models exhausted. Last error: {last_err}")
        return {
            "reply": "LifeSync AI is currently operating with high model traffic. Your persistent data is intact.",
            "workspace": workspace,
            "model": used_model,
            "error": True
        }
