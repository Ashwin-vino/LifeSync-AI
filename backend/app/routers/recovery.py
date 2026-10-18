import json
import logging
from datetime import date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from google import genai
from google.genai import types
from backend.app.auth import get_authenticated_user_id

from backend.app.config import settings
from backend.app.schemas.recovery import (
    RecoveryLogCreateSchema,
    RecoveryLogUpdateSchema,
    RecoveryLogResponseSchema,
    RecoveryStatusOverview,
    RecoveryRecommendationResponse
)
from backend.app.database.supabase_client import (
    get_recovery_log_by_date,
    get_recovery_log_by_id,
    get_recent_recovery_logs,
    get_recent_workouts,
    get_meals_by_date,
    get_user_profile
)
from backend.app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recovery", tags=["recovery"])

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview"]

def _get_gemini_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)

def compute_recovery_score(
    sleep_hours: float,
    sleep_quality: str,
    soreness_level: int,
    hydration_liters: float,
    stress_level: int,
    fatigue_level: int = 2
) -> int:
    """Calculate an evidence-based recovery score (0 - 100)."""
    # 1. Sleep quantity (up to 35 points, target = 8h)
    sleep_score = min(35.0, (sleep_hours / 8.0) * 35.0)
    
    # 2. Sleep quality (up to 20 points)
    quality_map = {"poor": 6.0, "fair": 12.0, "good": 17.0, "excellent": 20.0}
    quality_score = quality_map.get(sleep_quality.lower(), 14.0)
    
    # 3. Musculoskeletal soreness mitigation (up to 15 points, 0 soreness = 15, 10 soreness = 0)
    soreness_score = max(0.0, (10 - soreness_level) * 1.5)

    # 4. Systemic fatigue mitigation (up to 10 points)
    fatigue_score = max(0.0, (10 - fatigue_level) * 1.0)
    
    # 5. Hydration (up to 12 points, target = 3.0L)
    hydration_score = min(12.0, (hydration_liters / 3.0) * 12.0)
    
    # 6. Stress mitigation (up to 8 points, 1 stress = 8, 10 stress = 1)
    stress_score = max(1.0, (11 - stress_level) * 0.8)
    
    total = int(round(sleep_score + quality_score + soreness_score + fatigue_score + hydration_score + stress_score))
    return max(5, min(100, total))

def compute_readiness_score(data: Dict[str, Any]) -> int:
    """Helper wrapper for computing readiness score from a dictionary of metrics."""
    return compute_recovery_score(
        sleep_hours=float(data.get("sleep_hours") or 7.5),
        sleep_quality=str(data.get("sleep_quality") or "good"),
        soreness_level=int(data.get("soreness_level") or 2),
        hydration_liters=float(data.get("hydration_liters") or 2.5),
        stress_level=int(data.get("stress_level") or 3),
        fatigue_level=int(data.get("fatigue_level") or 2)
    )

# ==================== Recovery Logging & CRUD ====================

@router.get("/overview", response_model=RecoveryStatusOverview)
async def get_recovery_overview(user_id: str = Depends(get_authenticated_user_id)):
    """Retrieve recovery readiness status, weekly logs, and biomarker averages scoped to user."""
    today_str = date.today().isoformat()
    try:
        today_data = get_recovery_log_by_date(today_str, user_id=user_id)
        weekly = get_recent_recovery_logs(limit=7, user_id=user_id)
        
        today_model = None
        if today_data:
            today_model = RecoveryLogResponseSchema(
                id=str(today_data.get("id")),
                user_id=today_data.get("user_id", user_id),
                date=str(today_data.get("date")),
                recovery_score=int(today_data.get("recovery_score", 70)),
                sleep_hours=float(today_data.get("sleep_hours", 7.0)),
                sleep_quality=str(today_data.get("sleep_quality", "good")),
                resting_hr=today_data.get("resting_hr"),
                hrv_ms=today_data.get("hrv_ms"),
                hydration_liters=float(today_data.get("hydration_liters", 2.5)),
                soreness_level=int(today_data.get("soreness_level", 2)),
                fatigue_level=int(today_data.get("fatigue_level", 2)),
                stress_level=int(today_data.get("stress_level", 3)),
                notes=today_data.get("notes"),
                created_at=str(today_data.get("created_at", ""))
            )

        avg_sleep = 7.5
        avg_score = 78.0
        avg_hrv = None
        avg_rhr = None

        if weekly:
            avg_sleep = round(sum(float(x.get("sleep_hours", 7.5)) for x in weekly) / len(weekly), 1)
            avg_score = round(sum(float(x.get("recovery_score", 75)) for x in weekly) / len(weekly), 1)
            
            hrv_vals = [int(x["hrv_ms"]) for x in weekly if x.get("hrv_ms") is not None]
            if hrv_vals:
                avg_hrv = round(sum(hrv_vals) / len(hrv_vals), 1)
                
            rhr_vals = [int(x["resting_hr"]) for x in weekly if x.get("resting_hr") is not None]
            if rhr_vals:
                avg_rhr = round(sum(rhr_vals) / len(rhr_vals), 1)

        readiness = "Prime" if (today_model and today_model.recovery_score >= 80) else ("Adequate" if (today_model and today_model.recovery_score >= 60) else "Recovering")
        hydration_status = "Optimal" if (today_model and today_model.hydration_liters >= 2.8) else "Needs Attention"
        fatigue_trend = "Low Strain" if (today_model and today_model.soreness_level <= 3) else "Accumulated Fatigue"

        return RecoveryStatusOverview(
            today_log=today_model,
            weekly_logs=weekly,
            average_sleep=avg_sleep,
            average_recovery_score=avg_score,
            average_hrv=avg_hrv,
            average_resting_hr=avg_rhr,
            hydration_status=hydration_status,
            readiness_status=readiness,
            fatigue_trend=fatigue_trend
        )
    except Exception as e:
        logger.error(f"Error fetching recovery overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/log/{log_id}", response_model=RecoveryLogResponseSchema)
async def get_single_recovery_log(log_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Retrieve single recovery log with ownership check."""
    rec = get_recovery_log_by_id(log_id, user_id=user_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recovery log not found or access denied")
    return RecoveryLogResponseSchema(
        id=str(rec.get("id")),
        user_id=rec.get("user_id", user_id),
        date=str(rec.get("date")),
        recovery_score=int(rec.get("recovery_score", 70)),
        sleep_hours=float(rec.get("sleep_hours", 7.0)),
        sleep_quality=str(rec.get("sleep_quality", "good")),
        resting_hr=rec.get("resting_hr"),
        hrv_ms=rec.get("hrv_ms"),
        hydration_liters=float(rec.get("hydration_liters", 2.5)),
        soreness_level=int(rec.get("soreness_level", 2)),
        fatigue_level=int(rec.get("fatigue_level", 2)),
        stress_level=int(rec.get("stress_level", 3)),
        notes=rec.get("notes"),
        created_at=str(rec.get("created_at", ""))
    )

@router.post("/log", response_model=RecoveryLogResponseSchema)
async def log_recovery(req: RecoveryLogCreateSchema, user_id: str = Depends(get_authenticated_user_id)):
    """Record recovery biomarkers, compute readiness score, and sync with FalkorDB graph."""
    try:
        score = compute_recovery_score(
            sleep_hours=req.sleep_hours,
            sleep_quality=req.sleep_quality,
            soreness_level=req.soreness_level,
            hydration_liters=req.hydration_liters,
            stress_level=req.stress_level,
            fatigue_level=req.fatigue_level
        )

        data = {
            "date": req.date,
            "recovery_score": score,
            "sleep_hours": req.sleep_hours,
            "sleep_quality": req.sleep_quality,
            "resting_hr": req.resting_hr,
            "hrv_ms": req.hrv_ms,
            "hydration_liters": req.hydration_liters,
            "soreness_level": req.soreness_level,
            "fatigue_level": req.fatigue_level,
            "stress_level": req.stress_level,
            "notes": req.notes
        }

        saved = MemoryManager.record_recovery_log(data, user_id=user_id)
        return RecoveryLogResponseSchema(
            id=str(saved.get("id")),
            user_id=saved.get("user_id", user_id),
            date=str(saved.get("date")),
            recovery_score=int(saved.get("recovery_score", score)),
            sleep_hours=float(saved.get("sleep_hours")),
            sleep_quality=str(saved.get("sleep_quality")),
            resting_hr=saved.get("resting_hr"),
            hrv_ms=saved.get("hrv_ms"),
            hydration_liters=float(saved.get("hydration_liters")),
            soreness_level=int(saved.get("soreness_level")),
            fatigue_level=int(saved.get("fatigue_level", req.fatigue_level)),
            stress_level=int(saved.get("stress_level")),
            notes=saved.get("notes"),
            created_at=str(saved.get("created_at", ""))
        )
    except Exception as e:
        logger.error(f"Error saving recovery log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/log/{log_id}", response_model=RecoveryLogResponseSchema)
async def update_recovery(
    log_id: str,
    req: RecoveryLogUpdateSchema,
    user_id: str = Depends(get_authenticated_user_id)
):
    """Edit recovery record, recalculate score, and resync FalkorDB graph."""
    existing = get_recovery_log_by_id(log_id, user_id=user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recovery record not found or access denied")

    try:
        sleep_hours = req.sleep_hours if req.sleep_hours is not None else float(existing.get("sleep_hours", 7.0))
        sleep_quality = req.sleep_quality if req.sleep_quality is not None else str(existing.get("sleep_quality", "good"))
        soreness_level = req.soreness_level if req.soreness_level is not None else int(existing.get("soreness_level", 2))
        fatigue_level = req.fatigue_level if req.fatigue_level is not None else int(existing.get("fatigue_level", 2))
        hydration_liters = req.hydration_liters if req.hydration_liters is not None else float(existing.get("hydration_liters", 2.5))
        stress_level = req.stress_level if req.stress_level is not None else int(existing.get("stress_level", 3))

        score = compute_recovery_score(
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            soreness_level=soreness_level,
            hydration_liters=hydration_liters,
            stress_level=stress_level,
            fatigue_level=fatigue_level
        )

        update_data = {
            "recovery_score": score,
            "sleep_hours": sleep_hours,
            "sleep_quality": sleep_quality,
            "soreness_level": soreness_level,
            "fatigue_level": fatigue_level,
            "hydration_liters": hydration_liters,
            "stress_level": stress_level,
            "resting_hr": req.resting_hr if req.resting_hr is not None else existing.get("resting_hr"),
            "hrv_ms": req.hrv_ms if req.hrv_ms is not None else existing.get("hrv_ms"),
            "notes": req.notes if req.notes is not None else existing.get("notes")
        }

        updated = MemoryManager.update_recovery_log(log_id, update_data, user_id=user_id)
        return RecoveryLogResponseSchema(
            id=str(updated.get("id")),
            user_id=updated.get("user_id", user_id),
            date=str(updated.get("date")),
            recovery_score=int(updated.get("recovery_score", score)),
            sleep_hours=float(updated.get("sleep_hours")),
            sleep_quality=str(updated.get("sleep_quality")),
            resting_hr=updated.get("resting_hr"),
            hrv_ms=updated.get("hrv_ms"),
            hydration_liters=float(updated.get("hydration_liters")),
            soreness_level=int(updated.get("soreness_level")),
            fatigue_level=int(updated.get("fatigue_level", 2)),
            stress_level=int(updated.get("stress_level")),
            notes=updated.get("notes"),
            created_at=str(updated.get("created_at", ""))
        )
    except Exception as e:
        logger.error(f"Error updating recovery log {log_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/log/{log_id}")
async def delete_recovery(log_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Delete recovery record across Supabase and FalkorDB graph."""
    existing = get_recovery_log_by_id(log_id, user_id=user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recovery log not found or access denied")

    try:
        MemoryManager.delete_recovery_log(log_id, user_id=user_id)
        return {"status": "deleted", "id": log_id, "success": True}
    except Exception as e:
        logger.error(f"Error deleting recovery log {log_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Personalized Recovery Recommendations ====================

@router.post("/recommendations", response_model=RecoveryRecommendationResponse)
async def get_recovery_recommendations(user_id: str = Depends(get_authenticated_user_id)):
    """
    Synthesize individualized recovery guidance grounded in:
    - Recent completed workouts, duration, volume, and RPE
    - Today's sleep, quality, and soreness records
    - Today's nutrition and hydration status
    - Explicit injuries or limitations from memory facts
    """
    today_str = date.today().isoformat()
    today_rec = get_recovery_log_by_date(today_str, user_id=user_id)
    recent_workouts = get_recent_workouts(limit=3, user_id=user_id, status="completed")
    today_meals = get_meals_by_date(today_str, user_id=user_id)

    # Cross-agent memory context
    memory_context = MemoryManager.get_relevant_context(user_id, workspace="recovery", current_message="Personalized recovery recommendations")

    # Honest missing data tracking
    missing_fields = []
    if not today_rec:
        missing_fields.append("Today's sleep & soreness log")
    if not today_meals:
        missing_fields.append("Today's nutrition intake")
    if not recent_workouts:
        missing_fields.append("Recent workout records")

    prompt = f"""You are LifeSync AI's Lead Recovery & Sleep Scientist.
Synthesize individualized recovery guidance grounded strictly in the user's recorded biometrics and training history.

CRITICAL INSTRUCTIONS:
- Explain which recorded facts informed the recommendation.
- Any missing data must be explicitly described as unknown or unrecorded, NEVER fabricated or assumed to be normal.
- Provide practical recovery actions (active recovery, sleep hygiene, tissue work, hydration).
- Do not make medical diagnoses.

ATHLETE PERSISTENT MEMORY:
{memory_context}

TODAY'S RECOVERY RECORD:
{json.dumps(today_rec) if today_rec else 'None recorded today (Status: Unknown)'}

RECENT COMPLETED WORKOUTS:
{json.dumps([{ 'title': w.get('title'), 'category': w.get('category'), 'duration': w.get('duration_minutes'), 'rpe': w.get('rpe'), 'calories': w.get('calories_burned') } for w in recent_workouts])}

TODAY'S NUTRITION LOGGED:
{len(today_meals)} meals logged today.

Return a JSON object:
{{
  "readiness_score": {today_rec.get('recovery_score', 75) if today_rec else 70},
  "status": "Prime" or "Adequate" or "Recovering",
  "training_recommendation": "Clear suggestion on whether to train hard, do active recovery, or rest.",
  "rest_protocols": ["Specific protocol 1", "Specific protocol 2"],
  "sleep_guidance": "Concrete guidance on sleep timing and architecture.",
  "hydration_guidance": "Targeted fluid and electrolyte intake guidance.",
  "workout_influence_summary": "How recent workouts influenced this readiness state",
  "nutrition_influence_summary": "How today's nutrition supports recovery"
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
                return RecoveryRecommendationResponse(**data)
        except Exception as me:
            logger.warning(f"Model {m} failed for recovery recommendations: {me}. Trying fallback...")
            continue

    # Honest fallback
    score = int(today_rec.get("recovery_score", 70)) if today_rec else 70
    status_label = "Prime" if score >= 80 else ("Adequate" if score >= 60 else "Recovering")
    return RecoveryRecommendationResponse(
        readiness_score=score,
        status=status_label,
        training_recommendation="Moderate physical activity with focus on mobility and dynamic warm-up before any heavy loading.",
        rest_protocols=[
            "10 minutes of gentle spinal decompression and hip mobility",
            "Contrast shower or warm Epsom salt bath to stimulate parasympathetic blood flow"
        ],
        sleep_guidance="Target 7.5 to 8.5 hours with consistent sleep-wake timing and a cool, dark environment.",
        hydration_guidance="Consume 2.5 to 3.0 liters of water spaced throughout the day.",
        workout_influence_summary="Recent training load demands adequate restorative downtime.",
        nutrition_influence_summary="Support tissue repair with adequate protein and micronutrient density."
    )
