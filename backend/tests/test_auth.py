"""Authentication test suite."""
from __future__ import annotations

import pytest
from app.core.security import hash_token
from app.db.models import RefreshToken


def test_register_success(client):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "username": "newuser", "password": "SecurePassword123!"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "id" in data


def test_register_duplicate_email(client, test_user):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "user1@example.com", "username": "different", "password": "SecurePassword123!"},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "EMAIL_TAKEN"


def test_register_duplicate_username(client, test_user):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "different@example.com", "username": "user1", "password": "SecurePassword123!"},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "USERNAME_TAKEN"


def test_login_success(client, test_user):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "user1@example.com", "password": "Password123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in res.cookies


def test_login_invalid_password(client, test_user):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "user1@example.com", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
    assert res.json()["error_code"] == "INVALID_CREDENTIALS"


def test_login_nonexistent_user(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "Password123!"},
    )
    assert res.status_code == 401
    assert res.json()["error_code"] == "INVALID_CREDENTIALS"


def test_profile_me_authenticated(client, test_user):
    res = client.get("/api/v1/auth/me", headers=test_user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "user1@example.com"
    assert data["username"] == "user1"
    assert "hashed_password" not in data


def test_profile_me_unauthorized(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_refresh_token_rotation(client, test_user):
    # Login to get refresh cookie
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "user1@example.com", "password": "Password123!"},
    )
    old_refresh = login_res.cookies.get("refresh_token")
    assert old_refresh is not None

    # Call refresh
    refresh_res = client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert refresh_res.status_code == 200
    new_access = refresh_res.json().get("access_token")
    new_refresh = refresh_res.cookies.get("refresh_token")

    assert new_access is not None
    assert new_refresh is not None
    assert new_refresh != old_refresh

    # Using old refresh token again must fail (token reuse detection)
    reuse_res = client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert reuse_res.status_code == 401
    assert reuse_res.json()["error_code"] == "TOKEN_REUSE"


def test_logout(client, test_user):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "user1@example.com", "password": "Password123!"},
    )
    refresh_cookie = login_res.cookies.get("refresh_token")

    res = client.post("/api/v1/auth/logout", cookies={"refresh_token": refresh_cookie})
    assert res.status_code == 200

    # Refresh after logout should fail
    refresh_res = client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert refresh_res.status_code == 401
