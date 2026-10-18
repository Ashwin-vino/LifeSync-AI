import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth import get_authenticated_user_id
from backend.app.database.supabase_client import (
    create_workout_entry,
    get_workout_by_id,
    log_meal_entry,
    get_meal_by_id,
    update_meal_entry,
    delete_meal_entry,
    save_recovery_log,
    get_recovery_log_by_id,
    update_recovery_log_by_id,
    delete_recovery_log_by_id
)

client = TestClient(app)

USER_ALICE = "test_sec_alice"
USER_BOB = "test_sec_bob"

def test_invalid_bearer_token_rejected_with_401():
    """An invalid, forged, or expired Supabase Bearer token must be rejected with HTTP 401."""
    resp = client.get("/api/workout/list", headers={"Authorization": "Bearer invalid_or_expired_jwt_token"})
    assert resp.status_code == 401
    assert "Invalid or expired" in resp.json()["detail"] or "validation failed" in resp.json()["detail"]

def test_unauthenticated_request_defaults_safely():
    """Without an Authorization token, dev/test fallback is allowed without crashing."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data

def test_payload_size_limit_25mb_rejected():
    """Request with Content-Length exceeding 25MB must be rejected with HTTP 413."""
    too_large_bytes = 26 * 1024 * 1024 # 26MB
    headers = {"Content-Length": str(too_large_bytes), "Content-Type": "application/json"}
    resp = client.post("/api/workout/log", data=b"{}", headers=headers)
    assert resp.status_code == 413
    assert "25 MB" in resp.json()["detail"]

def test_safe_error_handling_no_secrets_leak():
    """HTTP 404/500 errors must not leak database passwords, hosts, or server tracebacks."""
    resp = client.get("/api/workout/session/non_existent_uuid_12345")
    assert resp.status_code in [404, 500]
    error_text = resp.text.lower()
    assert "password" not in error_text
    assert "traceback" not in error_text
    assert "secret" not in error_text

def test_user_ownership_isolation_workout():
    """User Bob cannot read or access User Alice's workouts."""
    w_data = {
        "title": "Alice Private Workout",
        "category": "Strength",
        "duration_minutes": 45,
        "calories_burned": 300,
        "rpe": 7,
        "status": "completed"
    }
    alice_workout = create_workout_entry(w_data, [], user_id=USER_ALICE)
    wid = str(alice_workout["id"])

    # Alice can read
    alice_fetch = get_workout_by_id(wid, user_id=USER_ALICE)
    assert alice_fetch is not None
    assert alice_fetch["title"] == "Alice Private Workout"

    # Bob CANNOT read
    bob_fetch = get_workout_by_id(wid, user_id=USER_BOB)
    assert bob_fetch is None, "Bob must not be able to retrieve Alice's workout"

def test_user_ownership_isolation_meal():
    """User Bob cannot read, edit, or delete User Alice's meal entries."""
    m_data = {
        "user_id": USER_ALICE,
        "date": "2026-10-18",
        "meal_type": "lunch",
        "name": "Alice Private Meal",
        "calories": 500,
        "protein": 40,
        "carbs": 50,
        "fat": 15,
        "fiber": 5
    }
    alice_meal = log_meal_entry(m_data, user_id=USER_ALICE)
    mid = str(alice_meal["id"])

    # Bob cannot read
    bob_read = get_meal_by_id(mid, user_id=USER_BOB)
    assert bob_read is None, "Bob must not be able to retrieve Alice's meal"

    # Bob cannot update
    bob_update = update_meal_entry(mid, {"name": "Bob Hacked Meal"}, user_id=USER_BOB)
    assert bob_update is None or bob_update.get("name") != "Bob Hacked Meal"

    # Bob cannot delete
    bob_del = delete_meal_entry(mid, user_id=USER_BOB)
    assert bob_del is False

    # Alice's meal remains untouched
    alice_check = get_meal_by_id(mid, user_id=USER_ALICE)
    assert alice_check is not None
    assert alice_check["name"] == "Alice Private Meal"

    # Cleanup
    delete_meal_entry(mid, user_id=USER_ALICE)

def test_user_ownership_isolation_recovery():
    """User Bob cannot read, edit, or delete User Alice's recovery logs."""
    r_data = {
        "user_id": USER_ALICE,
        "date": "2026-10-18",
        "recovery_score": 85,
        "sleep_hours": 8.0,
        "sleep_quality": "excellent",
        "hydration_liters": 3.0,
        "soreness_level": 2,
        "stress_level": 2,
        "fatigue_level": 2
    }
    alice_rec = save_recovery_log(r_data, user_id=USER_ALICE)
    rid = str(alice_rec["id"])

    # Bob cannot read
    bob_read = get_recovery_log_by_id(rid, user_id=USER_BOB)
    assert bob_read is None

    # Bob cannot update
    bob_update = update_recovery_log_by_id(rid, {"sleep_hours": 4.0}, user_id=USER_BOB)
    assert bob_update is None

    # Bob cannot delete
    bob_del = delete_recovery_log_by_id(rid, user_id=USER_BOB)
    assert bob_del is False

    # Alice's log remains untouched
    alice_check = get_recovery_log_by_id(rid, user_id=USER_ALICE)
    assert alice_check is not None
    assert float(alice_check["sleep_hours"]) == 8.0

    # Cleanup
    delete_recovery_log_by_id(rid, user_id=USER_ALICE)
