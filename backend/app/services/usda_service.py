import logging
import time
import httpx
from typing import List, Dict, Any, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Search cache structure: query -> { timestamp, data }
_search_cache: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache

def _get_api_key() -> Optional[str]:
    return settings.USDA_API_KEY

def _parse_usda_food_item(item: Dict[str, Any], source: str = "usda_verified") -> Dict[str, Any]:
    """Extract standard macronutrients and fiber from USDA FoodData Central item."""
    nutrients: Dict[str, float] = {
        "calories": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "fiber": 0.0
    }

    # FoodData Central returns foodNutrients list
    for n in item.get("foodNutrients", []):
        name = n.get("nutrientName", "")
        val = float(n.get("value", 0.0) or 0.0)
        
        if name == "Energy" and val > 0 and nutrients["calories"] == 0:
            nutrients["calories"] = round(val, 1)
        elif "Protein" in name and nutrients["protein"] == 0:
            nutrients["protein"] = round(val, 1)
        elif "Carbohydrate" in name and nutrients["carbs"] == 0:
            nutrients["carbs"] = round(val, 1)
        elif "Total lipid (fat)" in name and nutrients["fat"] == 0:
            nutrients["fat"] = round(val, 1)
        elif "Fiber" in name and nutrients["fiber"] == 0:
            nutrients["fiber"] = round(val, 1)

    serving_size = float(item.get("servingSize", 100.0) or 100.0)
    serving_unit = item.get("servingSizeUnit", "g") or "g"
    brand_owner = item.get("brandOwner") or "Standard Reference"

    # Clean description
    raw_desc = item.get("description", "").title().strip()

    return {
        "fdcId": str(item.get("fdcId")),
        "description": raw_desc or "Food Item",
        "brandOwner": brand_owner,
        "servingSize": serving_size,
        "servingUnit": serving_unit,
        "calories": nutrients["calories"],
        "protein": nutrients["protein"],
        "carbs": nutrients["carbs"],
        "fat": nutrients["fat"],
        "fiber": nutrients["fiber"],
        "source": source
    }

async def search_foods(query: str, page_size: int = 15) -> List[Dict[str, Any]]:
    """
    Search official USDA FoodData Central database with caching,
    timeout handling, and fallback behavior.
    """
    q_clean = query.lower().strip()
    if not q_clean:
        return []

    # Check memory cache
    now = time.time()
    if q_clean in _search_cache:
        cached = _search_cache[q_clean]
        if now - cached["timestamp"] < CACHE_TTL_SECONDS:
            return cached["data"][:page_size]

    api_key = _get_api_key()
    if not api_key:
        logger.warning("USDA_API_KEY is not configured. Returning curated fallback.")
        return _search_fallback_foods(q_clean)[:page_size]

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": api_key,
        "query": query,
        "pageSize": min(page_size, 25),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("foods", []):
                    parsed = _parse_usda_food_item(item, source="usda_verified")
                    results.append(parsed)

                # Update cache
                _search_cache[q_clean] = {"timestamp": now, "data": results}
                return results[:page_size]
            elif resp.status_code == 429:
                logger.warning("USDA API rate limit reached (HTTP 429). Using fallback.")
            else:
                logger.error(f"USDA API error: HTTP {resp.status_code}")
    except httpx.TimeoutException:
        logger.warning("USDA API search timed out (10s). Using fallback.")
    except Exception as e:
        logger.error(f"Error searching USDA foods: {e}")

    # Fallback if network or API error
    return _search_fallback_foods(q_clean)[:page_size]

async def get_food_details(fdc_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete nutrition details for a specific USDA food by fdcId."""
    api_key = _get_api_key()
    if not api_key:
        return None

    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {"api_key": api_key}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return _parse_usda_food_item(resp.json(), source="usda_verified")
    except Exception as e:
        logger.error(f"Error fetching USDA food details for fdcId {fdc_id}: {e}")

    # Search in cache
    for entry in _search_cache.values():
        for item in entry.get("data", []):
            if item.get("fdcId") == str(fdc_id):
                return item

    return None

def _search_fallback_foods(query: str) -> List[Dict[str, Any]]:
    """Curated fallback foods when USDA API is unreachable. Explicitly labeled as ai_estimated."""
    all_fallbacks = [
        {"fdcId": "fb_1", "description": "Chicken Breast (Boneless, Skinless)", "brandOwner": "Standard Whole Food", "servingSize": 100.0, "servingUnit": "g", "calories": 165.0, "protein": 31.0, "carbs": 0.0, "fat": 3.6, "fiber": 0.0, "source": "ai_estimated"},
        {"fdcId": "fb_2", "description": "White Rice (Cooked, Long-Grain)", "brandOwner": "Standard Whole Food", "servingSize": 150.0, "servingUnit": "g", "calories": 195.0, "protein": 4.0, "carbs": 43.0, "fat": 0.4, "fiber": 0.6, "source": "ai_estimated"},
        {"fdcId": "fb_3", "description": "Whole Eggs (Large, Raw)", "brandOwner": "Standard Whole Food", "servingSize": 50.0, "servingUnit": "g", "calories": 72.0, "protein": 6.3, "carbs": 0.4, "fat": 4.8, "fiber": 0.0, "source": "ai_estimated"},
        {"fdcId": "fb_4", "description": "Greek Yogurt (Nonfat, Plain)", "brandOwner": "Standard Whole Food", "servingSize": 170.0, "servingUnit": "g", "calories": 100.0, "protein": 17.0, "carbs": 6.0, "fat": 0.7, "fiber": 0.0, "source": "ai_estimated"},
        {"fdcId": "fb_5", "description": "Oatmeal (Rolled Oats, Dry)", "brandOwner": "Standard Whole Food", "servingSize": 40.0, "servingUnit": "g", "calories": 150.0, "protein": 5.0, "carbs": 27.0, "fat": 2.5, "fiber": 4.0, "source": "ai_estimated"},
        {"fdcId": "fb_6", "description": "Salmon Fillet (Atlantic, Raw)", "brandOwner": "Standard Whole Food", "servingSize": 100.0, "servingUnit": "g", "calories": 208.0, "protein": 20.4, "carbs": 0.0, "fat": 13.4, "fiber": 0.0, "source": "ai_estimated"},
        {"fdcId": "fb_7", "description": "Whey Protein Isolate Powder", "brandOwner": "Standard Supplement", "servingSize": 30.0, "servingUnit": "g", "calories": 120.0, "protein": 25.0, "carbs": 1.5, "fat": 0.5, "fiber": 0.0, "source": "ai_estimated"},
        {"fdcId": "fb_8", "description": "Avocado (Fresh, Raw)", "brandOwner": "Standard Whole Food", "servingSize": 50.0, "servingUnit": "g", "calories": 80.0, "protein": 1.0, "carbs": 4.3, "fat": 7.3, "fiber": 3.4, "source": "ai_estimated"},
        {"fdcId": "fb_9", "description": "Sweet Potato (Baked with Skin)", "brandOwner": "Standard Whole Food", "servingSize": 100.0, "servingUnit": "g", "calories": 90.0, "protein": 2.0, "carbs": 20.7, "fat": 0.2, "fiber": 3.3, "source": "ai_estimated"},
        {"fdcId": "fb_10", "description": "Banana (Raw, Medium)", "brandOwner": "Standard Whole Food", "servingSize": 118.0, "servingUnit": "g", "calories": 105.0, "protein": 1.3, "carbs": 27.0, "fat": 0.3, "fiber": 3.1, "source": "ai_estimated"}
    ]
    q = query.lower()
    return [f for f in all_fallbacks if q in f["description"].lower() or q in f["brandOwner"].lower()]

# Convenient aliases
search_usda_foods = search_foods
_get_curated_fallback_foods = _search_fallback_foods
