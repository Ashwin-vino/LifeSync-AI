from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class RecoveryLogCreateSchema(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    sleep_hours: float = Field(..., ge=0.0, le=24.0)
    sleep_quality: str = Field(default="good", pattern="^(poor|fair|good|excellent)$")
    resting_hr: Optional[int] = Field(default=None, ge=30, le=220)
    hrv_ms: Optional[int] = Field(default=None, ge=10, le=250)
    hydration_liters: float = Field(default=2.5, ge=0.0, le=15.0)
    soreness_level: int = Field(default=2, ge=0, le=10)
    fatigue_level: int = Field(default=2, ge=0, le=10)
    stress_level: int = Field(default=3, ge=1, le=10)
    notes: Optional[str] = Field(default=None, max_length=500)

class RecoveryLogUpdateSchema(BaseModel):
    sleep_hours: Optional[float] = Field(default=None, ge=0.0, le=24.0)
    sleep_quality: Optional[str] = Field(default=None, pattern="^(poor|fair|good|excellent)$")
    resting_hr: Optional[int] = Field(default=None, ge=30, le=220)
    hrv_ms: Optional[int] = Field(default=None, ge=10, le=250)
    hydration_liters: Optional[float] = Field(default=None, ge=0.0, le=15.0)
    soreness_level: Optional[int] = Field(default=None, ge=0, le=10)
    fatigue_level: Optional[int] = Field(default=None, ge=0, le=10)
    stress_level: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = Field(default=None, max_length=500)

class RecoveryLogResponseSchema(BaseModel):
    id: str
    user_id: str
    date: str
    recovery_score: int
    sleep_hours: float
    sleep_quality: str
    resting_hr: Optional[int] = None
    hrv_ms: Optional[int] = None
    hydration_liters: float
    soreness_level: int
    fatigue_level: int = 2
    stress_level: int
    notes: Optional[str] = None
    created_at: str

class RecoveryStatusOverview(BaseModel):
    today_log: Optional[RecoveryLogResponseSchema] = None
    weekly_logs: List[Dict[str, Any]] = []
    average_sleep: float
    average_recovery_score: float
    average_hrv: Optional[float] = None
    average_resting_hr: Optional[float] = None
    hydration_status: str
    readiness_status: str
    fatigue_trend: str

class RecoveryRecommendationResponse(BaseModel):
    readiness_score: int
    status: str
    training_recommendation: str
    rest_protocols: List[str] = []
    sleep_guidance: str
    hydration_guidance: str
    workout_influence_summary: Optional[str] = None
    nutrition_influence_summary: Optional[str] = None
