from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MealItemSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    calories: float = Field(default=0.0, ge=0.0, le=5000.0)
    protein: float = Field(default=0.0, ge=0.0, le=500.0)
    carbs: float = Field(default=0.0, ge=0.0, le=1000.0)
    fat: float = Field(default=0.0, ge=0.0, le=500.0)
    fiber: float = Field(default=0.0, ge=0.0, le=200.0)
    portion_g: Optional[float] = Field(default=100.0, ge=0.0, le=5000.0)
    fdc_id: Optional[str] = None
    source: str = Field(default="usda_verified")

class MealCreateSchema(BaseModel):
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    name: str = Field(..., min_length=2, max_length=150)
    calories: float = Field(..., ge=0.0, le=10000.0)
    protein: float = Field(default=0.0, ge=0.0, le=1000.0)
    carbs: float = Field(default=0.0, ge=0.0, le=2000.0)
    fat: float = Field(default=0.0, ge=0.0, le=1000.0)
    fiber: Optional[float] = Field(default=0.0, ge=0.0, le=500.0)
    serving_size: Optional[float] = Field(default=100.0, ge=0.0)
    serving_unit: Optional[str] = Field(default="g")
    fdc_id: Optional[str] = None
    source: str = Field(default="usda_verified")
    date: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    items: Optional[List[Dict[str, Any]]] = None

class MealUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    meal_type: Optional[str] = Field(default=None, pattern="^(breakfast|lunch|dinner|snack)$")
    calories: Optional[float] = Field(default=None, ge=0.0, le=10000.0)
    protein: Optional[float] = Field(default=None, ge=0.0, le=1000.0)
    carbs: Optional[float] = Field(default=None, ge=0.0, le=2000.0)
    fat: Optional[float] = Field(default=None, ge=0.0, le=1000.0)
    fiber: Optional[float] = Field(default=None, ge=0.0, le=500.0)
    serving_size: Optional[float] = Field(default=None, ge=0.0)
    serving_unit: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    items: Optional[List[Dict[str, Any]]] = None

class MealResponseSchema(BaseModel):
    id: str
    user_id: str
    meal_type: str
    name: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float = 0.0
    serving_size: float = 100.0
    serving_unit: str = "g"
    fdc_id: Optional[str] = None
    source: str = "usda_verified"
    date: str
    notes: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    created_at: str

class NutritionDaySummary(BaseModel):
    date: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    calorie_target: float
    protein_target: float
    carbs_target: float
    fat_target: float
    meals: List[Dict[str, Any]] = []

class USDASearchItem(BaseModel):
    fdcId: str
    description: str
    brandOwner: Optional[str] = None
    servingSize: float = 100.0
    servingUnit: str = "g"
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    fiber: float = 0.0
    source: str = "usda_verified"

class NutritionRecommendationResponse(BaseModel):
    headline: str
    macro_advice: str
    suggested_meals: List[Dict[str, Any]] = []
    workout_nutrition_link: Optional[str] = None
    recovery_nutrition_link: Optional[str] = None
    cautions: List[str] = []
