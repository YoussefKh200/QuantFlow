"""
Async SQLAlchemy database engine, session factory, and dependency.
Uses asyncpg driver for full async performance.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings


def _make_engine(testing: bool = False) -> AsyncEngine:
    kwargs: dict[str, Any] = {
        "echo": settings.DB_ECHO,
        "echo_pool": False,
        "future": True,
    }
    if testing:
        # NullPool for test isolation — no connection reuse between tests
        kwargs["poolclass"] = NullPool
    else:
        kwargs.update(
            {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "pool_pre_ping": True,          # detects stale connections
                "pool_recycle": 3600,           # recycle connections hourly
                "connect_args": {
                    "server_settings": {
                        "application_name": "quantflow-backend",
                        "jit": "off",           # disable JIT for OLTP workload
                    },
                    "command_timeout": 60,
                },
            }
        )

    return create_async_engine(settings.DATABASE_URL, **kwargs)


engine: AsyncEngine = _make_engine()

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def create_db_pool() -> AsyncEngine:
    """Called at application startup to validate connectivity."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an async session per request.
    Commits on success, rolls back on exception.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session_no_commit() -> AsyncGenerator[AsyncSession, None]:
    """Read-only sessions — no commit, ideal for GET endpoints."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()
