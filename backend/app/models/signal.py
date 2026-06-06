"""Trading signal model."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Signal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "signals"
    underlying: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    direction: Mapped[Optional[str]] = mapped_column(String(1))
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    expected_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    expected_vol: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    sharpe_estimate: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    entry_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    target_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    stop_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    horizon_days: Mapped[Optional[int]] = mapped_column(SmallInteger)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actual_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
