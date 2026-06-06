"""Earnings and PEAD models."""
from __future__ import annotations
import uuid
from datetime import date
from typing import Optional
from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Earnings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "earnings"
    symbol_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("symbols.id"))
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fiscal_period: Mapped[Optional[str]] = mapped_column(String(10))
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    report_time: Mapped[Optional[str]] = mapped_column(String(5))
    eps_actual: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    eps_estimate: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    eps_surprise: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    eps_surprise_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    revenue_actual: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    revenue_estimate: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    revenue_surprise: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    guidance_raised: Mapped[Optional[bool]] = mapped_column(Boolean)

class EarningsPEAD(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "earnings_pead"
    earnings_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("earnings.id"))
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    sue_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), index=True)
    price_at_close: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    price_day_before: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    drift_1d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    drift_5d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    drift_10d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    drift_20d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    drift_60d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    iv_pre: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    iv_post_1d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    iv_crush_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    signal_direction: Mapped[Optional[str]] = mapped_column(String(1))
    signal_confidence: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
