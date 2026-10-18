import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from backend.app.auth import get_authenticated_user_id

from backend.app.schemas.workout import (
    WorkoutCreateSchema,
    WorkoutUpdateSchema,
    WorkoutResponseSchema,
    ExerciseSearchItem,
    WorkoutPlanGenerateRequest,
    WorkoutPlanResponseSchema,
    WorkoutAnalyticsResponse
)
from backend.app.database.supabase_client import (
    get_recent_workouts,
    get_workout_by_id,
    create_workout_entry,
    update_workout_entry,
    delete_workout_entry,
    save_generated_plan,
    get_active_workout_plan,
    update_plan_status
)
from backend.app.memory.memory_manager import MemoryManager
from backend.app.services.wger_service import (
    search_exercises,
    fetch_exercises,
    get_exercise_by_id,
    get_categories
)
from backend.app.services.workout_planner import generate_personalized_workout_plan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workout", tags=["workout"])

# ==================== Workout Log Operations ====================

@router.get("/list", response_model=List[WorkoutResponseSchema])
async def list_workouts(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_authenticated_user_id),
    status: Optional[str] = Query(default="completed")
):
    """Retrieve logged workouts for the user, filtered by status."""
    try:
        data = get_recent_workouts(limit=limit, user_id=user_id, status=status)
        results = []
        for w in data:
            results.append(WorkoutResponseSchema(
                id=str(w.get("id")),
                user_id=w.get("user_id", user_id),
                title=w.get("title", "Workout"),
                category=w.get("category", "Strength"),
                duration_minutes=int(w.get("duration_minutes", 45)),
                calories_burned=w.get("calories_burned"),
                rpe=int(w.get("rpe", 7)),
                status=w.get("status", "completed"),
                notes=w.get("notes"),
                created_at=str(w.get("created_at")),
                workout_exercises=w.get("workout_exercises", [])
            ))
        return results
    except Exception as e:
        logger.error(f"Error fetching workouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{workout_id}", response_model=WorkoutResponseSchema)
async def get_workout(workout_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Retrieve a single workout session by ID."""
    w = get_workout_by_id(workout_id, user_id=user_id)
    if not w:
        raise HTTPException(status_code=404, detail="Workout not found")
    return WorkoutResponseSchema(
        id=str(w.get("id")),
        user_id=w.get("user_id", user_id),
        title=w.get("title", "Workout"),
        category=w.get("category", "Strength"),
        duration_minutes=int(w.get("duration_minutes", 45)),
        calories_burned=w.get("calories_burned"),
        rpe=int(w.get("rpe", 7)),
        status=w.get("status", "completed"),
        notes=w.get("notes"),
        created_at=str(w.get("created_at")),
        workout_exercises=w.get("workout_exercises", [])
    )

@router.post("/log", response_model=WorkoutResponseSchema)
async def log_workout(req: WorkoutCreateSchema, user_id: str = Depends(get_authenticated_user_id)):
    """
    Log a workout session.
    - If status == 'completed': persists to Supabase, updates FalkorDB graph,
      and records vector memory fact so Nutrition & Recovery AI can immediately access it.
    - If status == 'planned': recorded as a plan, NOT counted as completed activity.
    """
    try:
        workout_data = {
            "title": req.title,
            "category": req.category,
            "duration_minutes": req.duration_minutes,
            "calories_burned": req.calories_burned,
            "rpe": req.rpe or 7,
            "status": req.status,
            "notes": req.notes
        }
        exercises_data = [ex.model_dump(exclude={"id"}) for ex in req.exercises]

        # Only completed workouts trigger cross-agent graph activity records
        if req.status == "completed":
            saved = MemoryManager.record_completed_workout(
                workout_data=workout_data,
                exercises=exercises_data,
                user_id=user_id
            )
            # If linked to a planned workout, mark the plan as completed
            if req.plan_id:
                update_plan_status(req.plan_id, status="completed", user_id=user_id)
        else:
            # Saved as planned/in_progress record without graph completion side-effects
            saved = create_workout_entry(workout_data, exercises_data, user_id=user_id)

        return WorkoutResponseSchema(
            id=str(saved.get("id")),
            user_id=saved.get("user_id", user_id),
            title=saved.get("title", req.title),
            category=saved.get("category", req.category),
            duration_minutes=int(saved.get("duration_minutes", req.duration_minutes)),
            calories_burned=saved.get("calories_burned"),
            rpe=int(saved.get("rpe", req.rpe or 7)),
            status=saved.get("status", req.status),
            notes=saved.get("notes"),
            created_at=str(saved.get("created_at", "")),
            workout_exercises=saved.get("workout_exercises", [])
        )
    except Exception as e:
        logger.error(f"Error logging workout: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{workout_id}", response_model=WorkoutResponseSchema)
async def update_workout(
    workout_id: str,
    req: WorkoutUpdateSchema,
    user_id: str = Depends(get_authenticated_user_id)
):
    """Update an existing workout log and resynchronize FalkorDB graph memory."""
    try:
        existing = get_workout_by_id(workout_id, user_id=user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Workout not found")

        workout_data = {
            "title": req.title,
            "category": req.category,
            "duration_minutes": req.duration_minutes,
            "calories_burned": req.calories_burned,
            "rpe": req.rpe,
            "status": req.status,
            "notes": req.notes
        }
        exercises_data = [ex.model_dump(exclude={"id"}) for ex in req.exercises] if req.exercises is not None else None

        updated = MemoryManager.update_completed_workout(
            workout_id=workout_id,
            workout_data=workout_data,
            exercises=exercises_data,
            user_id=user_id
        )

        return WorkoutResponseSchema(
            id=str(updated.get("id")),
            user_id=updated.get("user_id", user_id),
            title=updated.get("title", "Workout"),
            category=updated.get("category", "Strength"),
            duration_minutes=int(updated.get("duration_minutes", 45)),
            calories_burned=updated.get("calories_burned"),
            rpe=int(updated.get("rpe", 7)),
            status=updated.get("status", "completed"),
            notes=updated.get("notes"),
            created_at=str(updated.get("created_at", "")),
            workout_exercises=updated.get("workout_exercises", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workout {workout_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{workout_id}")
async def delete_workout(workout_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Delete a workout record across Supabase and FalkorDB graph memory."""
    try:
        existing = get_workout_by_id(workout_id, user_id=user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Workout not found")

        MemoryManager.delete_completed_workout(workout_id=workout_id, user_id=user_id)
        return {"status": "deleted", "id": workout_id, "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workout {workout_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Workout Intelligence & Planning ====================

@router.post("/generate-plan", response_model=WorkoutPlanResponseSchema)
async def generate_plan(
    req: WorkoutPlanGenerateRequest,
    user_id: str = Depends(get_authenticated_user_id)
):
    """Generate personalized workout plan grounded in memory, recovery, and wger."""
    try:
        plan = await generate_personalized_workout_plan(user_id=user_id, req=req)
        return plan
    except Exception as e:
        logger.error(f"Error generating workout plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active-plan", response_model=Optional[WorkoutPlanResponseSchema])
async def get_active_plan(user_id: str = Depends(get_authenticated_user_id)):
    """Retrieve the current active or planned workout plan."""
    try:
        plan_row = get_active_workout_plan(user_id=user_id)
        if not plan_row:
            return None
        data = plan_row.get("plan_data", {})
        data["id"] = str(plan_row.get("id"))
        data["status"] = plan_row.get("status", "planned")
        data["created_at"] = str(plan_row.get("created_at"))
        return WorkoutPlanResponseSchema(**data)
    except Exception as e:
        logger.error(f"Error fetching active plan: {e}")
        return None

class StartSessionRequest(BaseModel):
    plan_id: Optional[str] = None

@router.post("/start-session")
async def start_session(req: StartSessionRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Mark an active plan as in-progress."""
    if req.plan_id:
        update_plan_status(req.plan_id, status="in_progress", user_id=user_id)
    return {"status": "in_progress", "plan_id": req.plan_id}

# ==================== Analytics & Telemetry ====================

@router.get("/analytics", response_model=WorkoutAnalyticsResponse)
async def get_analytics(user_id: str = Depends(get_authenticated_user_id)):
    """Calculate workout volume, category distribution, and 7-day progression."""
    try:
        workouts = get_recent_workouts(limit=50, user_id=user_id, status="completed")
        
        total_sessions = len(workouts)
        total_volume = 0.0
        total_minutes = 0
        rpe_sum = 0
        cat_dist: Dict[str, int] = {}

        # 7-day volume tracking
        today = date.today()
        seven_days_map = {
            (today - timedelta(days=i)).isoformat(): {"volume_kg": 0.0, "sessions": 0}
            for i in range(6, -1, -1)
        }

        for w in workouts:
            total_minutes += int(w.get("duration_minutes", 0) or 0)
            rpe_sum += int(w.get("rpe", 7) or 7)
            cat = w.get("category", "Strength")
            cat_dist[cat] = cat_dist.get(cat, 0) + 1

            # Compute session volume
            session_vol = 0.0
            for ex in w.get("workout_exercises", []):
                sets = int(ex.get("sets", 0) or 0)
                reps = int(ex.get("reps", 0) or 0)
                weight = float(ex.get("weight_kg", 0.0) or 0.0)
                session_vol += (sets * reps * weight)
            total_volume += session_vol

            # Group into 7-day map if within range
            created_str = str(w.get("created_at", ""))[:10]
            if created_str in seven_days_map:
                seven_days_map[created_str]["volume_kg"] += session_vol
                seven_days_map[created_str]["sessions"] += 1

        avg_rpe = round(rpe_sum / total_sessions, 1) if total_sessions > 0 else 0.0

        daily_volume = [
            {"date": d, "volume_kg": round(data["volume_kg"], 1), "sessions": data["sessions"]}
            for d, data in seven_days_map.items()
        ]

        return WorkoutAnalyticsResponse(
            total_sessions=total_sessions,
            total_volume_kg=round(total_volume, 1),
            total_minutes=total_minutes,
            average_rpe=avg_rpe,
            category_distribution=cat_dist,
            recent_7_days_volume=daily_volume
        )
    except Exception as e:
        logger.error(f"Error calculating analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== wger Exercise Library Operations ====================

@router.get("/exercises", response_model=List[ExerciseSearchItem])
async def list_exercises(
    q: str = Query(default="", max_length=100),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Search exercises from wger official library.
    Every exercise includes a distinct source badge ('wger_verified' vs 'local_cache').
    """
    try:
        if q.strip():
            items = await search_exercises(query=q.strip(), category=category)
        else:
            items = await fetch_exercises(limit=limit, offset=offset, category=category)

        return [
            ExerciseSearchItem(
                id=str(item.get("id")),
                name=item.get("name"),
                category=item.get("category", "General"),
                muscles=item.get("muscles", []),
                equipment=item.get("equipment", []),
                description=item.get("description"),
                source=item.get("source", "wger_verified")
            )
            for item in items[:limit]
        ]
    except Exception as e:
        logger.error(f"Error listing exercises: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exercises/{exercise_id}", response_model=ExerciseSearchItem)
async def get_single_exercise(exercise_id: str = Path(...)):
    """Fetch details for a single verified wger exercise by ID."""
    ex = await get_exercise_by_id(exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ExerciseSearchItem(
        id=str(ex.get("id")),
        name=ex.get("name"),
        category=ex.get("category", "General"),
        muscles=ex.get("muscles", []),
        equipment=ex.get("equipment", []),
        description=ex.get("description"),
        source=ex.get("source", "wger_verified")
    )

@router.get("/categories")
async def list_categories():
    """Retrieve official exercise categories from wger."""
    return await get_categories()
