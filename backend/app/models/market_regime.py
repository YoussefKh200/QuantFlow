"""Market regime hypertable model."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class MarketRegime(Base):
    __tablename__ = "market_regimes"
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    underlying: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
    vol_regime: Mapped[str] = mapped_column(String(20), nullable=False)
    vol_state: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    gamma_regime: Mapped[str] = mapped_column(String(20), nullable=False)
    gex_level: Mapped[Optional[float]] = mapped_column(Numeric(22, 2))
    trend_regime: Mapped[Optional[str]] = mapped_column(String(20))
    trend_probability: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    composite_regime: Mapped[Optional[str]] = mapped_column(String(30))
    regime_confidence: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
