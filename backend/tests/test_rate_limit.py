"""Tests for Redis-backed rate limiter, concurrency, expiry, and resilience."""
from __future__ import annotations

import concurrent.futures
import time
from unittest.mock import patch

import pytest
import redis
from fastapi.testclient import TestClient

from app.config import settings
from app.core.exceptions import RateLimitException
from app.core.rate_limit import RateLimiter, rate_limiter, check_login_rate_limit


def test_rate_limiter_allows_under_limit():
    """Verify requests under the configured threshold succeed."""
    limiter = RateLimiter()
    limiter.clear("test_action", "ip_allow_test")

    for _ in range(3):
        is_limited, retry_after = limiter.is_rate_limited(
            action="test_action",
            identifier="ip_allow_test",
            limit=5,
            window=60,
        )
        assert not is_limited
        assert retry_after == 0


def test_rate_limiter_blocks_over_limit():
    """Verify exceeding the threshold triggers rate limit and returns retry-after."""
    limiter = RateLimiter()
    limiter.clear("test_action", "ip_block_test")

    # Consume all 5 attempts
    for _ in range(5):
        is_limited, _ = limiter.is_rate_limited(
            action="test_action",
            identifier="ip_block_test",
            limit=5,
            window=60,
        )
        assert not is_limited

    # 6th attempt must be blocked
    is_limited, retry_after = limiter.is_rate_limited(
        action="test_action",
        identifier="ip_block_test",
        limit=5,
        window=60,
    )
    assert is_limited
    assert retry_after > 0


def test_rate_limiter_concurrent_requests():
    """
    Verify atomic sliding window handles concurrent threads correctly.
    Exactly `limit` requests must succeed, and remainder must be blocked.
    """
    limiter = RateLimiter()
    limiter.clear("concurrent_test", "shared_ip")
    limit = 8
    total_workers = 20

    results = []

    def make_attempt(worker_id: int):
        limited, _ = limiter.is_rate_limited(
            action="concurrent_test",
            identifier="shared_ip",
            limit=limit,
            window=30,
        )
        return limited

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_attempt, i) for i in range(total_workers)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    allowed_count = results.count(False)
    blocked_count = results.count(True)

    assert allowed_count == limit, f"Expected {limit} allowed, got {allowed_count}"
    assert blocked_count == total_workers - limit


def test_rate_limiter_expiry():
    """Verify that rate limit records expire after the time window passes."""
    limiter = RateLimiter()
    limiter.clear("expiry_test", "expiring_ip")

    # Window of 1 second with limit 2
    for _ in range(2):
        is_limited, _ = limiter.is_rate_limited(
            action="expiry_test",
            identifier="expiring_ip",
            limit=2,
            window=1,
        )
        assert not is_limited

    # Immediate 3rd attempt is blocked
    is_limited, retry_after = limiter.is_rate_limited(
        action="expiry_test",
        identifier="expiring_ip",
        limit=2,
        window=1,
    )
    assert is_limited
    assert retry_after >= 1

    # Sleep 1.2 seconds for window to slide past
    time.sleep(1.2)

    # Now request should be allowed again
    is_limited, _ = limiter.is_rate_limited(
        action="expiry_test",
        identifier="expiring_ip",
        limit=2,
        window=1,
    )
    assert not is_limited


def test_redis_connection_failure_safe_fallback():
    """
    Verify that when Redis is unreachable or fails, the rate limiter
    gracefully falls back to the in-memory store without crashing.
    """
    # Create limiter with an invalid Redis URL to simulate network outage
    faulty_limiter = RateLimiter(redis_url="redis://127.0.0.1:59999/0")
    faulty_limiter.clear("fallback_test", "fallback_ip")

    # Must not raise connection error; falls back to in-memory store
    for _ in range(3):
        is_limited, _ = faulty_limiter.is_rate_limited(
            action="fallback_test",
            identifier="fallback_ip",
            limit=3,
            window=10,
        )
        assert not is_limited

    # 4th request must be limited by in-memory fallback
    is_limited, retry_after = faulty_limiter.is_rate_limited(
        action="fallback_test",
        identifier="fallback_ip",
        limit=3,
        window=10,
    )
    assert is_limited
    assert retry_after > 0


def test_api_login_rate_limiting_enforced(client: TestClient, test_user):
    """Verify FastAPI /auth/login route returns HTTP 429 when rate limit is exceeded."""
    client_ip = "192.168.1.100"
    rate_limiter.clear("login", client_ip)

    headers = {"X-Forwarded-For": client_ip}

    # Attempt invalid logins up to limit
    for _ in range(settings.LOGIN_RATE_LIMIT_ATTEMPTS):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": test_user["user"].email, "password": "WrongPassword!"},
            headers=headers,
        )
        assert res.status_code == 401

    # Next attempt must trigger HTTP 429 RATE_LIMITED
    res = client.post(
        "/api/v1/auth/login",
        json={"email": test_user["user"].email, "password": "WrongPassword!"},
        headers=headers,
    )
    assert res.status_code == 429
    assert res.json()["error_code"] == "RATE_LIMITED"
    assert "Too many login attempts" in res.json()["message"]

    # Clear rate limit and verify access is restored
    rate_limiter.clear("login", client_ip)
    res = client.post(
        "/api/v1/auth/login",
        json={"email": test_user["user"].email, "password": "Password123!"},
        headers=headers,
    )
    assert res.status_code == 200
