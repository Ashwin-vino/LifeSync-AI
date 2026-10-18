import json
import logging
from datetime import date
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from backend.app.auth import get_authenticated_user_id
from google import genai
from google.genai import types

from backend.app.config import settings
from backend.app.schemas.home import DailyWellnessOverview
from backend.app.database.supabase_client import (
    get_user_profile,
    get_recovery_log_by_date,
    get_meals_by_date,
    get_recent_workouts,
    get_active_workout_plan
)
from backend.app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/home", tags=["home"])

MODEL_NAME = "gemini-3.8-flash"

def _get_gemini_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)

import re

def _has_word(text: str, keywords: List[str]) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE) for w in keywords)

def route_user_intent(message: str) -> str:
    """
    Determine which workspace telemetry is required to answer the user query:
    'all', 'workout', 'nutrition', 'recovery', or 'general'.
    """
    msg_lower = message.lower()
    needs_workout = _has_word(msg_lower, ["workout", "exercise", "lift", "training", "squat", "bench", "deadlift", "sets", "reps", "gym", "rpe"])
    needs_nutrition = _has_word(msg_lower, ["eat", "food", "calorie", "calories", "protein", "carb", "carbs", "fat", "macro", "macros", "meal", "diet", "nutrition", "breakfast", "dinner", "snack"])
    needs_recovery = _has_word(msg_lower, ["sleep", "recovery", "sore", "soreness", "fatigue", "tired", "hrv", "resting hr", "hydrate", "hydration", "readiness"])

    count = sum([needs_workout, needs_nutrition, needs_recovery])
    if count >= 2 or _has_word(msg_lower, ["today", "overall", "summary", "plan", "focus", "how am i", "progress"]):
        return "all"
    elif needs_workout:
        return "workout"
    elif needs_nutrition:
        return "nutrition"
    elif needs_recovery:
        return "recovery"
    return "general"

@router.get("/overview", response_model=DailyWellnessOverview)
async def get_home_daily_overview(user_id: str = Depends(get_authenticated_user_id)):
    """
    Unified multi-workspace telemetry aggregator for Home AI.
    Combines:
    - User Profile & Goal Targets
    - Today's Recovery Log & Readiness Score
    - Today's Meals & Macro Breakdown vs Targets
    - Today's Completed Workouts & Active Training Plan
    - Recent Confirmed Memory Facts (Goals, Injuries, Restrictions)
    """
    today_str = date.today().isoformat()
    try:
        profile = get_user_profile(user_id) or {
            "display_name": "Ashwin",
            "primary_goal": "Strength & Lean Muscle",
            "calorie_target": 2200,
            "protein_target": 160,
            "carbs_target": 220,
            "fat_target": 65,
            "water_target_liters": 3.0,
            "sleep_target_hours": 8.0
        }

        # 1. Recovery
        today_rec = get_recovery_log_by_date(today_str, user_id=user_id)
        
        # 2. Nutrition
        meals = get_meals_by_date(today_str, user_id=user_id)
        total_cals = sum(float(m.get("calories") or 0.0) for m in meals)
        total_p = sum(float(m.get("protein") or m.get("protein_g") or 0.0) for m in meals)
        total_c = sum(float(m.get("carbs") or m.get("carbs_g") or 0.0) for m in meals)
        total_f = sum(float(m.get("fat") or m.get("fat_g") or 0.0) for m in meals)
        total_fib = sum(float(m.get("fiber") or 0.0) for m in meals)

        # 3. Workouts
        workouts = get_recent_workouts(limit=5, user_id=user_id, status="completed")
        today_workouts = [w for w in workouts if str(w.get("created_at", ""))[:10] == today_str]
        active_plan = get_active_workout_plan(user_id=user_id)

        # 4. Memory Facts
        memories = MemoryManager.list_user_memories(user_id=user_id, status="active")[:5]

        # 5. Readiness Status
        rec_score = int(today_rec.get("recovery_score", 75)) if today_rec else 75
        if rec_score >= 80:
            readiness = "Feeling Great (Ready to Train! 💪)"
        elif rec_score >= 60:
            readiness = "Good to Go (Standard Training Day)"
        else:
            readiness = "Taking it Easy (Rest & Recovery Day)"

        # 6. Synthesize 2-3 Actionable AI Insights
        insights = []
        if today_workouts:
            w_names = ", ".join([w.get("title", "Workout") for w in today_workouts])
            insights.append(f"Great job on completing your training session ({w_names})! Grab some protein to help your muscles recover. 💪")
        elif active_plan:
            insights.append(f"Your scheduled training is ready: '{active_plan.get('title')}'. Jump in whenever you're ready!")
        else:
            insights.append("No workouts logged today. Check today's plan when you're ready to move! ⏱️")

        rem_p = max(0.0, float(profile.get("protein_target", 160)) - total_p)
        if rem_p > 0:
            insights.append(f"Nutrition: {round(total_cals)} kcal logged. You're {round(rem_p, 1)}g of protein away from your daily goal! 🥗")
        else:
            insights.append(f"Protein goal hit ({round(total_p, 1)}g)! Total energy: {round(total_cals)} kcal. Great fueling today! 🎉")

        if today_rec:
            insights.append(f"Recovery score is {rec_score}/100 with {today_rec.get('sleep_hours')}h sleep and {today_rec.get('hydration_liters')}L water. Looking good! 😊")
        else:
            insights.append("Recovery metrics are unlogged today. Record your sleep and soreness whenever you're ready to get personalized tips! 😊")

        return DailyWellnessOverview(
            date=today_str,
            user_profile=profile,
            today_recovery=today_rec,
            today_meals=meals,
            today_macros={
                "calories": round(total_cals, 1),
                "protein": round(total_p, 1),
                "carbs": round(total_c, 1),
                "fat": round(total_f, 1),
                "fiber": round(total_fib, 1)
            },
            macro_targets={
                "calorie_target": float(profile.get("calorie_target", 2200)),
                "protein_target": float(profile.get("protein_target", 160)),
                "carbs_target": float(profile.get("carbs_target", 220)),
                "fat_target": float(profile.get("fat_target", 65))
            },
            today_workouts=today_workouts,
            active_workout_plan=active_plan,
            recent_memory_facts=memories,
            readiness_status=readiness,
            ai_insights=insights
        )
    except Exception as e:
        logger.error(f"Error compiling home overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
