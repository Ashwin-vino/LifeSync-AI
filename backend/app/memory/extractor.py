import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Patterns for explicit statements
GOAL_PATTERNS = [
    r"(?:my goal is to|i want to|aiming to|targeting|goal:)\s+([^.,;\n]+)",
    r"(?:trying to reach|working towards)\s+([^.,;\n]+)",
    r"(?:bench press goal|squat goal|deadlift goal)\s+([^.,;\n]+)"
]

INJURY_OR_HEALTH_PATTERNS = [
    r"(?:i have (?:a|an)|suffering from|dealing with)\s+([^.,;\n]*(?:injury|pain|strain|tear|impingement|tightness|sprain)[^.,;\n]*)",
    r"(?:my\s+([^.,;\n]+)\s+(?:hurts|is sore|aches|is injured))",
    r"(?:allergic to|cannot eat|intolerant to)\s+([^.,;\n]+)"
]

PREFERENCE_PATTERNS = [
    r"(?:i prefer|i like to|i always|i usually)\s+([^.,;\n]+)",
    r"(?:i don't like|i avoid|i hate|never do)\s+([^.,;\n]+)",
    r"(?:my diet is|eating style is)\s+([^.,;\n]+)"
]

def extract_explicit_statements(text: str) -> List[Dict[str, Any]]:
    """
    Extract confirmed facts supported by explicit user statements.
    Returns list of facts with provenance='explicit_user_statement' and confidence=1.0.
    """
    facts = []
    text_lower = text.lower().strip()

    # Check for goals
    for pattern in GOAL_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for m in matches:
            content = m.strip()
            if len(content) > 4:
                facts.append({
                    "fact_type": "goal",
                    "content": f"User goal: {content}",
                    "provenance": "explicit_user_statement",
                    "confidence": 1.0,
                    "tags": ["goal", "target"]
                })

    # Check for health flags & injuries
    for pattern in INJURY_OR_HEALTH_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for m in matches:
            content = m.strip() if isinstance(m, str) else m[0].strip()
            if len(content) > 3:
                facts.append({
                    "fact_type": "injury",
                    "content": f"Health restriction / physical note: {content}",
                    "provenance": "explicit_user_statement",
                    "confidence": 1.0,
                    "tags": ["injury", "health_restriction"]
                })

    # Check for preferences
    for pattern in PREFERENCE_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for m in matches:
            content = m.strip()
            if len(content) > 4:
                facts.append({
                    "fact_type": "preference",
                    "content": f"User preference: {content}",
                    "provenance": "explicit_user_statement",
                    "confidence": 1.0,
                    "tags": ["preference"]
                })

    return facts

def extract_activity_fact_from_workout(
    title: str,
    category: str,
    duration: int,
    exercises: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create a verified activity memory fact from a logged workout session."""
    ex_names = [e.get("exercise_name") for e in exercises if e.get("exercise_name")]
    ex_str = f" including {', '.join(ex_names[:4])}" if ex_names else ""
    return {
        "fact_type": "workout_activity",
        "content": f"Completed {duration}m {category} session '{title}'{ex_str}.",
        "provenance": "verified_activity_record",
        "confidence": 1.0,
        "tags": ["workout", category.lower()]
    }

def extract_activity_fact_from_recovery(
    recovery_score: int,
    sleep_hours: float,
    sleep_quality: str,
    soreness_level: int
) -> Dict[str, Any]:
    """Create a verified activity memory fact from a logged recovery entry."""
    return {
        "fact_type": "recovery_status",
        "content": f"Logged readiness score {recovery_score}/100 with {sleep_hours}h {sleep_quality} sleep and soreness {soreness_level}/10.",
        "provenance": "verified_activity_record",
        "confidence": 1.0,
        "tags": ["recovery", "biometrics"]
    }
