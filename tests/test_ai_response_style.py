import pytest
import re
from backend.app.services.ai_style import (
    clean_ai_response,
    SYSTEM_PROMPTS,
    CORE_STYLE_INSTRUCTIONS,
    FRIENDLY_ERROR_FALLBACK,
    FRIENDLY_MISSING_GOAL_PROMPT,
    BANNED_PHRASES
)
from backend.app.services.gemini_service import generate_chat_response
from backend.app.services.workout_planner import _generate_fallback_plan
from backend.app.routers.nutrition import get_nutrition_recommendations
from backend.app.routers.recovery import get_recovery_recommendations
from backend.app.routers.home import get_home_daily_overview

def test_clean_ai_response_sanitizes_banned_phrases():
    """Verify that banned robotic boilerplate is scrubbed from AI responses."""
    bad_text = (
        "Currently, your profile does not have baseline goals configured. "
        "To establish your baseline framework and universal performance fundamentals, "
        "we need to calibrate your metrics."
    )
    cleaned = clean_ai_response(bad_text)
    for phrase in BANNED_PHRASES:
        assert not re.search(phrase, cleaned, re.IGNORECASE), f"Banned phrase '{phrase}' found in cleaned response"
    assert "baseline" not in cleaned.lower()
    assert "universal performance" not in cleaned.lower()

def test_clean_ai_response_removes_model_prefixes():
    """Verify that system/assistant prefixes are cleanly stripped."""
    assert clean_ai_response("LifeSync AI: Here is your quick tip for today.") == "Here is your quick tip for today."
    assert clean_ai_response("Assistant: Drink some water!") == "Drink some water!"
    assert clean_ai_response("Bot: Keep it up! 💪") == "Keep it up! 💪"

def test_clean_ai_response_handles_empty():
    """Verify empty or null returns the friendly error fallback."""
    assert clean_ai_response("") == FRIENDLY_ERROR_FALLBACK
    assert clean_ai_response(None) == FRIENDLY_ERROR_FALLBACK

def test_system_prompts_for_all_workspaces():
    """Verify that all four workspaces have friendly system prompts configured."""
    for ws in ["home", "workout", "nutrition", "recovery"]:
        assert ws in SYSTEM_PROMPTS
        prompt = SYSTEM_PROMPTS[ws]
        assert "RESPONSE STYLE RULES" in prompt
        assert "Brevity" in prompt or "short" in prompt.lower()
        assert "friendly" in prompt.lower()

def test_workout_fallback_plan_style():
    """Verify that fallback workout plans do not contain dense baseline jargon."""
    plan = _generate_fallback_plan("Chest & Triceps", 30)
    assert "(Structured Baseline)" not in plan["title"]
    assert "baseline" not in plan["title"].lower()
    assert "baseline" not in plan["summary"].lower()
    assert "baseline" not in plan["explanation"].lower()
    assert len(plan["summary"].split()) < 40, "Summary should be short and punchy"
    assert len(plan["explanation"].split()) < 40, "Explanation should be short and friendly"

@pytest.mark.asyncio
async def test_home_daily_overview_friendly_style():
    """Verify that Home AI readiness status and insights use friendly language."""
    overview = await get_home_daily_overview(user_id="default_user")
    assert "Prime Readiness (High Output Capacity)" not in overview.readiness_status
    assert "Recovering (Prioritize Restorative Work)" not in overview.readiness_status
    # Check insights are conversational
    for insight in overview.ai_insights:
        assert "baseline framework" not in insight.lower()
        assert "universal performance" not in insight.lower()

@pytest.mark.asyncio
async def test_chat_response_brevity_and_style():
    """Verify that live or fallback chat responses are concise, friendly, and jargon-free."""
    res = await generate_chat_response(
        message="What should I eat before my workout?",
        workspace="nutrition",
        user_id="default_user"
    )
    assert "reply" in res
    reply = res["reply"]
    words = reply.split()
    # Brevity: normal response should be punchy and under 120 words
    assert len(words) <= 120, f"Expected <= 120 words, got {len(words)}: {reply}"
    # Check no banned phrases
    for phrase in BANNED_PHRASES:
        assert not re.search(phrase, reply, re.IGNORECASE), f"Banned phrase '{phrase}' leaked in reply"
    # Friendly tone check
    assert not reply.startswith("AI:")
    assert not reply.startswith("Assistant:")

def test_clean_ai_response_handles_max_tokens_truncation():
    """Verify that responses truncated by MAX_TOKENS are trimmed cleanly rather than cutting off mid-sentence."""
    # Case 1: Multiple sentences where the second is chopped off mid-phrase
    text1 = "Commit to 20 minutes of daily exercise! It will build strong momentum and you will"
    cleaned1 = clean_ai_response(text1, finish_reason="MAX_TOKENS")
    assert cleaned1 == "Commit to 20 minutes of daily exercise!"

    # Case 2: Single sentence chopped off at a trailing connector word
    text2 = "Focus on moving your body for at least 30 minutes every"
    cleaned2 = clean_ai_response(text2, finish_reason="MAX_TOKENS")
    assert cleaned2.endswith(".")
    assert not cleaned2.endswith("every.")
    assert "Focus on moving your body for at least 30 minutes" in cleaned2

@pytest.mark.asyncio
async def test_chat_response_workout_tip_completeness():
    """Verify Workout AI response to 'I want to get fit. Give me one simple tip' finishes completely without truncation."""
    res = await generate_chat_response(
        message="I want to get fit. Give me one simple tip",
        workspace="workout",
        user_id="default_user"
    )
    assert "reply" in res
    reply = res["reply"].strip()
    words = reply.split()
    assert len(words) >= 10, f"Response too short: {reply}"
    assert len(words) <= 120, f"Response too long: {reply}"
    # Verify the reply terminates naturally with proper punctuation or emoji
    assert re.search(r"[\.!\?][\s\W]*$", reply) or any(reply.endswith(c) for c in (".", "!", "?", "💪", "😊", "🔥", "✨", "🏃‍♂️", "🥗")), f"Reply does not end with natural terminal punctuation/emoji: '{reply}'"
    # Ensure it didn't cut off on common dangling conjunctions
    assert not re.search(r"\b(every|and|or|with|to|for|the|a)\s*$", reply, re.IGNORECASE), f"Reply ends on dangling word: '{reply}'"


