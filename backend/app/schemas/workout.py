from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class WorkoutExerciseSchema(BaseModel):
    id: Optional[str] = None
    exercise_name: str = Field(..., min_length=1, max_length=150)
    target_muscle: Optional[str] = None
    sets: int = Field(default=3, ge=1, le=50)
    reps: int = Field(default=10, ge=1, le=500)
    weight_kg: float = Field(default=0.0, ge=0.0, le=1000.0)
    notes: Optional[str] = None
    status: str = Field(default="completed", pattern="^(completed|skipped|modified|planned)$")
    source: str = Field(default="wger_verified") # "wger_verified" | "ai_suggested" | "custom"
    rest_seconds: Optional[int] = Field(default=90, ge=0, le=600)

class WorkoutCreateSchema(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    category: str = Field(default="Strength")
    duration_minutes: int = Field(default=45, ge=1, le=480)
    calories_burned: Optional[int] = Field(default=None, ge=0, le=5000)
    rpe: Optional[int] = Field(default=7, ge=1, le=10)
    status: str = Field(default="completed", pattern="^(completed|in_progress|planned)$")
    plan_id: Optional[str] = None
    notes: Optional[str] = None
    exercises: List[WorkoutExerciseSchema] = []

class WorkoutUpdateSchema(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=150)
    category: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=480)
    calories_burned: Optional[int] = Field(default=None, ge=0, le=5000)
    rpe: Optional[int] = Field(default=None, ge=1, le=10)
    status: Optional[str] = Field(default=None, pattern="^(completed|in_progress|planned)$")
    notes: Optional[str] = None
    exercises: Optional[List[WorkoutExerciseSchema]] = None

class WorkoutResponseSchema(BaseModel):
    id: str
    user_id: str
    title: str
    category: str
    duration_minutes: int
    calories_burned: Optional[int] = None
    rpe: Optional[int] = 7
    status: str = "completed"
    notes: Optional[str] = None
    created_at: str
    workout_exercises: List[Dict[str, Any]] = []

class PlannedExerciseSchema(BaseModel):
    name: str = Field(..., min_length=1)
    target_muscle: str = Field(default="Full Body")
    sets: int = Field(default=3, ge=1, le=20)
    reps: str = Field(default="8-12") # string to support rep ranges like "8-10" or "Failure"
    rest_seconds: int = Field(default=90, ge=15, le=360)
    suggested_weight_kg: Optional[float] = None
    notes: Optional[str] = None
    wger_id: Optional[str] = None
    source: str = Field(default="wger_verified") # "wger_verified" | "ai_suggested"

class WorkoutPlanGenerateRequest(BaseModel):
    focus: Optional[str] = Field(default=None, max_length=100) # e.g. "Upper Body Push", "Legs", "Cardio"
    duration_target: Optional[int] = Field(default=45, ge=15, le=120)
    equipment_available: Optional[List[str]] = None
    notes: Optional[str] = Field(default=None, max_length=500)

class WorkoutPlanResponseSchema(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = "default_user"
    title: str
    category: str = "Strength"
    summary: str
    warmup: List[str] = []
    exercises: List[PlannedExerciseSchema] = []
    cooldown: List[str] = []
    estimated_duration_minutes: int = 45
    status: str = "planned" # "planned" | "in_progress" | "completed"
    explanation: str
    created_at: Optional[str] = None

class ExerciseSearchItem(BaseModel):
    id: str
    name: str
    category: str
    muscles: List[str] = []
    equipment: List[str] = []
    description: Optional[str] = None
    source: str = "wger_verified" # "wger_verified" | "local_cache" | "ai_suggested"

class WorkoutAnalyticsResponse(BaseModel):
    total_sessions: int
    total_volume_kg: float
    total_minutes: int
    average_rpe: float
    category_distribution: Dict[str, int]
    recent_7_days_volume: List[Dict[str, Any]]
