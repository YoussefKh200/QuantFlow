"""
Redis-backed sliding window rate limiter.
Per-user, per-endpoint with configurable limits.
"""
from __future__ import annotations

import time

from fastapi import HTTPException, Request, status

from app.core.cache import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

# (requests, window_seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth":               (10, 60),     # strict — brute force protection
    "/api/v1/options":            (100, 60),
    "/api/v1/dealer":             (200, 60),
    "/api/v1/flow":               (300, 60),
    "/api/v1/research/backtest":  (10, 3600),   # expensive — 10/hr
    "/api/v1/research":           (50, 60),
    "default":                    (300, 60),
}


def _get_limit(path: str) -> tuple[int, int]:
    # Match on the first 4 path segments
    prefix = "/" + "/".join(path.strip("/").split("/")[:4])
    return RATE_LIMITS.get(prefix, RATE_LIMITS["default"])


class SlidingWindowRateLimiter:
    """
    Sliding window implemented with Redis sorted sets.
    Key: rl:{user_id}:{path_prefix}
    Score: timestamp in milliseconds
    """

    async def check(self, request: Request, user_id: str) -> None:
        redis = get_redis()
        limit, window = _get_limit(request.url.path)
        key = f"rl:{user_id}:{request.url.path[:50]}"
        now_ms = int(time.time() * 1000)
        window_ms = window * 1000

        async with redis.pipeline(transaction=True) as pipe:
            # Remove entries outside the window
            pipe.zremrangebyscore(key, 0, now_ms - window_ms)
            # Count current entries
            pipe.zcard(key)
            # Add this request
            pipe.zadd(key, {str(now_ms): now_ms})
            # Reset expiry
            pipe.expire(key, window)
            results = await pipe.execute()

        count = results[1]

        if count >= limit:
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                path=request.url.path,
                count=count,
                limit=limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "limit": limit,
                    "window_seconds": window,
                    "retry_after": window,
                },
                headers={"Retry-After": str(window)},
            )


rate_limiter = SlidingWindowRateLimiter()
