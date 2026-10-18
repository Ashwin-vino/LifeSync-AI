from typing import Optional
from pydantic import BaseModel, Field

class ProfileUpdateSchema(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    primary_goal: Optional[str] = None
    activity_level: Optional[str] = None
    calorie_target: Optional[int] = Field(None, ge=1000, le=8000)
    protein_target: Optional[int] = Field(None, ge=30, le=400)
    carbs_target: Optional[int] = Field(None, ge=20, le=800)
    fat_target: Optional[int] = Field(None, ge=10, le=250)
    water_target_liters: Optional[float] = Field(None, ge=1.0, le=10.0)
    sleep_target_hours: Optional[float] = Field(None, ge=4.0, le=14.0)

class ProfileResponseSchema(BaseModel):
    id: str
    user_id: str
    display_name: str
    primary_goal: str
    activity_level: str
    calorie_target: int
    protein_target: int
    carbs_target: int
    fat_target: int
    water_target_liters: float
    sleep_target_hours: float
    created_at: str
