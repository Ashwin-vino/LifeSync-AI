import logging
from fastapi import APIRouter, HTTPException, Depends
from backend.app.schemas.profile import ProfileUpdateSchema, ProfileResponseSchema
from backend.app.database.supabase_client import get_user_profile, update_user_profile
from backend.app.auth import get_authenticated_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("", response_model=ProfileResponseSchema)
async def fetch_profile(user_id: str = Depends(get_authenticated_user_id)):
    try:
        p = get_user_profile(user_id)
        if not p:
            # Create default profile row if not existing
            p = update_user_profile(user_id, {
                "display_name": "Ashwin",
                "primary_goal": "Strength & Lean Muscle",
                "activity_level": "moderate",
                "calorie_target": 2200,
                "protein_target": 160,
                "carbs_target": 220,
                "fat_target": 65,
                "water_target_liters": 3.0,
                "sleep_target_hours": 8.0
            })
        return ProfileResponseSchema(
            id=str(p.get("id")),
            user_id=p.get("user_id", user_id),
            display_name=p.get("display_name", "User"),
            primary_goal=p.get("primary_goal", "Overall Wellness"),
            activity_level=p.get("activity_level", "moderate"),
            calorie_target=int(p.get("calorie_target", 2200)),
            protein_target=int(p.get("protein_target", 160)),
            carbs_target=int(p.get("carbs_target", 220)),
            fat_target=int(p.get("fat_target", 65)),
            water_target_liters=float(p.get("water_target_liters", 3.0)),
            sleep_target_hours=float(p.get("sleep_target_hours", 8.0)),
            created_at=str(p.get("created_at"))
        )
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("", response_model=ProfileResponseSchema)
async def save_profile(req: ProfileUpdateSchema, user_id: str = Depends(get_authenticated_user_id)):
    try:
        clean_data = req.model_dump(exclude_unset=True)
        updated = update_user_profile(user_id, clean_data)
        return ProfileResponseSchema(
            id=str(updated.get("id")),
            user_id=updated.get("user_id", user_id),
            display_name=updated.get("display_name", "User"),
            primary_goal=updated.get("primary_goal", "Overall Wellness"),
            activity_level=updated.get("activity_level", "moderate"),
            calorie_target=int(updated.get("calorie_target", 2200)),
            protein_target=int(updated.get("protein_target", 160)),
            carbs_target=int(updated.get("carbs_target", 220)),
            fat_target=int(updated.get("fat_target", 65)),
            water_target_liters=float(updated.get("water_target_liters", 3.0)),
            sleep_target_hours=float(updated.get("sleep_target_hours", 8.0)),
            created_at=str(updated.get("created_at"))
        )
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
