"""Greeks hypertable model — TimescaleDB managed."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class Greeks(Base):
    __tablename__ = "greeks"
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("option_contracts.id"), primary_key=True)
    underlying: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    spot_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    delta: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    gamma: Mapped[Optional[float]] = mapped_column(Numeric(14, 10))
    vega: Mapped[Optional[float]] = mapped_column(Numeric(12, 8))
    theta: Mapped[Optional[float]] = mapped_column(Numeric(12, 8))
    rho: Mapped[Optional[float]] = mapped_column(Numeric(12, 8))
    vanna: Mapped[Optional[float]] = mapped_column(Numeric(14, 10))
    charm: Mapped[Optional[float]] = mapped_column(Numeric(14, 10))
    vomma: Mapped[Optional[float]] = mapped_column(Numeric(14, 10))
    speed: Mapped[Optional[float]] = mapped_column(Numeric(16, 12))
    iv: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    iv_bid: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    iv_ask: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
