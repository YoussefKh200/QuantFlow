"""Volatility metrics hypertable model."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class VolatilityMetric(Base):
    __tablename__ = "volatility_metrics"
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    underlying: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
    hv_5d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    hv_10d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    hv_21d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    hv_63d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    atm_iv_30d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    atm_iv_60d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    vix_term: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    iv_rank: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    iv_percentile: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    skew_25d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    skew_10d: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    ts_30_60: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    ts_slope: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    vol_regime: Mapped[Optional[str]] = mapped_column(String(20))
