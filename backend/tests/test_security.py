"""Security test suite."""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token
from app.services.storage_service import sanitize_filename
from tests.conftest import create_test_image


def test_sanitize_filename_prevents_path_traversal():
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("safe_image.jpg") == "safe_image.jpg"
    assert sanitize_filename("...hidden.png") == "hidden.png"
    assert sanitize_filename("test\x00exploit.png") == "test_exploit.png"


def test_cross_user_submission_access_forbidden(client, test_user, second_user):
    # User 1 submits an image
    img_bytes = create_test_image()
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("mosquito.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    sub_id = res.json()["id"]

    # User 2 attempts to get User 1's submission
    cross_res = client.get(f"/api/v1/adult/submissions/{sub_id}", headers=second_user["headers"])
    assert cross_res.status_code == 403

    # User 2 attempts to get User 1's image
    img_res = client.get(f"/api/v1/adult/submissions/{sub_id}/image", headers=second_user["headers"])
    assert img_res.status_code == 403

    # User 2 attempts to delete User 1's submission
    del_res = client.delete(f"/api/v1/submissions/{sub_id}", headers=second_user["headers"])
    assert del_res.status_code == 403


def test_invalid_jwt_rejected(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert res.status_code == 401


def test_expired_jwt_rejected(client, test_user):
    # Create an already expired token
    expired_token = create_access_token(
        {"sub": test_user["user"].id},
        expires_delta=timedelta(seconds=-60),
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401


def test_non_admin_cannot_access_admin_routes(client, test_user):
    res = client.get("/api/v1/admin/users", headers=test_user["headers"])
    assert res.status_code == 403

    res_sys = client.get("/api/v1/admin/system", headers=test_user["headers"])
    assert res_sys.status_code == 403


def test_admin_can_access_admin_routes(client, admin_user):
    res = client.get("/api/v1/admin/users", headers=admin_user["headers"])
    assert res.status_code == 200
    assert "items" in res.json()

    res_sys = client.get("/api/v1/admin/system", headers=admin_user["headers"])
    assert res_sys.status_code == 200
    assert res_sys.json()["database_connected"] is True
    assert res_sys.json()["status"] == "healthy"


def test_sql_injection_payload_handled_safely(client, test_user):
    """SQL injection payloads in queries must be safely parameterized without syntax errors."""
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE submissions; --",
        "1' UNION SELECT null, null, null --",
    ]
    for payload in sql_payloads:
        res = client.get(f"/api/v1/submissions?search={payload}", headers=test_user["headers"])
        assert res.status_code == 200
        assert isinstance(res.json()["items"], list)


def test_xss_payload_in_filename_sanitized(client, test_user):
    """XSS payloads in uploaded filenames must be sanitized to safe characters."""
    img_bytes = create_test_image()
    xss_filename = "<script>alert('XSS')</script>.jpg"
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": (xss_filename, io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert res.status_code == 201
    sub_id = res.json()["id"]

    detail_res = client.get(f"/api/v1/submissions/{sub_id}", headers=test_user["headers"])
    assert detail_res.status_code == 200
    media = detail_res.json()["media"][0]
    assert "<script>" not in media["filename"]
    assert sanitize_filename(xss_filename) == "script_.jpg"


def test_csrf_protection_requires_bearer_token(client):
    """Mutating state without Bearer authorization header must be rejected."""
    res = client.post("/api/v1/adult/submit")
    assert res.status_code == 401

    res_larvae = client.post("/api/v1/larvae/submit")
    assert res_larvae.status_code == 401
