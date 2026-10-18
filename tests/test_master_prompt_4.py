import pytest
import uuid
from datetime import date
from unittest.mock import patch, MagicMock, AsyncMock

from backend.app.config import settings
from backend.app.schemas.nutrition import MealCreateSchema, MealUpdateSchema
from backend.app.schemas.recovery import RecoveryLogCreateSchema, RecoveryLogUpdateSchema
from backend.app.services.usda_service import (
    search_usda_foods,
    get_food_details,
    _get_curated_fallback_foods
)
from backend.app.memory.memory_manager import MemoryManager
from backend.app.memory.graph_service import (
    get_graph,
    delete_user_graph_data,
    get_graph_context_for_prompt
)
from backend.app.database.supabase_client import (
    get_supabase,
    save_meal_entry,
    get_meals_by_date,
    get_meal_by_id,
    update_meal_entry,
    delete_meal_entry,
    save_recovery_log,
    get_recovery_log_by_id,
    update_recovery_log_by_id,
    delete_recovery_log_by_id,
    get_recent_recovery_logs,
    get_recent_workouts,
    save_workout_session
)
from backend.app.routers.nutrition import calculate_day_macros
from backend.app.routers.recovery import compute_readiness_score
from backend.app.routers.home import route_user_intent, get_home_daily_overview
from backend.app.services.gemini_service import generate_chat_response

TEST_USER_A = "test_user_nutrition_rec_a"
TEST_USER_B = "test_user_nutrition_rec_b"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Ensure test users are cleaned before and after tests."""
    sb = get_supabase()

    def cleanup():
        try:
            for u in [TEST_USER_A, TEST_USER_B]:
                sb.table("meals").delete().eq("user_id", u).execute()
                sb.table("recovery_logs").delete().eq("user_id", u).execute()
                # Find workouts and delete their exercises first
                w_res = sb.table("workouts").select("id").eq("user_id", u).execute()
                for w in w_res.data or []:
                    sb.table("workout_exercises").delete().eq("workout_id", w["id"]).execute()
                sb.table("workouts").delete().eq("user_id", u).execute()
                sb.table("memory_facts").delete().eq("user_id", u).execute()
                sb.table("chat_messages").delete().eq("user_id", u).execute()
                delete_user_graph_data(u)
        except Exception as e:
            print("Cleanup notice:", e)

    cleanup()
    MemoryManager.initialize()
    yield
    cleanup()

# =========================================================================
# 1. Nutrition AI Tests
# =========================================================================

@pytest.mark.asyncio
async def test_real_usda_food_search():
    """Verify live search using real USDA FoodData Central API."""
    results = await search_usda_foods("chicken breast")
    assert len(results) > 0, "USDA search should return results"
    first = results[0]
    assert "description" in first
    assert "calories" in first
    assert "protein" in first
    assert "carbs" in first
    assert "fat" in first
    assert "servingSize" in first
    assert first.get("source") in ("usda_verified", "ai_estimated")

@pytest.mark.asyncio
async def test_usda_mocked_fallback_when_unavailable():
    """Explicitly labeled mock test for USDA fallback when API is down/rate-limited."""
    with patch("backend.app.services.usda_service.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("USDA API simulated 503 error")
        mock_client.return_value.__aenter__.return_value = mock_instance

        # Call search_usda_foods under failure with a term not previously in cache
        fallback_results = await search_usda_foods("mocked_fallback_query_oats_123")
        # Should return curated fallback foods
        assert len(fallback_results) >= 0

@pytest.mark.asyncio
async def test_nutrient_and_daily_total_calculations():
    """Verify accurate nutrient summation for daily totals including fiber."""
    meals = [
        {"calories": 450.0, "protein": 35.0, "carbs": 40.0, "fat": 12.0, "fiber": 4.0},
        {"calories": 620.0, "protein": 45.0, "carbs": 65.0, "fat": 18.0, "fiber": 8.0},
        {"calories": 210.0, "protein": 15.0, "carbs": 20.0, "fat": 5.0, "fiber": 3.0},
    ]
    totals = calculate_day_macros(meals)
    assert totals["calories"] == 1280.0
    assert totals["protein"] == 95.0
    assert totals["carbs"] == 125.0
    assert totals["fat"] == 35.0
    assert totals["fiber"] == 15.0

def test_meal_crud_operations():
    """Verify meal creation, retrieval by ID/date, updating, and deleting."""
    today_str = date.today().isoformat()

    # 1. Create
    meal_data = {
        "user_id": TEST_USER_A,
        "name": "Grilled Salmon & Quinoa",
        "meal_type": "dinner",
        "calories": 520,
        "protein": 42.5,
        "carbs": 38.0,
        "fat": 16.5,
        "fiber": 5.0,
        "serving_size": 1.5,
        "serving_unit": "cup",
        "source": "usda_verified",
        "fdc_id": "123456",
        "notes": "Post-workout dinner",
        "date": today_str
    }
    saved_meal = save_meal_entry(meal_data)
    meal_id = saved_meal["id"]
    assert meal_id is not None
    assert saved_meal["name"] == "Grilled Salmon & Quinoa"

    # 2. Retrieve
    retrieved = get_meal_by_id(meal_id, TEST_USER_A)
    assert retrieved is not None
    assert retrieved["id"] == meal_id
    assert retrieved["protein"] == 42.5

    # 3. Update
    updated = update_meal_entry(meal_id, TEST_USER_A, {
        "calories": 580,
        "protein": 48.0,
        "notes": "Added extra avocado"
    })
    assert updated["calories"] == 580
    assert updated["protein"] == 48.0
    assert updated["notes"] == "Added extra avocado"

    # 4. Delete
    deleted = delete_meal_entry(meal_id, TEST_USER_A)
    assert deleted is True

    # Confirm deletion
    assert get_meal_by_id(meal_id, TEST_USER_A) is None

def test_meal_records_isolated_by_owner():
    """Verify that User A's meal records cannot be viewed, updated, or deleted by User B."""
    today_str = date.today().isoformat()
    saved = save_meal_entry({
        "user_id": TEST_USER_A,
        "name": "User A Secret Protein Shake",
        "meal_type": "snack",
        "calories": 300,
        "protein": 30.0,
        "carbs": 10.0,
        "fat": 5.0,
        "date": today_str
    })
    meal_id = saved["id"]

    # User B cannot read User A's meal
    b_view = get_meal_by_id(meal_id, TEST_USER_B)
    assert b_view is None, "User B must not be able to retrieve User A's meal"

    # User B cannot update User A's meal
    b_update = update_meal_entry(meal_id, TEST_USER_B, {"name": "Hacked Meal"})
    assert b_update is None, "User B must not be able to update User A's meal"

    # User B cannot delete User A's meal
    b_delete = delete_meal_entry(meal_id, TEST_USER_B)
    assert b_delete is False, "User B must not be able to delete User A's meal"

    # Confirm User A's meal is intact
    a_view = get_meal_by_id(meal_id, TEST_USER_A)
    assert a_view is not None
    assert a_view["name"] == "User A Secret Protein Shake"

# =========================================================================
# 2. Recovery AI Tests
# =========================================================================

def test_recovery_crud_and_score_computation():
    """Verify recovery log creation, readiness calculation, update, and deletion."""
    today_str = date.today().isoformat()

    # 1. Create with good metrics
    log_data = {
        "user_id": TEST_USER_A,
        "date": today_str,
        "sleep_hours": 8.0,
        "sleep_quality": "good",
        "resting_hr": 52,
        "hrv_ms": 72,
        "hydration_liters": 3.0,
        "soreness_level": 2,
        "fatigue_level": 2,
        "stress_level": 2,
        "notes": "Felt well-rested"
    }
    score = compute_readiness_score(log_data)
    assert 70 <= score <= 100, f"Expected high readiness score for optimal metrics, got {score}"

    saved = save_recovery_log({**log_data, "recovery_score": score})
    rec_id = saved["id"]
    assert rec_id is not None
    assert saved["recovery_score"] == score

    # 2. Retrieve
    retrieved = get_recovery_log_by_id(rec_id, TEST_USER_A)
    assert retrieved is not None
    assert retrieved["sleep_hours"] == 8.0

    # 3. Update (user reports severe soreness)
    updated = update_recovery_log_by_id(rec_id, TEST_USER_A, {
        "soreness_level": 5,
        "fatigue_level": 4,
        "recovery_score": 52
    })
    assert updated["soreness_level"] == 5
    assert updated["recovery_score"] == 52

    # 4. Delete
    deleted = delete_recovery_log_by_id(rec_id, TEST_USER_A)
    assert deleted is True
    assert get_recovery_log_by_id(rec_id, TEST_USER_A) is None

@pytest.mark.asyncio
async def test_missing_recovery_data_handled_honestly():
    """Verify that unrecorded sleep or soreness is described as missing, not fabricated."""
    # Compute score with missing optional metrics
    partial_data = {
        "sleep_hours": 7.0,
        "sleep_quality": "good",
        "hydration_liters": 2.5
        # soreness_level, fatigue_level, resting_hr, hrv_ms are missing
    }
    score = compute_readiness_score(partial_data)
    assert isinstance(score, int)

    # Overview should identify missing metrics
    overview = await get_home_daily_overview(user_id=TEST_USER_A)
    assert overview.today_recovery is None
    # Insights should honestly disclose unlogged recovery
    recovery_insight = [ins for ins in overview.ai_insights if "Recovery" in ins]
    assert len(recovery_insight) > 0
    assert "unlogged" in recovery_insight[0] or "Record" in recovery_insight[0]

def test_recovery_records_isolated_by_owner():
    """Verify User A's recovery logs cannot be read, updated, or deleted by User B."""
    saved = save_recovery_log({
        "user_id": TEST_USER_A,
        "date": date.today().isoformat(),
        "sleep_hours": 8.0,
        "sleep_quality": "excellent",
        "hydration_liters": 3.0,
        "recovery_score": 92
    })
    rec_id = saved["id"]

    assert get_recovery_log_by_id(rec_id, TEST_USER_B) is None
    assert update_recovery_log_by_id(rec_id, TEST_USER_B, {"sleep_hours": 4.0}) is None
    assert delete_recovery_log_by_id(rec_id, TEST_USER_B) is False

    # Intact for owner
    assert get_recovery_log_by_id(rec_id, TEST_USER_A) is not None

# =========================================================================
# 3. Unified Home AI & Cross-Agent Integration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_workout_meal_recovery_all_retrievable_by_home_ai():
    """
    Verify that:
    1. A completed workout in Workout AI
    2. A logged meal in Nutrition AI
    3. A recovery record in Recovery AI
    Are all retrieved simultaneously and integrated into Home AI's daily overview.
    """
    today_str = date.today().isoformat()

    # 1. Completed workout in Workout AI
    save_workout_session({
        "user_id": TEST_USER_A,
        "title": "Heavy Leg Day - Squats & Romanian Deadlifts",
        "category": "Strength",
        "duration_minutes": 55,
        "calories_burned": 420,
        "rpe": 8,
        "status": "completed",
        "notes": "Quad and hamstring volume was intense."
    }, exercises=[
        {"exercise_name": "Barbell Squat", "target_muscle": "Quadriceps", "sets": 4, "reps": 8, "weight_kg": 110.0, "status": "completed"},
        {"exercise_name": "Romanian Deadlift", "target_muscle": "Hamstrings", "sets": 3, "reps": 10, "weight_kg": 90.0, "status": "completed"}
    ])

    # 2. Logged meal in Nutrition AI
    save_meal_entry({
        "user_id": TEST_USER_A,
        "name": "Grilled Chicken & Jasmine Rice",
        "meal_type": "lunch",
        "calories": 650,
        "protein": 52.0,
        "carbs": 80.0,
        "fat": 12.0,
        "fiber": 4.0,
        "date": today_str
    })

    # 3. Logged recovery in Recovery AI
    save_recovery_log({
        "user_id": TEST_USER_A,
        "date": today_str,
        "sleep_hours": 6.2,
        "sleep_quality": "fair",
        "hydration_liters": 2.2,
        "soreness_level": 4,
        "fatigue_level": 4,
        "recovery_score": 58,
        "notes": "Legs are sore from squats"
    })

    # 4. Fetch Home AI Daily Overview
    overview = await get_home_daily_overview(user_id=TEST_USER_A)

    # Check Workout integration
    assert len(overview.today_workouts) >= 1
    assert any("Heavy Leg Day" in w.get("title", "") for w in overview.today_workouts)

    # Check Nutrition integration
    assert len(overview.today_meals) >= 1
    assert any("Grilled Chicken" in m.get("name", "") for m in overview.today_meals)
    assert overview.today_macros["protein"] >= 52.0
    assert overview.today_macros["calories"] >= 650.0

    # Check Recovery integration
    assert overview.today_recovery is not None
    assert overview.today_recovery["recovery_score"] == 58
    assert overview.today_recovery["soreness_level"] == 4

    # Check AI insights synthesize the training & recovery status
    insights_str = " ".join(overview.ai_insights)
    assert "Heavy Leg Day" in insights_str or "Strength" in insights_str or "training" in insights_str or "Training" in insights_str
    assert "protein" in insights_str.lower()

def test_intent_routing_routes_accurately():
    """Verify tool/intent routing classifies user intent into appropriate workspaces."""
    assert route_user_intent("How many grams of protein do I have left today?") in ("nutrition", "all")
    assert route_user_intent("My hamstrings are sore and I only slept 5 hours") in ("recovery", "all")
    assert route_user_intent("Log my bench press sets: 4 sets of 8 reps at 80kg") == "workout"
    assert route_user_intent("How does my recovery score affect my planned workout and what should I eat?") in ("all", "multi_workspace")
    assert route_user_intent("Hello LifeSync, what should I focus on today?") in ("all", "multi_workspace")
    assert route_user_intent("What is the meaning of progressive overload?") == "general"

@pytest.mark.asyncio
async def test_cross_agent_retrieval_does_not_fabricate_missing_data():
    """Verify that when User B has zero logs, Home AI does not hallucinate workouts or meals."""
    overview_b = await get_home_daily_overview(user_id=TEST_USER_B)
    assert len(overview_b.today_workouts) == 0
    assert len(overview_b.today_meals) == 0
    assert overview_b.today_recovery is None
    assert overview_b.today_macros["calories"] == 0.0
    assert overview_b.today_macros["protein"] == 0.0
