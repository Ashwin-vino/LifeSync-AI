import pytest
import asyncio
from datetime import date
from backend.app.memory.memory_manager import MemoryManager
from backend.app.memory.graph_service import (
    get_graph,
    delete_user_graph_data,
    get_graph_context_for_prompt
)
from backend.app.database.supabase_client import get_supabase
from backend.app.services.gemini_service import generate_chat_response

TEST_USER = "test_user_cross_agent"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Clean up test user data before and after each test."""
    sb = get_supabase()
    
    def cleanup():
        try:
            sb.table("memory_facts").delete().eq("user_id", TEST_USER).execute()
            sb.table("workouts").delete().eq("user_id", TEST_USER).execute()
            sb.table("meals").delete().eq("user_id", TEST_USER).execute()
            sb.table("recovery_logs").delete().eq("user_id", TEST_USER).execute()
            sb.table("chat_messages").delete().eq("user_id", TEST_USER).execute()
            delete_user_graph_data(TEST_USER)
        except Exception as e:
            print("Cleanup notice:", e)

    cleanup()
    MemoryManager.initialize()
    yield
    cleanup()

def test_goal_stated_in_one_chat_is_recalled_in_new_chat():
    """
    Verify that an explicit goal stated in one conversation is extracted,
    vectorized with Gemini 768-dim embeddings, stored in Supabase & FalkorDB,
    and retrieved in a brand new chat context in another workspace.
    """
    sb = get_supabase()

    # 1. User explicitly states their goal in Chat 1 (Home workspace)
    user_statement = "My goal is to bench press 100kg and reach 12% body fat"
    MemoryManager.process_incoming_user_message(user_id=TEST_USER, message=user_statement)

    # 2. Verify Supabase write succeeded with explicit provenance
    sb_facts = sb.table("memory_facts").select("*").eq("user_id", TEST_USER).execute()
    assert len(sb_facts.data) >= 1, "Memory fact must be written to Supabase"
    fact = sb_facts.data[0]
    assert fact["fact_type"] == "goal"
    assert "100kg" in fact["content"]
    assert fact["provenance"] == "explicit_user_statement"
    assert fact["confidence"] == 1.0
    assert fact["embedding"] is not None, "Semantic vector embedding must be generated"

    # 3. Verify FalkorDB graph write succeeded
    g = get_graph()
    graph_res = g.query(f"""
        MATCH (u:User {{id: '{TEST_USER}'}})-[:REMINDED_OF]->(f:MemoryFact)
        RETURN f.content, f.provenance, f.confidence
    """)
    assert len(graph_res.result_set) >= 1, "Memory fact must be linked in FalkorDB graph"
    assert "100kg" in graph_res.result_set[0][0]

    # 4. In a brand new conversation in a different workspace (Nutrition),
    # query context for a nutrition question.
    nutrition_query = "What macro targets should I eat to fuel my bench press progression?"
    context = MemoryManager.get_relevant_context(
        user_id=TEST_USER,
        workspace="nutrition",
        current_message=nutrition_query
    )

    # 5. Assert that the goal from Chat 1 is retrieved into the prompt context
    assert "100kg" in context, "Goal stated in Chat 1 must be retrieved in Nutrition context"
    assert "EXPLICIT_USER_STATEMENT" in context or "ACTIVE USER GOALS" in context

@pytest.mark.asyncio
async def test_completed_workout_available_to_nutrition_and_recovery_ai():
    """
    Verify that a completed workout logged in the Workout workspace is
    immediately accessible to Nutrition AI and Recovery AI with volume and fatigue details.
    """
    sb = get_supabase()

    # 1. Log a completed strength workout session
    workout_data = {
        "title": "Chest & Triceps Hypertrophy",
        "category": "Strength",
        "duration_minutes": 55,
        "calories_burned": 420,
        "notes": "Targeted chest and triceps with heavy volume"
    }
    exercises = [
        {"exercise_name": "Barbell Bench Press", "sets": 4, "reps": 8, "weight_kg": 85.0},
        {"exercise_name": "Incline Dumbbell Press", "sets": 3, "reps": 10, "weight_kg": 32.0}
    ]

    saved_workout = MemoryManager.record_completed_workout(
        workout_data=workout_data,
        exercises=exercises,
        user_id=TEST_USER
    )

    # 2. Verify Supabase write succeeded
    assert saved_workout["id"] is not None
    assert len(saved_workout["workout_exercises"]) == 2

    # 3. Verify FalkorDB graph relationship:
    # (:User)-[:USER_COMPLETED_WORKOUT]->(:WorkoutSession)-[:WORKOUT_CONTAINS_EXERCISE]->(:Exercise)
    g = get_graph()
    w_res = g.query(f"""
        MATCH (u:User {{id: '{TEST_USER}'}})-[:USER_COMPLETED_WORKOUT]->(w:WorkoutSession)
        MATCH (w)-[:WORKOUT_CONTAINS_EXERCISE]->(e:Exercise)
        RETURN w.title, w.duration, collect(e.name)
    """)
    assert len(w_res.result_set) >= 1, "WorkoutSession and Exercise nodes must be linked in graph"
    assert "Chest & Triceps Hypertrophy" in w_res.result_set[0][0]
    assert "Barbell Bench Press" in w_res.result_set[0][2]

    # 4. Verify context retrieved by Nutrition AI
    nutrition_context = MemoryManager.get_relevant_context(
        user_id=TEST_USER,
        workspace="nutrition",
        current_message="How should I adjust my post-workout meal today?"
    )
    assert "Chest & Triceps Hypertrophy" in nutrition_context
    assert "Barbell Bench Press" in nutrition_context or "COMPLETED WORKOUTS" in nutrition_context

    # 5. Verify context retrieved by Recovery AI
    recovery_context = MemoryManager.get_relevant_context(
        user_id=TEST_USER,
        workspace="recovery",
        current_message="Should I do intense cardio or active recovery tomorrow?"
    )
    assert "Chest & Triceps Hypertrophy" in recovery_context

def test_memory_inspection_correction_and_cross_layer_deletion():
    """
    Verify that stored memories can be inspected, corrected with updated embeddings,
    and cleanly deleted across both Supabase PostgreSQL and FalkorDB graph.
    """
    sb = get_supabase()

    # 1. Create explicit memory
    mem = MemoryManager.save_memory_fact(
        user_id=TEST_USER,
        fact_type="injury",
        content="Right shoulder tightness when benching above 80kg",
        provenance="explicit_user_statement",
        confidence=1.0,
        tags=["injury", "shoulder"]
    )
    fact_id = mem["id"]

    # 2. Inspect memory
    active_memories = MemoryManager.list_user_memories(user_id=TEST_USER, status="active")
    assert any(m["id"] == fact_id for m in active_memories), "Memory must be listed for inspection"

    # 3. Correct memory
    corrected_content = "Right shoulder is fully recovered; ready for normal bench volume"
    MemoryManager.correct_user_memory(user_id=TEST_USER, fact_id=fact_id, new_content=corrected_content)

    # Verify correction in Supabase
    updated_sb = sb.table("memory_facts").select("*").eq("id", fact_id).execute()
    assert updated_sb.data[0]["content"] == corrected_content
    assert updated_sb.data[0]["status"] == "corrected"

    # Verify correction in FalkorDB
    g = get_graph()
    updated_g = g.query(f"MATCH (f:MemoryFact {{id: '{fact_id}'}}) RETURN f.content")
    assert updated_g.result_set[0][0] == corrected_content

    # 4. Delete memory across storage layers
    MemoryManager.delete_user_memory(user_id=TEST_USER, fact_id=fact_id)

    # Verify deletion in Supabase
    del_sb = sb.table("memory_facts").select("*").eq("id", fact_id).execute()
    assert len(del_sb.data) == 0, "Memory must be deleted from Supabase"

    # Verify deletion in FalkorDB
    del_g = g.query(f"MATCH (f:MemoryFact {{id: '{fact_id}'}}) RETURN f")
    assert len(del_g.result_set) == 0, "Memory node must be deleted from FalkorDB graph"


def test_duplicate_goal_prevention_on_repeated_messages():
    """
    Verify that repeated generic messages like 'I want to get fit'
    do NOT create multiple Goal nodes for the user in FalkorDB.
    """
    g = get_graph()

    # User says "I want to get fit" twice in chat
    MemoryManager.process_incoming_user_message(user_id=TEST_USER, message="I want to get fit")
    MemoryManager.process_incoming_user_message(user_id=TEST_USER, message="I want to get fit. Give me one simple tip")

    # Verify only 1 active Goal node exists in FalkorDB graph
    res = g.query(f"""
        MATCH (u:User {{id: '{TEST_USER}'}})-[:USER_HAS_GOAL]->(goal:Goal)
        WHERE goal.status = 'active'
        RETURN goal.title
    """)
    assert len(res.result_set) == 1, f"Expected exactly 1 Goal node, but found {len(res.result_set)}"
    assert "fit" in res.result_set[0][0].lower()


def test_specific_goal_preserved_when_generic_goal_stated():
    """
    Verify that a distinct, specific goal (e.g. running a 10k race under 50 minutes in December)
    is never overwritten or displaced when a user later sends a generic message like 'I want to get fit'.
    """
    g = get_graph()

    # 1. User records a specific goal
    specific_title = "Running a 10k race under 50 minutes in December"
    MemoryManager.save_memory_fact(
        user_id=TEST_USER,
        fact_type="goal",
        content=specific_title,
        provenance="explicit_user_statement"
    )

    # 2. User later sends a generic conversational statement
    MemoryManager.process_incoming_user_message(
        user_id=TEST_USER,
        message="I want to get fit. Give me one simple tip"
    )

    # 3. Verify specific goal is preserved in FalkorDB and not overwritten
    res = g.query(f"""
        MATCH (u:User {{id: '{TEST_USER}'}})-[:USER_HAS_GOAL]->(goal:Goal)
        WHERE goal.status = 'active'
        RETURN goal.title
    """)
    titles = [row[0] for row in (res.result_set or [])]
    assert any("10k" in t for t in titles), "Specific 10k goal must be preserved in active goals"

    # 4. Verify context retrieval prioritizes the specific goal
    context = get_graph_context_for_prompt(user_id=TEST_USER)
    retrieved_titles = [item["title"] for item in context.get("goals", [])]
    assert len(retrieved_titles) >= 1
    assert "10k" in retrieved_titles[0], "Specific goal must be prioritized first in prompt context"


def test_retrieval_limits_and_prioritization_with_legacy_duplicates():
    """
    Verify that if legacy duplicate Goal nodes exist in FalkorDB, retrieval:
    1. Returns unique goals (no duplicates)
    2. Prioritizes specific goals first
    3. Prevents duplicates from consuming all five context slots
    """
    g = get_graph()

    # Simulate 6 legacy duplicate "User goal: get fit" nodes with different IDs in FalkorDB
    for i in range(6):
        g.query(f"""
            MERGE (u:User {{id: '{TEST_USER}'}})
            CREATE (goal:Goal {{
                id: 'legacy_dup_{i}',
                title: 'User goal: get fit',
                category: 'general',
                provenance: 'explicit_user_statement',
                status: 'active',
                timestamp: {1000 + i * 10}
            }})
            CREATE (u)-[:USER_HAS_GOAL]->(goal)
        """)

    # Also insert 1 specific goal with an older timestamp
    g.query(f"""
        MERGE (u:User {{id: '{TEST_USER}'}})
        CREATE (goal:Goal {{
            id: 'specific_10k_legacy',
            title: 'Running a 10k race under 50 minutes in December',
            category: 'cardio',
            provenance: 'explicit_user_statement',
            status: 'active',
            timestamp: 500
        }})
        CREATE (u)-[:USER_HAS_GOAL]->(goal)
    """)

    # Retrieve prompt context
    context = get_graph_context_for_prompt(user_id=TEST_USER)
    goals = context.get("goals", [])

    # Assertions
    assert len(goals) <= 5, "Context must not exceed 5 slots"
    # Duplicates must be collapsed to 1 unique entry
    titles = [item["title"] for item in goals]
    fit_count = sum(1 for t in titles if "get fit" in t.lower())
    assert fit_count == 1, f"Expected exactly 1 'get fit' entry in context, found {fit_count}"

    # Specific goal must be prioritized at position 0 despite older timestamp
    assert "10k" in goals[0]["title"], f"Specific goal should be first in context, but got: {goals[0]['title']}"


def test_conversational_messages_not_extracted_as_goals():
    """
    Verify that ordinary conversational messages with 'I want to ...'
    (like asking a question or asking for advice) are not aggressively extracted as goals.
    """
    from backend.app.memory.extractor import extract_explicit_statements

    conversational_messages = [
        "I want to ask a question about creatine",
        "I want to know if I should stretch before working out",
        "I want to check my heart rate zones",
        "I want to get advice on proper squat depth",
        "I want to discuss my recovery score",
        "I want to make sure I am doing this correctly"
    ]

    for msg in conversational_messages:
        facts = extract_explicit_statements(msg)
        goal_facts = [f for f in facts if f.get("fact_type") == "goal"]
        assert len(goal_facts) == 0, f"Conversational message '{msg}' was improperly extracted as goal: {goal_facts}"

