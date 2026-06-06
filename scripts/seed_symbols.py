#!/usr/bin/env python3
"""
Seed script — populates the database with:
  - Core equity/ETF/index symbols
  - A default admin user
  - Sample option contracts (for dev/testing)

Usage: python scripts/seed_symbols.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings  # noqa: E402 — must import after sys.path


SYMBOLS = [
    # Indices
    {"ticker": "SPX",  "name": "S&P 500 Index",        "asset_class": "index",  "has_options": True},
    {"ticker": "NDX",  "name": "Nasdaq 100 Index",      "asset_class": "index",  "has_options": True},
    {"ticker": "RUT",  "name": "Russell 2000 Index",    "asset_class": "index",  "has_options": True},
    {"ticker": "VIX",  "name": "CBOE Volatility Index", "asset_class": "index",  "has_options": True},
    # ETFs
    {"ticker": "SPY",  "name": "SPDR S&P 500 ETF",      "asset_class": "etf",    "has_options": True},
    {"ticker": "QQQ",  "name": "Invesco QQQ Trust",      "asset_class": "etf",    "has_options": True},
    {"ticker": "IWM",  "name": "iShares Russell 2000",   "asset_class": "etf",    "has_options": True},
    {"ticker": "GLD",  "name": "SPDR Gold Shares",       "asset_class": "etf",    "has_options": True},
    {"ticker": "TLT",  "name": "iShares 20+ Year Tsy",   "asset_class": "etf",    "has_options": True},
    # Equities
    {"ticker": "AAPL", "name": "Apple Inc.",             "asset_class": "equity", "has_options": True},
    {"ticker": "MSFT", "name": "Microsoft Corp.",        "asset_class": "equity", "has_options": True},
    {"ticker": "NVDA", "name": "NVIDIA Corp.",           "asset_class": "equity", "has_options": True},
    {"ticker": "META", "name": "Meta Platforms Inc.",    "asset_class": "equity", "has_options": True},
    {"ticker": "TSLA", "name": "Tesla Inc.",             "asset_class": "equity", "has_options": True},
    {"ticker": "AMZN", "name": "Amazon.com Inc.",        "asset_class": "equity", "has_options": True},
    {"ticker": "GOOGL","name": "Alphabet Inc. Class A",  "asset_class": "equity", "has_options": True},
    {"ticker": "GOOG", "name": "Alphabet Inc. Class C",  "asset_class": "equity", "has_options": True},
    {"ticker": "NFLX", "name": "Netflix Inc.",           "asset_class": "equity", "has_options": True},
    {"ticker": "AMD",  "name": "Advanced Micro Devices", "asset_class": "equity", "has_options": True},
    {"ticker": "INTC", "name": "Intel Corp.",            "asset_class": "equity", "has_options": True},
    # Futures (underlying)
    {"ticker": "ES",   "name": "E-mini S&P 500 Futures", "asset_class": "future", "multiplier": 50},
    {"ticker": "NQ",   "name": "E-mini Nasdaq Futures",  "asset_class": "future", "multiplier": 20},
    {"ticker": "GC",   "name": "Gold Futures",            "asset_class": "commodity"},
    {"ticker": "SI",   "name": "Silver Futures",          "asset_class": "commodity"},
    # Forex
    {"ticker": "EURUSD", "name": "EUR/USD",              "asset_class": "forex"},
    {"ticker": "GBPUSD", "name": "GBP/USD",              "asset_class": "forex"},
]

DEFAULT_ADMIN = {
    "email": "admin@quantflow.io",
    "password": "ChangeMe123!",  # CHANGE IN PRODUCTION
    "full_name": "QuantFlow Admin",
    "role": "admin",
}


async def seed():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select
    from app.models.base import Base
    from app.models.symbol import Symbol
    from app.models.user import User
    from app.core.security import hash_password

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionFactory() as session:
        # --- Seed symbols ---
        existing_tickers = set(
            row[0] for row in (await session.execute(select(Symbol.ticker))).all()
        )
        new_symbols = []
        for sym in SYMBOLS:
            if sym["ticker"] not in existing_tickers:
                new_symbols.append(Symbol(
                    ticker=sym["ticker"],
                    name=sym.get("name"),
                    asset_class=sym["asset_class"],
                    has_options=sym.get("has_options", False),
                    multiplier=sym.get("multiplier", 1.0),
                    is_active=True,
                ))

        if new_symbols:
            session.add_all(new_symbols)
            print(f"  Added {len(new_symbols)} symbols")
        else:
            print("  Symbols already seeded — skipping")

        # --- Seed admin user ---
        existing_user = (
            await session.execute(select(User).where(User.email == DEFAULT_ADMIN["email"]))
        ).scalar_one_or_none()

        if not existing_user:
            admin = User(
                email=DEFAULT_ADMIN["email"],
                hashed_password=hash_password(DEFAULT_ADMIN["password"]),
                full_name=DEFAULT_ADMIN["full_name"],
                role=DEFAULT_ADMIN["role"],
                is_active=True,
            )
            session.add(admin)
            print(f"  Created admin user: {DEFAULT_ADMIN['email']}")
            print(f"  ⚠️  Default password: {DEFAULT_ADMIN['password']} — CHANGE IMMEDIATELY")
        else:
            print("  Admin user already exists — skipping")

        await session.commit()

    await engine.dispose()
    print("\n✅ Seed complete")


if __name__ == "__main__":
    print("🌱 Seeding QuantFlow database...\n")
    asyncio.run(seed())
