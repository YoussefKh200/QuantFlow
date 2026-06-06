"""Dealer positioning hypertable model."""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, BigInteger, Date, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class DealerPositioning(Base):
    __tablename__ = "dealer_positioning"
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    underlying: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
    strike: Mapped[float] = mapped_column(Numeric(12, 2), primary_key=True)
    expiration: Mapped[Optional[date]] = mapped_column(Date)
    gex_calls: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    gex_puts: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    gex_net: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    dex_calls: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    dex_puts: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    dex_net: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    vex_net: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    cex_net: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    oi_calls: Mapped[Optional[int]] = mapped_column(BigInteger)
    oi_puts: Mapped[Optional[int]] = mapped_column(BigInteger)
    is_call_wall: Mapped[bool] = mapped_column(Boolean, default=False)
    is_put_wall: Mapped[bool] = mapped_column(Boolean, default=False)
    is_gamma_flip: Mapped[bool] = mapped_column(Boolean, default=False)
    is_vol_trigger: Mapped[bool] = mapped_column(Boolean, default=False)
