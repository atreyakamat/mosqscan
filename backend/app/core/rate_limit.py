"""Rate limiting module using Redis with atomic sliding window and safe in-memory fallback."""
from __future__ import annotations

import logging
import secrets
import threading
import time
from typing import Any, Tuple

import redis

from app.config import settings
from app.core.exceptions import RateLimitException

logger = logging.getLogger(__name__)

# Atomic sliding window Lua script
# Evaluates attempts in a sliding time window [now - window, now]
# KEYS[1]: Redis key for rate limiter
# ARGV[1]: current timestamp in seconds
# ARGV[2]: window duration in seconds
# ARGV[3]: max allowed requests in the window
# ARGV[4]: unique event identifier (member)
# Returns: {allowed (1 or 0), remaining attempts, retry_after seconds}
SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

local clear_before = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', clear_before)
local current_count = redis.call('ZCARD', key)

if current_count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, math.ceil(window) + 1)
    return {1, limit - current_count - 1, 0}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = math.ceil(window)
    if oldest and #oldest >= 2 then
        local oldest_time = tonumber(oldest[2])
        retry_after = math.max(1, math.ceil(oldest_time + window - now))
    end
    return {0, 0, retry_after}
end
"""

_mem_lock = threading.Lock()
_in_memory_store: dict[str, list[float]] = {}


def _check_in_memory(key: str, limit: int, window: int) -> Tuple[bool, int]:
    """Fallback sliding window rate limiter in memory."""
    now = time.time()
    with _mem_lock:
        timestamps = _in_memory_store.get(key, [])
        timestamps = [t for t in timestamps if now - t < window]
        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(oldest + window - now))
            _in_memory_store[key] = timestamps
            return False, retry_after
        timestamps.append(now)
        _in_memory_store[key] = timestamps
        return True, 0


def _clear_in_memory(key: str) -> None:
    with _mem_lock:
        _in_memory_store.pop(key, None)


class RateLimiter:
    """Redis-backed rate limiter with atomic sliding window and in-memory fallback."""

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: redis.Redis | None = None
        self._script: Any = None
        self._client_lock = threading.Lock()

    def get_client(self) -> redis.Redis | None:
        """Get or initialize Redis client with fast timeout to avoid blocking."""
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    try:
                        client = redis.from_url(
                            self.redis_url,
                            decode_responses=True,
                            socket_timeout=1.0,
                            socket_connect_timeout=1.0,
                        )
                        client.ping()
                        self._client = client
                        self._script = client.register_script(SLIDING_WINDOW_LUA)
                    except Exception as exc:
                        logger.warning(
                            "Redis connection failed (%s); using in-memory rate limiter fallback.",
                            exc,
                        )
                        self._client = None
                        self._script = None
        return self._client

    def is_rate_limited(
        self, action: str, identifier: str, limit: int, window: int
    ) -> Tuple[bool, int]:
        """
        Check whether an action is rate limited for the given identifier.

        Returns:
            (is_limited: bool, retry_after_seconds: int)
        """
        key = f"rl:{action}:{identifier}"
        client = self.get_client()

        if client is not None:
            try:
                now = time.time()
                member = f"{now}:{secrets.token_hex(4)}"
                if self._script is None:
                    self._script = client.register_script(SLIDING_WINDOW_LUA)
                res = self._script(keys=[key], args=[now, window, limit, member])
                allowed = bool(res[0])
                retry_after = int(res[2])
                return not allowed, retry_after
            except (redis.RedisError, OSError) as exc:
                logger.warning(
                    "Redis rate limit check failed (%s); falling back to in-memory store.",
                    exc,
                )
                self._client = None
                self._script = None

        # Fallback to in-memory store
        allowed, retry_after = _check_in_memory(key, limit, window)
        return not allowed, retry_after

    def clear(self, action: str, identifier: str) -> None:
        """Clear recorded attempts for an action and identifier."""
        key = f"rl:{action}:{identifier}"
        client = self.get_client()
        if client is not None:
            try:
                client.delete(key)
            except Exception as exc:
                logger.warning("Failed to clear Redis key %s: %s", key, exc)
                self._client = None
        _clear_in_memory(key)


# Global singleton instance
rate_limiter = RateLimiter()


def check_login_rate_limit(ip: str) -> None:
    """Check login rate limit for the client IP."""
    limited, retry_after = rate_limiter.is_rate_limited(
        action="login",
        identifier=ip,
        limit=settings.LOGIN_RATE_LIMIT_ATTEMPTS,
        window=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    if limited:
        minutes = max(1, (retry_after + 59) // 60)
        raise RateLimitException(
            f"Too many login attempts. Try again after {minutes} minutes."
        )


def clear_login_rate_limit(ip: str) -> None:
    """Clear login rate limit for the client IP (on successful login)."""
    rate_limiter.clear(action="login", identifier=ip)


def check_password_reset_rate_limit(ip: str) -> None:
    """Check password reset request rate limit for the client IP."""
    limited, retry_after = rate_limiter.is_rate_limited(
        action="password_reset",
        identifier=ip,
        limit=settings.PASSWORD_RESET_RATE_LIMIT_ATTEMPTS,
        window=settings.PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS,
    )
    if limited:
        minutes = max(1, (retry_after + 59) // 60)
        raise RateLimitException(
            f"Too many password reset requests. Try again after {minutes} minutes."
        )


def check_password_reset_confirm_rate_limit(ip: str) -> None:
    """Check password reset confirmation rate limit for the client IP."""
    limited, retry_after = rate_limiter.is_rate_limited(
        action="password_reset_confirm",
        identifier=ip,
        limit=settings.PASSWORD_RESET_RATE_LIMIT_ATTEMPTS,
        window=settings.PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS,
    )
    if limited:
        minutes = max(1, (retry_after + 59) // 60)
        raise RateLimitException(
            f"Too many password reset confirmation attempts. Try again after {minutes} minutes."
        )
