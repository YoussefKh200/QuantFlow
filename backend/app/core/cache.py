"""
Redis cache layer.
Provides typed get/set/delete helpers with automatic JSON serialization.
"""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings


_redis_client: Redis | None = None


async def init_redis() -> Redis:
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    # Validate connection
    await _redis_client.ping()
    return _redis_client


def get_redis() -> Redis:
    if _redis_client is None:
        raise RuntimeError("Redis not initialized — call init_redis() first")
    return _redis_client


# --------------------------------------------------------------------------
# Cache TTL constants (seconds)
# --------------------------------------------------------------------------
class CacheTTL:
    OPTION_CHAIN = 10
    GREEKS = 10
    GEX_SUMMARY = 30
    VOL_SURFACE = 60
    IV_RANK = 300
    EARNINGS_CALENDAR = 3_600
    PEAD_SIGNALS = 300
    REGIME = 60
    FLOW_SCANNER = 5
    USER_SESSION = 900          # 15 min
    RATE_LIMIT_WINDOW = 60


# --------------------------------------------------------------------------
# Cache key builder
# --------------------------------------------------------------------------
class CacheKey:
    _VERSION = "v1"

    @classmethod
    def build(cls, *parts: str) -> str:
        return f"qf:{cls._VERSION}:{':'.join(parts)}"

    @classmethod
    def option_chain(cls, symbol: str) -> str:
        return cls.build("chain", symbol)

    @classmethod
    def greeks(cls, symbol: str) -> str:
        return cls.build("greeks", symbol)

    @classmethod
    def gex(cls, symbol: str) -> str:
        return cls.build("gex", symbol)

    @classmethod
    def vol_surface(cls, symbol: str) -> str:
        return cls.build("surface", symbol)

    @classmethod
    def iv_rank(cls, symbol: str) -> str:
        return cls.build("ivrank", symbol)

    @classmethod
    def regime(cls, symbol: str) -> str:
        return cls.build("regime", symbol)

    @classmethod
    def flow_scanner(cls) -> str:
        return cls.build("flow", "scanner")

    @classmethod
    def blacklisted_token(cls, jti: str) -> str:
        return cls.build("blacklist", jti)


# --------------------------------------------------------------------------
# Typed cache helpers
# --------------------------------------------------------------------------
class Cache:
    def __init__(self, redis: Redis):
        self._r = redis

    async def get(self, key: str) -> Any | None:
        raw = await self._r.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int) -> None:
        await self._r.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._r.exists(key))

    async def incr(self, key: str) -> int:
        return int(await self._r.incr(key))

    async def expire(self, key: str, ttl: int) -> None:
        await self._r.expire(key, ttl)

    async def zadd(self, key: str, mapping: dict[str, float]) -> None:
        await self._r.zadd(key, mapping)

    async def zremrangebyscore(self, key: str, min_: float, max_: float) -> None:
        await self._r.zremrangebyscore(key, min_, max_)

    async def zcard(self, key: str) -> int:
        return int(await self._r.zcard(key))
