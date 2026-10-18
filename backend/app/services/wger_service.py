import logging
import time
import httpx
from typing import List, Dict, Any, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Category mapping ID -> Name and Name -> ID
WGER_CATEGORIES: Dict[str, int] = {
    "abs": 10,
    "arms": 8,
    "back": 12,
    "calves": 14,
    "cardio": 15,
    "chest": 11,
    "legs": 9,
    "shoulders": 13
}

# Cache structure: data + timestamp
_cache: Dict[str, Any] = {
    "exercises": [],
    "last_fetched": 0,
    "categories": []
}
CACHE_TTL_SECONDS = 3600  # 1 hour in-memory cache

def _get_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    if settings.WGER_API_KEY:
        headers["Authorization"] = f"Token {settings.WGER_API_KEY}"
    return headers

def _parse_exercise_item(item: Dict[str, Any], source: str = "wger_verified") -> Optional[Dict[str, Any]]:
    """Extract English name, description, category, muscles, equipment from raw wger JSON."""
    translations = item.get("translations", [])
    name = None
    description = ""
    
    # Prefer English translation (language 2 in wger) or first available with name
    for t in translations:
        if t.get("name"):
            name = t.get("name")
            description = t.get("description", "")
            if t.get("language") == 2:
                break

    if not name:
        return None

    # Clean description HTML tags
    clean_desc = (
        description.replace("<p>", "")
        .replace("</p>", "\n")
        .replace("<ul>", "")
        .replace("</ul>", "")
        .replace("<li>", "• ")
        .replace("</li>", "\n")
        .replace("<br>", "\n")
        .replace("<br/>", "\n")
        .strip()
    )

    category_obj = item.get("category")
    category_name = "General"
    if isinstance(category_obj, dict):
        category_name = category_obj.get("name", "General")
    elif isinstance(category_obj, str):
        category_name = category_obj

    muscles = [
        m.get("name") for m in item.get("muscles", [])
        if isinstance(m, dict) and m.get("name")
    ]
    equipment = [
        eq.get("name") for eq in item.get("equipment", [])
        if isinstance(eq, dict) and eq.get("name")
    ]

    return {
        "id": str(item.get("id")),
        "name": name,
        "description": clean_desc,
        "category": category_name,
        "muscles": muscles,
        "equipment": equipment,
        "source": source
    }

async def fetch_exercises(
    limit: int = 100,
    offset: int = 0,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch verified exercises from official wger API with caching, pagination,
    and category filtering.
    """
    global _cache
    now = time.time()

    # If general list is cached and fresh, and no category filter requested, return from cache
    if not category and _cache["exercises"] and (now - _cache["last_fetched"] < CACHE_TTL_SECONDS):
        return _cache["exercises"][offset: offset + limit]

    url = "https://wger.de/api/v2/exerciseinfo/"
    params: Dict[str, Any] = {"limit": min(limit, 100), "offset": offset}
    if category:
        cat_lower = category.lower().strip()
        cat_id = WGER_CATEGORIES.get(cat_lower)
        if cat_id:
            params["category"] = cat_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                raw_results = data.get("results", [])
                formatted = []
                for item in raw_results:
                    parsed = _parse_exercise_item(item, source="wger_verified")
                    if parsed:
                        formatted.append(parsed)

                # Update cache if general query
                if not category and offset == 0:
                    _cache["exercises"] = formatted
                    _cache["last_fetched"] = now

                return formatted
            elif resp.status_code == 429:
                logger.warning("wger API rate limit hit (HTTP 429). Returning local cache.")
            else:
                logger.error(f"wger API error: HTTP {resp.status_code}")
    except httpx.TimeoutException:
        logger.warning("wger API request timed out (10s). Using fallback.")
    except Exception as e:
        logger.error(f"Error fetching wger exercises: {e}")

    # Fallback to local cache or curated backup, strictly tagged as local_cache
    if _cache["exercises"]:
        return _cache["exercises"][offset: offset + limit]

    return _get_curated_fallback_exercises()

async def get_exercise_by_id(exercise_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single verified exercise by ID from wger API."""
    url = f"https://wger.de/api/v2/exerciseinfo/{exercise_id}/"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code == 200:
                return _parse_exercise_item(resp.json(), source="wger_verified")
            elif resp.status_code == 404:
                return None
    except Exception as e:
        logger.error(f"Error fetching wger exercise by id {exercise_id}: {e}")

    # Check local cache
    for ex in _cache.get("exercises", []):
        if ex.get("id") == str(exercise_id):
            return ex

    return None

async def search_exercises(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search exercises across wger API results by exercise name, target muscle, or category.
    """
    # Fetch exercises (up to 200 for searching)
    all_ex = await fetch_exercises(limit=100, category=category)
    if len(all_ex) < 50:
        # Fetch another page to have a wider search breadth
        more = await fetch_exercises(limit=100, offset=100, category=category)
        all_ex.extend(more)

    q = query.lower().strip()
    if not q:
        return all_ex[:50]

    matched = []
    for e in all_ex:
        name_match = q in e["name"].lower()
        muscle_match = any(q in m.lower() for m in e.get("muscles", []))
        cat_match = q in e.get("category", "").lower()
        if name_match or muscle_match or cat_match:
            matched.append(e)

    return matched

async def get_categories() -> List[Dict[str, Any]]:
    """Fetch official categories from wger."""
    global _cache
    if _cache["categories"]:
        return _cache["categories"]

    url = "https://wger.de/api/v2/exercisecategory/"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                _cache["categories"] = results
                return results
    except Exception as e:
        logger.error(f"Error fetching wger categories: {e}")

    return [
        {"id": 10, "name": "Abs"},
        {"id": 8, "name": "Arms"},
        {"id": 12, "name": "Back"},
        {"id": 14, "name": "Calves"},
        {"id": 15, "name": "Cardio"},
        {"id": 11, "name": "Chest"},
        {"id": 9, "name": "Legs"},
        {"id": 13, "name": "Shoulders"}
    ]

def _get_curated_fallback_exercises() -> List[Dict[str, Any]]:
    """Curated fallback exercises when wger API is unreachable. Strictly tagged as local_cache."""
    return [
        {"id": "c1", "name": "Barbell Bench Press", "category": "Chest", "muscles": ["Pectoralis major", "Triceps brachii"], "equipment": ["Barbell", "Bench"], "source": "local_cache", "description": "Flat bench barbell press for chest strength."},
        {"id": "c2", "name": "Barbell Deadlift", "category": "Back", "muscles": ["Erector spinae", "Gluteus maximus", "Hamstrings"], "equipment": ["Barbell"], "source": "local_cache", "description": "Conventional deadlift for posterior chain power."},
        {"id": "c3", "name": "Barbell Squat", "category": "Legs", "muscles": ["Quadriceps", "Gluteus maximus"], "equipment": ["Barbell", "Rack"], "source": "local_cache", "description": "Back squat for quadriceps and core drive."},
        {"id": "c4", "name": "Overhead Press", "category": "Shoulders", "muscles": ["Anterior deltoid", "Triceps brachii"], "equipment": ["Barbell"], "source": "local_cache", "description": "Standing barbell overhead shoulder press."},
        {"id": "c5", "name": "Pull-Up", "category": "Back", "muscles": ["Latissimus dorsi", "Biceps brachii"], "equipment": ["Pull-up bar"], "source": "local_cache", "description": "Pronated grip bodyweight pull-up."},
        {"id": "c6", "name": "Dumbbell Incline Press", "category": "Chest", "muscles": ["Upper Pectorals", "Triceps"], "equipment": ["Dumbbells", "Incline Bench"], "source": "local_cache", "description": "Incline dumbbell press targeting clavicular head."},
        {"id": "c7", "name": "Barbell Row", "category": "Back", "muscles": ["Latissimus dorsi", "Rhomboids"], "equipment": ["Barbell"], "source": "local_cache", "description": "Bent-over barbell row for back thickness."},
        {"id": "c8", "name": "Romanian Deadlift", "category": "Legs", "muscles": ["Hamstrings", "Gluteus maximus"], "equipment": ["Barbell"], "source": "local_cache", "description": "Hinge movement emphasizing hamstring stretch."},
        {"id": "c9", "name": "Lateral Raise", "category": "Shoulders", "muscles": ["Lateral deltoid"], "equipment": ["Dumbbells"], "source": "local_cache", "description": "Dumbbell side raises for deltoid width."},
        {"id": "c10", "name": "Triceps Rope Pushdown", "category": "Arms", "muscles": ["Triceps brachii"], "equipment": ["Cable machine"], "source": "local_cache", "description": "Cable pushdown focusing on lateral triceps head."}
    ]
