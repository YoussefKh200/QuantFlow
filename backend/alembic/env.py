"""
Alembic migration environment.
Supports async SQLAlchemy (asyncpg) driver with synchronous fallback for Alembic.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.models.base import Base

# --- Load all models so Alembic autogenerates correctly ---
from app.models import (  # noqa: F401
    alert,
    backtest,
    dealer_positioning,
    earnings,
    flow_event,
    greeks,
    market_regime,
    option_chain,
    option_contract,
    research_result,
    signal,
    symbol,
    user,
    volatility_metric,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    # Use sync psycopg2 URL for Alembic (it doesn't support asyncpg natively)
    return settings.DATABASE_URL_SYNC


def include_object(object: Any, name: str, type_: str, reflected: bool, compare_to: Any) -> bool:
    """Exclude TimescaleDB internal tables from autogenerate."""
    if type_ == "table" and name.startswith("_timescaledb"):
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — no DB connection needed."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Any) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Enable TimescaleDB extension before migrations
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
        await connection.commit()

        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
