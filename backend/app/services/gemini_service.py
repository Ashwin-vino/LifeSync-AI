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

from backend.app.services.ai_style import (
    SYSTEM_PROMPTS,
    CORE_STYLE_INSTRUCTIONS,
    clean_ai_response,
    FRIENDLY_ERROR_FALLBACK,
)

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview"]

def build_context_block(workspace: str, user_id: str = "default_user") -> str:
    """Gather live data from FalkorDB and Supabase to ground the AI's response."""
    lines = []
    
    # 1. User Profile
    # 1. User Profile
    profile = get_user_profile(user_id)
    if profile and profile.get("primary_goal"):
        lines.append(f"USER PROFILE: Name={profile.get('display_name', 'User')}, Goal={profile.get('primary_goal')}, Calorie Target={profile.get('calorie_target', 2200)}kcal, Protein Target={profile.get('protein_target', 160)}g, Sleep Target={profile.get('sleep_target_hours', 8.0)}h.")
    elif profile:
        lines.append(f"USER PROFILE: Name={profile.get('display_name', 'User')}, Goal=Unspecified.")
    else:
        lines.append("USER PROFILE: New user. Primary fitness goal unspecified.")
    
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

CRITICAL RULES:
- Answer the user's actual question immediately in 1–4 short, natural sentences (prefer 30–80 words).
- Speak like a friendly, supportive fitness coach.
- Use simple, everyday English without corporate, medical, or academic jargon.
- Never say "To establish your baseline" or lecture about missing data.
- If profile info is missing, answer directly and ask at most ONE simple question naturally (e.g. "What's your main goal: building muscle, losing fat, or staying fit?").
- Use short bullet points ONLY if listing 2–3 actionable items.
- Never output internal reasoning, model names, or system tags.
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
                    temperature=0.6,
                    max_output_tokens=800,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
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
        candidate = response.candidates[0] if (response.candidates and len(response.candidates) > 0) else None
        finish_reason = getattr(candidate, "finish_reason", None)
        reply_text = clean_ai_response(response.text, finish_reason=finish_reason)
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
            "reply": FRIENDLY_ERROR_FALLBACK,
            "workspace": workspace,
            "model": used_model,
            "error": True
        }
