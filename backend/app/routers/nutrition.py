import json
import logging
from datetime import date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from google import genai
from google.genai import types
from backend.app.auth import get_authenticated_user_id

from backend.app.config import settings
from backend.app.schemas.nutrition import (
    MealCreateSchema,
    MealUpdateSchema,
    MealResponseSchema,
    NutritionDaySummary,
    USDASearchItem,
    NutritionRecommendationResponse
)
from backend.app.database.supabase_client import (
    get_meals_by_date,
    get_meal_by_id,
    get_user_profile,
    get_recent_workouts,
    get_recent_recovery_logs
)
from backend.app.memory.memory_manager import MemoryManager
from backend.app.services.usda_service import search_foods, get_food_details

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview"]

def _get_gemini_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)

def calculate_day_macros(meals: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate aggregated calories, protein, carbs, fat, and fiber for a list of meals."""
    total_cals = sum(float(m.get("calories") or 0.0) for m in meals)
    total_p = sum(float(m.get("protein") or m.get("protein_g") or 0.0) for m in meals)
    total_c = sum(float(m.get("carbs") or m.get("carbs_g") or 0.0) for m in meals)
    total_f = sum(float(m.get("fat") or m.get("fat_g") or 0.0) for m in meals)
    total_fiber = sum(float(m.get("fiber") or 0.0) for m in meals)
    return {
        "calories": round(total_cals, 1),
        "protein": round(total_p, 1),
        "carbs": round(total_c, 1),
        "fat": round(total_f, 1),
        "fiber": round(total_fiber, 1)
    }

# ==================== Meal Logging & CRUD ====================

@router.get("/summary", response_model=NutritionDaySummary)
async def get_day_summary(
    date_str: Optional[str] = Query(default=None),
    user_id: str = Depends(get_authenticated_user_id)
):
    """Retrieve daily nutrition totals, macro adherence, and logged meals scoped to user."""
    target_date = date_str or date.today().isoformat()
    try:
        meals = get_meals_by_date(target_date, user_id=user_id)
        profile = get_user_profile(user_id) or {}
        
        calorie_target = float(profile.get("calorie_target") or 2200)
        protein_target = float(profile.get("protein_target") or 160)
        carbs_target = float(profile.get("carbs_target") or 220)
        fat_target = float(profile.get("fat_target") or 65)

        macros = calculate_day_macros(meals)
        total_cals = macros["calories"]
        total_p = macros["protein"]
        total_c = macros["carbs"]
        total_f = macros["fat"]
        total_fiber = macros["fiber"]

        formatted_meals = []
        for m in meals:
            formatted_meals.append({
                "id": str(m.get("id")),
                "user_id": m.get("user_id", user_id),
                "meal_type": m.get("meal_type", "lunch"),
                "name": m.get("name", "Meal"),
                "calories": float(m.get("calories") or 0.0),
                "protein": float(m.get("protein") or m.get("protein_g") or 0.0),
                "carbs": float(m.get("carbs") or m.get("carbs_g") or 0.0),
                "fat": float(m.get("fat") or m.get("fat_g") or 0.0),
                "fiber": float(m.get("fiber") or 0.0),
                "serving_size": float(m.get("serving_size") or 100.0),
                "serving_unit": m.get("serving_unit", "g"),
                "source": m.get("source", "usda_verified"),
                "fdc_id": m.get("fdc_id"),
                "date": str(m.get("date", target_date)),
                "notes": m.get("notes"),
                "items": m.get("items") or [],
                "created_at": str(m.get("created_at", ""))
            })

        return NutritionDaySummary(
            date=target_date,
            total_calories=round(total_cals, 1),
            total_protein=round(total_p, 1),
            total_carbs=round(total_c, 1),
            total_fat=round(total_f, 1),
            total_fiber=round(total_fiber, 1),
            calorie_target=calorie_target,
            protein_target=protein_target,
            carbs_target=carbs_target,
            fat_target=fat_target,
            meals=formatted_meals
        )
    except Exception as e:
        logger.error(f"Error retrieving nutrition day summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/meal/{meal_id}", response_model=MealResponseSchema)
async def get_single_meal(meal_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Retrieve single meal record verifying ownership."""
    m = get_meal_by_id(meal_id, user_id=user_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meal record not found or access denied")
    return MealResponseSchema(
        id=str(m.get("id")),
        user_id=m.get("user_id", user_id),
        meal_type=m.get("meal_type", "lunch"),
        name=m.get("name", "Meal"),
        calories=float(m.get("calories") or 0.0),
        protein=float(m.get("protein") or m.get("protein_g") or 0.0),
        carbs=float(m.get("carbs") or m.get("carbs_g") or 0.0),
        fat=float(m.get("fat") or m.get("fat_g") or 0.0),
        fiber=float(m.get("fiber") or 0.0),
        serving_size=float(m.get("serving_size") or 100.0),
        serving_unit=m.get("serving_unit", "g"),
        fdc_id=m.get("fdc_id"),
        source=m.get("source", "usda_verified"),
        date=str(m.get("date")),
        notes=m.get("notes"),
        items=m.get("items") or [],
        created_at=str(m.get("created_at", ""))
    )

@router.post("/log", response_model=MealResponseSchema)
async def log_meal(req: MealCreateSchema, user_id: str = Depends(get_authenticated_user_id)):
    """Log a meal across Supabase and FalkorDB graph memory."""
    try:
        target_date = req.date or date.today().isoformat()
        meal_data = {
            "meal_type": req.meal_type,
            "name": req.name,
            "calories": req.calories,
            "protein": req.protein,
            "carbs": req.carbs,
            "fat": req.fat,
            "fiber": req.fiber or 0.0,
            "serving_size": req.serving_size or 100.0,
            "serving_unit": req.serving_unit or "g",
            "fdc_id": req.fdc_id,
            "source": req.source or "usda_verified",
            "date": target_date,
            "notes": req.notes,
            "items": req.items or []
        }
        saved = MemoryManager.record_completed_meal(meal_data, user_id=user_id)
        return MealResponseSchema(
            id=str(saved.get("id")),
            user_id=saved.get("user_id", user_id),
            meal_type=saved.get("meal_type", req.meal_type),
            name=saved.get("name", req.name),
            calories=float(saved.get("calories", req.calories)),
            protein=float(saved.get("protein", req.protein)),
            carbs=float(saved.get("carbs", req.carbs)),
            fat=float(saved.get("fat", req.fat)),
            fiber=float(saved.get("fiber", req.fiber or 0.0)),
            serving_size=float(saved.get("serving_size", req.serving_size or 100.0)),
            serving_unit=saved.get("serving_unit", "g"),
            fdc_id=saved.get("fdc_id"),
            source=saved.get("source", "usda_verified"),
            date=str(saved.get("date", target_date)),
            notes=saved.get("notes"),
            items=saved.get("items") or [],
            created_at=str(saved.get("created_at", ""))
        )
    except Exception as e:
        logger.error(f"Error logging meal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/meal/{meal_id}", response_model=MealResponseSchema)
async def update_meal(
    meal_id: str,
    req: MealUpdateSchema,
    user_id: str = Depends(get_authenticated_user_id)
):
    """Edit an existing meal log with ownership validation."""
    existing = get_meal_by_id(meal_id, user_id=user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Meal not found or access denied")

    try:
        update_data = {
            "name": req.name,
            "meal_type": req.meal_type,
            "calories": req.calories,
            "protein": req.protein,
            "carbs": req.carbs,
            "fat": req.fat,
            "fiber": req.fiber,
            "serving_size": req.serving_size,
            "serving_unit": req.serving_unit,
            "notes": req.notes,
            "items": req.items
        }
        updated = MemoryManager.update_completed_meal(meal_id, update_data, user_id=user_id)
        return MealResponseSchema(
            id=str(updated.get("id")),
            user_id=updated.get("user_id", user_id),
            meal_type=updated.get("meal_type", existing.get("meal_type")),
            name=updated.get("name", existing.get("name")),
            calories=float(updated.get("calories", existing.get("calories", 0))),
            protein=float(updated.get("protein", existing.get("protein", 0))),
            carbs=float(updated.get("carbs", existing.get("carbs", 0))),
            fat=float(updated.get("fat", existing.get("fat", 0))),
            fiber=float(updated.get("fiber", existing.get("fiber", 0))),
            serving_size=float(updated.get("serving_size", existing.get("serving_size", 100.0))),
            serving_unit=updated.get("serving_unit", "g"),
            fdc_id=updated.get("fdc_id"),
            source=updated.get("source", "usda_verified"),
            date=str(updated.get("date", existing.get("date"))),
            notes=updated.get("notes"),
            items=updated.get("items") or [],
            created_at=str(updated.get("created_at", ""))
        )
    except Exception as e:
        logger.error(f"Error updating meal {meal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/meal/{meal_id}")
async def delete_meal(meal_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Delete a meal record across Supabase and FalkorDB graph memory."""
    existing = get_meal_by_id(meal_id, user_id=user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Meal not found or access denied")

    try:
        MemoryManager.delete_completed_meal(meal_id, user_id=user_id)
        return {"status": "deleted", "id": meal_id, "success": True}
    except Exception as e:
        logger.error(f"Error deleting meal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== USDA Food Search ====================

@router.get("/search-foods", response_model=List[USDASearchItem])
async def search_usda_foods(q: str = Query(..., min_length=2, max_length=100)):
    """Search official USDA FoodData Central database with clear verified source labels."""
    try:
        results = await search_foods(q, page_size=15)
        return [
            USDASearchItem(
                fdcId=str(r["fdcId"]),
                description=r["description"],
                brandOwner=r.get("brandOwner"),
                servingSize=float(r.get("servingSize", 100.0)),
                servingUnit=r.get("servingUnit", "g"),
                calories=float(r.get("calories", 0.0)),
                protein=float(r.get("protein", 0.0)),
                carbs=float(r.get("carbs", 0.0)),
                fat=float(r.get("fat", 0.0)),
                fiber=float(r.get("fiber", 0.0)),
                source=r.get("source", "usda_verified")
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Error in search_usda_foods: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/food/{fdc_id}", response_model=USDASearchItem)
async def get_single_food(fdc_id: str = Path(...)):
    """Fetch complete nutrition profile for a single verified USDA item."""
    item = await get_food_details(fdc_id)
    if not item:
        raise HTTPException(status_code=404, detail="Food item not found in USDA database")
    return USDASearchItem(
        fdcId=str(item["fdcId"]),
        description=item["description"],
        brandOwner=item.get("brandOwner"),
        servingSize=float(item.get("servingSize", 100.0)),
        servingUnit=item.get("servingUnit", "g"),
        calories=float(item.get("calories", 0.0)),
        protein=float(item.get("protein", 0.0)),
        carbs=float(item.get("carbs", 0.0)),
        fat=float(item.get("fat", 0.0)),
        fiber=float(item.get("fiber", 0.0)),
        source=item.get("source", "usda_verified")
    )

# ==================== Personalized Nutrition Recommendations ====================

@router.post("/recommendations", response_model=NutritionRecommendationResponse)
async def get_nutrition_recommendations(user_id: str = Depends(get_authenticated_user_id)):
    """
    Generate personalized nutrition recommendations using Gemini grounded in:
    - User goals and explicit dietary preferences
    - Today's logged meals and remaining macros
    - Completed workouts from Workout AI (glycogen replenishment, protein needs)
    - Recovery readiness state
    """
    today_str = date.today().isoformat()
    meals = get_meals_by_date(today_str, user_id=user_id)
    profile = get_user_profile(user_id) or {"display_name": "Ashwin", "primary_goal": "Strength & Lean Muscle"}

    # Macro totals
    total_cals = sum(float(m.get("calories") or 0.0) for m in meals)
    total_p = sum(float(m.get("protein") or m.get("protein_g") or 0.0) for m in meals)
    total_c = sum(float(m.get("carbs") or m.get("carbs_g") or 0.0) for m in meals)
    total_f = sum(float(m.get("fat") or m.get("fat_g") or 0.0) for m in meals)

    cal_target = float(profile.get("calorie_target") or 2200)
    prot_target = float(profile.get("protein_target") or 160)

    # Cross-agent context: completed workouts today
    recent_workouts = get_recent_workouts(limit=2, user_id=user_id, status="completed")
    recent_recovery = get_recent_recovery_logs(limit=1, user_id=user_id)

    # Cross-agent memory context
    memory_context = MemoryManager.get_relevant_context(user_id, workspace="nutrition", current_message="Personalized meal recommendations")

    prompt = f"""You are LifeSync AI's Lead Performance Nutritionist.
Synthesize individualized meal recommendations and macro guidance for the user.

ATHLETE PROFILE & MEMORY:
{memory_context}

TODAY'S LOGGED NUTRITION ({today_str}):
- Current: {round(total_cals)} / {round(cal_target)} kcal
- Protein: {round(total_p, 1)} / {round(prot_target, 1)}g
- Carbs: {round(total_c, 1)}g, Fat: {round(total_f, 1)}g
- Meals logged count: {len(meals)}

COMPLETED WORKOUTS TODAY:
{json.dumps([{ 'title': w.get('title'), 'category': w.get('category'), 'duration': w.get('duration_minutes'), 'calories': w.get('calories_burned') } for w in recent_workouts])}

RECOVERY STATE:
{json.dumps([{ 'score': r.get('recovery_score'), 'sleep': r.get('sleep_hours'), 'soreness': r.get('soreness_level') } for r in recent_recovery]) if recent_recovery else 'None recorded today'}

Return a JSON object:
{{
  "headline": "Short punchy summary (e.g. Post-Workout Refuel & Glycogen Replenishment)",
  "macro_advice": "Actionable explanation of calories and macros remaining today based on their workout and recovery.",
  "suggested_meals": [
    {{
      "name": "Meal name",
      "type": "snack" or "dinner",
      "est_calories": 450,
      "est_protein": 35,
      "est_carbs": 50,
      "est_fat": 12,
      "rationale": "Why this aligns with today's training"
    }}
  ],
  "workout_nutrition_link": "How today's specific workout influences this advice",
  "recovery_nutrition_link": "How hydration or sleep influences this advice",
  "cautions": ["Dietary caution if applicable"]
}}
"""

    client = _get_gemini_client()
    for m in [MODEL_NAME] + FALLBACK_MODELS:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.4)
            )
            if resp and resp.text:
                data = json.loads(resp.text)
                return NutritionRecommendationResponse(**data)
        except Exception as me:
            logger.warning(f"Model {m} failed for nutrition recommendations: {me}. Trying fallback...")
            continue

    # Fallback response
    rem_cals = max(round(cal_target - total_cals), 0)
    rem_p = max(round(prot_target - total_p, 1), 0.0)
    return NutritionRecommendationResponse(
        headline="Balanced Nutrient Allocation",
        macro_advice=f"You have approximately {rem_cals} kcal and {rem_p}g protein remaining to hit your target today.",
        suggested_meals=[
            {
                "name": "Grilled Chicken Breast with Quinoa & Steamed Broccoli",
                "type": "dinner",
                "est_calories": 480,
                "est_protein": 42,
                "est_carbs": 52,
                "est_fat": 8,
                "rationale": "High bioavailability lean protein with complex carbs to replenish muscle glycogen."
            }
        ],
        workout_nutrition_link="Prioritizing complete protein and complex carbs after physical training.",
        recovery_nutrition_link="Ensure adequate sodium and water intake to support cellular rehydration.",
        cautions=["Adjust portion sizes according to your subjective fullness and energy demands."]
    )
