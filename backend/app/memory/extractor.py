import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Generic phrases that shouldn't repeatedly spawn redundant goal nodes
GENERIC_GOAL_PHRASES = {
    "get fit", "be fit", "stay fit", "be healthy", "live healthy",
    "work out", "exercise", "train", "start", "do better", "feel better",
    "get in shape", "stay in shape", "be active", "stay active",
    "lose weight", "gain muscle", "build muscle", "eat better", "eat healthy",
    "exercise more"
}

# Conversational non-goal phrases to ignore when preceded by "i want to"
CONVERSATIONAL_EXCLUSIONS = {
    "know", "ask", "see", "check", "find", "understand", "learn", "talk",
    "chat", "tell", "say", "try", "make sure", "have", "discuss", "start with",
    "look into", "think about", "wonder", "get advice", "get a tip", "get some tips",
    "get one simple tip", "get help", "hear", "read"
}

def is_generic_goal(title: str) -> bool:
    """Check if a goal title is an overly generic phrase like 'get fit' or 'stay healthy'."""
    clean = re.sub(r"^(user\s+goal:\s*|my\s+goal\s+is\s+(?:to\s+)?|to\s+)", "", title.lower().strip()).strip()
    clean = re.sub(r"[^\w\s]", "", clean).strip()
    return clean in GENERIC_GOAL_PHRASES or (len(clean.split()) <= 2 and any(w in clean for w in ["fit", "healthy", "shape"]))

# Patterns for explicit statements
GOAL_PATTERNS = [
    r"(?:my\s+(?:fitness\s+|primary\s+)?goal\s+is\s+(?:to\s+)?|aiming\s+to\s+|working\s+towards\s+|targeting\s+|goal:\s*)([^.,;\n]+)",
    r"(?:trying\s+to\s+reach\s+)([^.,;\n]+)",
    r"(?:bench\s+press\s+goal|squat\s+goal|deadlift\s+goal|running\s+goal|10k\s+goal|marathon\s+goal)\s*:?\s*([^.,;\n]+)",
    r"(?:i\s+want\s+to\s+(?:run|bench|squat|deadlift|lose|gain|build|achieve|reach|train\s+for|compete\s+in|hit))\s+([^.,;\n]+)",
    r"(?:i\s+want\s+to\s+)([^.,;\n]+)"
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
            content = m.strip() if isinstance(m, str) else m[0].strip()
            # Strip trailing conversational requests
            content = re.sub(r"\s+(?:give me|tell me|help me|can you|how do i).*$", "", content, flags=re.IGNORECASE).strip()
            words = content.split()
            if not words or len(content) <= 3:
                continue
            # Filter out non-goal conversational inquiries like "i want to know/ask..."
            content_lower = content.lower()
            if words[0] in CONVERSATIONAL_EXCLUSIONS or any(content_lower.startswith(excl) for excl in CONVERSATIONAL_EXCLUSIONS):
                continue
            facts.append({
                "fact_type": "goal",
                "content": f"User goal: {content}",
                "provenance": "explicit_user_statement",
                "confidence": 1.0,
                "tags": ["goal", "target"]
            })
            break
        if facts:
            break


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
