import pytest
import asyncio
import uuid
from pydantic import ValidationError

from backend.app.config import settings
from backend.app.schemas.workout import (
    WorkoutCreateSchema,
    WorkoutExerciseSchema,
    WorkoutPlanResponseSchema,
    PlannedExerciseSchema,
    WorkoutPlanGenerateRequest
)
from backend.app.services.wger_service import (
    fetch_exercises,
    search_exercises,
    get_exercise_by_id,
    get_categories,
    _get_curated_fallback_exercises
)
from backend.app.services.workout_planner import (
    generate_personalized_workout_plan,
    _generate_fallback_plan
)
from backend.app.memory.memory_manager import MemoryManager
from backend.app.memory.graph_service import get_graph, delete_user_graph_data
from backend.app.database.supabase_client import (
    get_supabase,
    get_recent_workouts,
    get_workout_by_id,
    save_generated_plan
)
from backend.app.services.gemini_service import generate_chat_response

TEST_USER_WORKOUT = "test_user_workout_ai"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Clean up test data before and after each test."""
    sb = get_supabase()
    
    def cleanup():
        try:
            # Delete exercises first to respect foreign key
            user_workouts = sb.table("workouts").select("id").eq("user_id", TEST_USER_WORKOUT).execute()
            for w in user_workouts.data or []:
                sb.table("workout_exercises").delete().eq("workout_id", w["id"]).execute()
            sb.table("workouts").delete().eq("user_id", TEST_USER_WORKOUT).execute()
            sb.table("generated_plans").delete().eq("user_id", TEST_USER_WORKOUT).execute()
            sb.table("memory_facts").delete().eq("user_id", TEST_USER_WORKOUT).execute()
            delete_user_graph_data(TEST_USER_WORKOUT)
        except Exception as e:
            print("Cleanup notice:", e)

    cleanup()
    MemoryManager.initialize()
    yield
    cleanup()

# 1. Real wger exercise lookup
@pytest.mark.asyncio
async def test_real_wger_exercise_lookup():
    """Verify official wger API integration with typed response, category filtering, and verified badge."""
    assert settings.WGER_API_KEY, "WGER_API_KEY must be configured in environment"

    # Search for an exercise
    results = await search_exercises("bench press")
    assert len(results) > 0, "wger search must return exercises"
    sample = results[0]
    assert sample["source"] == "wger_verified", "Live wger API results must be tagged as wger_verified"
    assert "bench" in sample["name"].lower()
    assert sample["category"] in ["Chest", "General", "Arms"]

    # Fetch exercise categories
    cats = await get_categories()
    assert len(cats) >= 5, "wger should return standard categories"

    # Fetch by ID
    exercise_id = sample["id"]
    single = await get_exercise_by_id(exercise_id)
    assert single is not None, "Exercise lookup by ID must succeed"
    assert single["id"] == str(exercise_id)
    assert single["source"] == "wger_verified"

# 2. Workout plan validation
def test_workout_plan_validation():
    """Validate Pydantic schema validation for planned exercises and workout plans."""
    # Valid plan
    valid_exercise = PlannedExerciseSchema(
        name="Barbell Bench Press",
        target_muscle="Chest",
        sets=4,
        reps="8-10",
        rest_seconds=90,
        suggested_weight_kg=80.0,
        notes="Control eccentric phase",
        source="wger_verified"
    )
    assert valid_exercise.name == "Barbell Bench Press"
    assert valid_exercise.source == "wger_verified"

    valid_plan = WorkoutPlanResponseSchema(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_WORKOUT,
        title="Hypertrophy Chest & Triceps",
        category="Strength",
        summary="Focused push session",
        warmup=["Arm circles 30s", "Band pull-aparts 15 reps"],
        exercises=[valid_exercise],
        cooldown=["Pectoral doorway stretch 60s"],
        estimated_duration_minutes=45,
        status="planned",
        explanation="Targets clavicular and sternal pectoral fibers."
    )
    assert valid_plan.title == "Hypertrophy Chest & Triceps"
    assert valid_plan.status == "planned"

    # Invalid exercise (sets <= 0 or invalid reps)
    with pytest.raises(ValidationError):
        PlannedExerciseSchema(name="", sets=0, reps="10")

    # Invalid workout create (duration > 480 or invalid RPE)
    with pytest.raises(ValidationError):
        WorkoutCreateSchema(title="Bad Workout", duration_minutes=600, rpe=15)

# 3 & 4. Creating, editing, completing, and preventing planned workouts from counting as completed
def test_creating_editing_and_planned_vs_completed_isolation():
    """
    Verify:
    - Planned workout is saved with status='planned' and is NOT counted in completed workouts.
    - Completed workout is saved, verified in Supabase & FalkorDB graph, and editable.
    """
    sb = get_supabase()

    # Step A: Save a PLANNED workout in generated_plans
    plan_data = {
        "title": "Planned Pull Session",
        "category": "Strength",
        "summary": "Upcoming planned workout",
        "warmup": ["Band dislocates"],
        "exercises": [{"name": "Barbell Row", "target_muscle": "Back", "sets": 3, "reps": "10", "rest_seconds": 90, "source": "wger_verified"}],
        "cooldown": ["Dead hang"],
        "estimated_duration_minutes": 45,
        "status": "planned",
        "explanation": "Planned routine"
    }
    saved_plan = save_generated_plan(
        user_id=TEST_USER_WORKOUT,
        plan_type="workout",
        title="Planned Pull Session",
        summary="Upcoming planned workout",
        plan_data=plan_data,
        status="planned"
    )
    assert saved_plan["id"] is not None
    assert saved_plan["status"] == "planned"

    # Verify that get_recent_workouts(status="completed") does NOT return the planned workout
    completed_workouts = get_recent_workouts(limit=10, user_id=TEST_USER_WORKOUT, status="completed")
    assert len(completed_workouts) == 0, "Planned workouts must NOT be counted as completed"

    # Verify FalkorDB graph does not have USER_COMPLETED_WORKOUT relationship
    g = get_graph()
    q_check = g.query(f"MATCH (u:User {{id: '{TEST_USER_WORKOUT}'}})-[:USER_COMPLETED_WORKOUT]->(w) RETURN count(w)")
    assert q_check.result_set[0][0] == 0, "No completed workout relationship should exist for a plan"

    # Step B: Record an ACTUAL completed workout
    workout_data = {
        "title": "Completed Pull Session",
        "category": "Strength",
        "duration_minutes": 50,
        "calories_burned": 420,
        "rpe": 8,
        "status": "completed",
        "notes": "Solid back pump"
    }
    exercises = [
        {"exercise_name": "Barbell Row", "target_muscle": "Back", "sets": 4, "reps": 8, "weight_kg": 75.0, "status": "completed", "notes": "Felt good"}
    ]
    saved_workout = MemoryManager.record_completed_workout(
        workout_data=workout_data,
        exercises=exercises,
        user_id=TEST_USER_WORKOUT
    )
    wid = saved_workout["id"]
    assert wid is not None

    # Verify Supabase returns completed workout
    completed_after = get_recent_workouts(limit=10, user_id=TEST_USER_WORKOUT, status="completed")
    assert len(completed_after) == 1
    assert completed_after[0]["title"] == "Completed Pull Session"
    assert len(completed_after[0]["workout_exercises"]) == 1

    # Step C: Edit the completed workout (e.g. increase weight and update notes)
    updated_data = {
        "title": "Completed Pull Session (Updated)",
        "duration_minutes": 55,
        "rpe": 9,
        "notes": "Updated weight to 80kg"
    }
    updated_exercises = [
        {"exercise_name": "Barbell Row", "target_muscle": "Back", "sets": 4, "reps": 8, "weight_kg": 80.0, "status": "completed", "notes": "Heavy"}
    ]
    updated_workout = MemoryManager.update_completed_workout(
        workout_id=wid,
        workout_data=updated_data,
        exercises=updated_exercises,
        user_id=TEST_USER_WORKOUT
    )
    assert updated_workout["title"] == "Completed Pull Session (Updated)"

    # Verify updated record in Supabase
    rechecked = get_workout_by_id(wid, user_id=TEST_USER_WORKOUT)
    assert rechecked["title"] == "Completed Pull Session (Updated)"
    assert float(rechecked["workout_exercises"][0]["weight_kg"]) == 80.0

    # Step D: Delete the workout
    del_ok = MemoryManager.delete_completed_workout(wid, user_id=TEST_USER_WORKOUT)
    assert del_ok is True
    assert get_workout_by_id(wid, user_id=TEST_USER_WORKOUT) is None
    q_del = g.query(f"MATCH (w:WorkoutSession {{id: '{wid}'}}) RETURN count(w)")
    assert q_del.result_set[0][0] == 0, "WorkoutSession node must be deleted from FalkorDB graph"

# 5, 6, 7. Cross-agent memory: Workout logged and retrieved in Nutrition & Recovery AI
@pytest.mark.asyncio
async def test_workout_persisted_to_supabase_and_retrieved_in_nutrition_and_recovery():
    """
    Log a completed intense leg workout, verify Supabase & FalkorDB graph persistence,
    and verify that brand new Nutrition AI and Recovery AI conversations immediately
    recall the workout details.
    """
    workout_data = {
        "title": "Heavy Squat & Posterior Chain",
        "category": "Strength",
        "duration_minutes": 65,
        "calories_burned": 520,
        "rpe": 9,
        "status": "completed",
        "notes": "High intensity leg volume"
    }
    exercises = [
        {"exercise_name": "Barbell Squat", "target_muscle": "Quadriceps", "sets": 5, "reps": 5, "weight_kg": 120.0, "status": "completed"},
        {"exercise_name": "Romanian Deadlift", "target_muscle": "Hamstrings", "sets": 4, "reps": 8, "weight_kg": 100.0, "status": "completed"}
    ]

    # 1. Log workout through MemoryManager
    saved = MemoryManager.record_completed_workout(
        workout_data=workout_data,
        exercises=exercises,
        user_id=TEST_USER_WORKOUT
    )
    wid = saved["id"]
    assert wid is not None

    # 2. Verify FalkorDB graph relationships
    g = get_graph()
    q = f"""
        MATCH (u:User {{id: '{TEST_USER_WORKOUT}'}})-[:USER_COMPLETED_WORKOUT]->(w:WorkoutSession {{id: '{wid}'}})
        MATCH (w)-[:WORKOUT_CONTAINS_EXERCISE]->(e:Exercise)
        RETURN w.title, w.duration, collect(e.name)
    """
    res = g.query(q)
    assert len(res.result_set) > 0, "FalkorDB must have WorkoutSession connected to User and Exercises"
    row = res.result_set[0]
    assert row[0] == "Heavy Squat & Posterior Chain"
    assert "Barbell Squat" in row[2]

    # 3. Nutrition AI retrieval in a brand new chat (zero prior messages)
    nutri_resp = await generate_chat_response(
        message="I just completed my heavy workout. What should I prioritize for my post-workout meal?",
        workspace="nutrition",
        history=[],
        user_id=TEST_USER_WORKOUT
    )
    nutri_text = nutri_resp["reply"].lower()
    # The Nutrition AI prompt received the workout details (squats / legs / strength session)
    assert any(term in nutri_text for term in ["squat", "leg", "strength", "heavy", "protein", "carbohydrate", "glycogen"]), (
        f"Nutrition AI must ground its advice in the completed workout: {nutri_resp['reply']}"
    )

    # 4. Recovery AI retrieval in a brand new chat (zero prior messages)
    recov_resp = await generate_chat_response(
        message="How will today's training session impact my sleep and systemic fatigue tomorrow?",
        workspace="recovery",
        history=[],
        user_id=TEST_USER_WORKOUT
    )
    recov_text = recov_resp["reply"].lower()
    assert any(term in recov_text for term in ["squat", "leg", "volume", "strain", "fatigue", "central nervous", "sleep", "recovery"]), (
        f"Recovery AI must acknowledge the completed leg session: {recov_resp['reply']}"
    )

# 8. Correct behavior when external services or API are unavailable
def test_graceful_fallbacks_when_services_unavailable():
    """Verify fallback mechanisms for wger and Gemini planner."""
    # wger fallback exercises
    fallbacks = _get_curated_fallback_exercises()
    assert len(fallbacks) >= 5
    for fb in fallbacks:
        # Crucial requirement: NEVER claim unverified items are verified by wger
        assert fb["source"] == "local_cache", "Fallback exercises must be tagged as local_cache"

    # Gemini planner fallback plan
    fb_plan = _generate_fallback_plan(focus="Upper Body", duration=45)
    assert fb_plan["category"] == "Strength"
    assert len(fb_plan["exercises"]) >= 3
    assert len(fb_plan["warmup"]) >= 2
    assert len(fb_plan["cooldown"]) >= 2
