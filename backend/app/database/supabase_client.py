import logging
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from backend.app.config import settings

logger = logging.getLogger(__name__)

_supabase: Optional[Client] = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        _supabase = create_client(settings.SUPABASE_URL, key)
    return _supabase

# Profile Operations
def get_user_profile(user_id: str = "default_user") -> Optional[Dict[str, Any]]:
    client = get_supabase()
    resp = client.table("profiles").select("*").eq("user_id", user_id).execute()
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    return None

def update_user_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    client = get_supabase()
    resp = client.table("profiles").upsert({"user_id": user_id, **data}).execute()
    return resp.data[0] if resp.data else {}

# Workout Operations
def get_recent_workouts(limit: int = 10, user_id: str = "default_user", status: Optional[str] = "completed") -> List[Dict[str, Any]]:
    client = get_supabase()
    query = client.table("workouts").select("*, workout_exercises(*)").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    resp = query.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []

def get_workout_by_id(workout_id: str, user_id: str = "default_user") -> Optional[Dict[str, Any]]:
    client = get_supabase()
    try:
        resp = client.table("workouts").select("*, workout_exercises(*)").eq("id", workout_id).eq("user_id", user_id).execute()
        return resp.data[0] if resp.data and len(resp.data) > 0 else None
    except Exception as e:
        logger.warning(f"Error getting workout by id {workout_id}: {e}")
        return None

def create_workout_entry(workout_data: Dict[str, Any], exercises: List[Dict[str, Any]], user_id: str = "default_user") -> Dict[str, Any]:
    client = get_supabase()
    effective_user = workout_data.get("user_id") or user_id
    workout_payload = {**workout_data, "user_id": effective_user}
    if "rpe" in workout_payload and workout_payload["rpe"] is not None:
        workout_payload["rpe"] = int(round(float(workout_payload["rpe"])))
    resp = client.table("workouts").insert(workout_payload).execute()
    workout = resp.data[0]
    
    saved_exercises = []
    if exercises:
        ex_payload = [{**ex, "workout_id": workout["id"]} for ex in exercises]
        ex_resp = client.table("workout_exercises").insert(ex_payload).execute()
        saved_exercises = ex_resp.data or []
        
    workout["workout_exercises"] = saved_exercises
    return workout

# Alias
save_workout_session = create_workout_entry

def update_workout_entry(workout_id: str, workout_data: Dict[str, Any], exercises: Optional[List[Dict[str, Any]]] = None, user_id: str = "default_user") -> Dict[str, Any]:
    client = get_supabase()
    # Update workout table
    clean_data = {k: v for k, v in workout_data.items() if v is not None}
    resp = client.table("workouts").update(clean_data).eq("id", workout_id).eq("user_id", user_id).execute()
    workout = resp.data[0] if resp.data else {}

    # If new exercises list provided, replace workout_exercises
    if exercises is not None:
        client.table("workout_exercises").delete().eq("workout_id", workout_id).execute()
        if exercises:
            ex_payload = [{**ex, "workout_id": workout_id} for ex in exercises]
            ex_resp = client.table("workout_exercises").insert(ex_payload).execute()
            workout["workout_exercises"] = ex_resp.data or []
        else:
            workout["workout_exercises"] = []
    else:
        # Fetch current exercises
        ex_resp = client.table("workout_exercises").select("*").eq("workout_id", workout_id).execute()
        workout["workout_exercises"] = ex_resp.data or []

    return workout

def delete_workout_entry(workout_id: str, user_id: str = "default_user") -> bool:
    client = get_supabase()
    client.table("workout_exercises").delete().eq("workout_id", workout_id).execute()
    client.table("workouts").delete().eq("id", workout_id).eq("user_id", user_id).execute()
    return True

# Generated Plans Operations
def save_generated_plan(
    user_id: str,
    plan_type: str,
    title: str,
    summary: str,
    plan_data: Dict[str, Any],
    status: str = "planned"
) -> Dict[str, Any]:
    client = get_supabase()
    payload = {
        "user_id": user_id,
        "plan_type": plan_type,
        "title": title,
        "summary": summary,
        "plan_data": plan_data,
        "status": status
    }
    resp = client.table("generated_plans").insert(payload).execute()
    return resp.data[0] if resp.data else {}

def get_active_workout_plan(user_id: str = "default_user") -> Optional[Dict[str, Any]]:
    client = get_supabase()
    resp = (
        client.table("generated_plans")
        .select("*")
        .eq("user_id", user_id)
        .eq("plan_type", "workout")
        .in_("status", ["planned", "in_progress"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data and len(resp.data) > 0 else None

def update_plan_status(plan_id: str, status: str, user_id: str = "default_user") -> bool:
    client = get_supabase()
    client.table("generated_plans").update({"status": status}).eq("id", plan_id).eq("user_id", user_id).execute()
    return True


# Nutrition / Meal Operations
def get_meals_by_date(date_str: str, user_id: str = "default_user") -> List[Dict[str, Any]]:
    client = get_supabase()
    resp = client.table("meals").select("*").eq("user_id", user_id).eq("date", date_str).order("created_at", desc=False).execute()
    return resp.data or []

def get_meal_by_id(meal_id: str, user_id: str = "default_user") -> Optional[Dict[str, Any]]:
    client = get_supabase()
    try:
        resp = client.table("meals").select("*").eq("id", meal_id).eq("user_id", user_id).execute()
        return resp.data[0] if resp.data and len(resp.data) > 0 else None
    except Exception as e:
        logger.warning(f"Error getting meal by id {meal_id}: {e}")
        return None

def log_meal_entry(meal_data: Dict[str, Any], user_id: str = "default_user") -> Dict[str, Any]:
    client = get_supabase()
    effective_user = meal_data.get("user_id") or user_id
    payload = {**meal_data, "user_id": effective_user}
    resp = client.table("meals").insert(payload).execute()
    return resp.data[0] if resp.data else {}

def update_meal_entry(meal_id: str, arg2: Any = None, arg3: Any = None, meal_data: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if meal_data is not None:
        data = meal_data
        uid = user_id or "default_user"
    elif isinstance(arg2, dict):
        data = arg2
        uid = user_id or arg3 or "default_user"
    else:
        uid = str(arg2 or user_id or "default_user")
        data = arg3 or {}

    client = get_supabase()
    existing = get_meal_by_id(meal_id, uid)
    if not existing:
        return None

    clean_data = {k: v for k, v in data.items() if v is not None}
    resp = client.table("meals").update(clean_data).eq("id", meal_id).eq("user_id", uid).execute()
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    return get_meal_by_id(meal_id, uid) or {**existing, **clean_data}

def delete_meal_entry(meal_id: str, user_id: str = "default_user") -> bool:
    client = get_supabase()
    existing = get_meal_by_id(meal_id, user_id)
    if not existing:
        return False
    client.table("meals").delete().eq("id", meal_id).eq("user_id", user_id).execute()
    return True

# Alias
save_meal_entry = log_meal_entry

# Recovery Operations
def get_recovery_log_by_date(date_str: str, user_id: str = "default_user") -> Optional[Dict[str, Any]]:
    client = get_supabase()
    resp = client.table("recovery_logs").select("*").eq("user_id", user_id).eq("date", date_str).execute()
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    return None

def get_recovery_log_by_id(log_id: str, user_id: str = "default_user") -> Optional[Dict[str, Any]]:
    client = get_supabase()
    try:
        resp = client.table("recovery_logs").select("*").eq("id", log_id).eq("user_id", user_id).execute()
        return resp.data[0] if resp.data and len(resp.data) > 0 else None
    except Exception as e:
        logger.warning(f"Error getting recovery log by id {log_id}: {e}")
        return None

def get_recent_recovery_logs(limit: int = 7, user_id: str = "default_user") -> List[Dict[str, Any]]:
    client = get_supabase()
    resp = client.table("recovery_logs").select("*").eq("user_id", user_id).order("date", desc=True).limit(limit).execute()
    return resp.data or []

def save_recovery_log(data: Dict[str, Any], user_id: str = "default_user") -> Dict[str, Any]:
    client = get_supabase()
    effective_user = data.get("user_id") or user_id
    payload = {**data, "user_id": effective_user}
    # upsert based on user_id and date if possible, or insert
    existing = get_recovery_log_by_date(str(payload.get("date")), effective_user)
    if existing:
        resp = client.table("recovery_logs").update(payload).eq("id", existing["id"]).eq("user_id", effective_user).execute()
    else:
        resp = client.table("recovery_logs").insert(payload).execute()
    return resp.data[0] if resp.data else {}

def update_recovery_log_by_id(log_id: str, arg2: Any = None, arg3: Any = None, data: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if data is not None:
        payload = data
        uid = user_id or "default_user"
    elif isinstance(arg2, dict):
        payload = arg2
        uid = user_id or arg3 or "default_user"
    else:
        uid = str(arg2 or user_id or "default_user")
        payload = arg3 or {}

    client = get_supabase()
    existing = get_recovery_log_by_id(log_id, uid)
    if not existing:
        return None

    clean_data = {k: v for k, v in payload.items() if v is not None}
    resp = client.table("recovery_logs").update(clean_data).eq("id", log_id).eq("user_id", uid).execute()
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    return get_recovery_log_by_id(log_id, uid) or {**existing, **clean_data}

def delete_recovery_log_by_id(log_id: str, user_id: str = "default_user") -> bool:
    client = get_supabase()
    existing = get_recovery_log_by_id(log_id, user_id)
    if not existing:
        return False
    client.table("recovery_logs").delete().eq("id", log_id).eq("user_id", user_id).execute()
    return True

# Chat History Operations
def get_chat_history(workspace: str = "home", limit: int = 30, user_id: str = "default_user") -> List[Dict[str, Any]]:
    client = get_supabase()
    resp = client.table("chat_messages").select("*").eq("workspace", workspace).eq("user_id", user_id).order("created_at", desc=False).limit(limit).execute()
    return resp.data or []

def save_chat_message(role: str, content: str, workspace: str = "home", metadata: Optional[Dict[str, Any]] = None, user_id: str = "default_user") -> Dict[str, Any]:
    client = get_supabase()
    payload = {
        "role": role,
        "content": content,
        "workspace": workspace,
        "user_id": user_id,
        "metadata": metadata or {}
    }
    resp = client.table("chat_messages").insert(payload).execute()
    return resp.data[0] if resp.data else {}
