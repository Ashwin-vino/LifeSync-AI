from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class DailyWellnessOverview(BaseModel):
    date: str
    user_profile: Dict[str, Any]
    today_recovery: Optional[Dict[str, Any]] = None
    today_meals: List[Dict[str, Any]] = []
    today_macros: Dict[str, float]
    macro_targets: Dict[str, float]
    today_workouts: List[Dict[str, Any]] = []
    active_workout_plan: Optional[Dict[str, Any]] = None
    recent_memory_facts: List[Dict[str, Any]] = []
    readiness_status: str
    ai_insights: List[str] = []
