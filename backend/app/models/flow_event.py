"""Flow events hypertable model."""
from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class FlowEvent(Base):
    __tablename__ = "flow_events"
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("option_contracts.id"), primary_key=True)
    underlying: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    strike: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    expiration: Mapped[Optional[date]] = mapped_column(Date)
    option_type: Mapped[Optional[str]] = mapped_column(String(1))
    trade_size: Mapped[Optional[int]] = mapped_column(Integer, primary_key=True)
    trade_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), primary_key=True)
    trade_side: Mapped[Optional[str]] = mapped_column(String(5))
    aggressor: Mapped[Optional[str]] = mapped_column(String(10))
    trade_type: Mapped[Optional[str]] = mapped_column(String(10))
    premium_total: Mapped[Optional[float]] = mapped_column(Numeric(16, 2))
    sentiment: Mapped[Optional[str]] = mapped_column(String(10))
    is_unusual: Mapped[bool] = mapped_column(Boolean, default=False)
    is_institutional: Mapped[bool] = mapped_column(Boolean, default=False)
    flow_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    exchange: Mapped[Optional[str]] = mapped_column(String(10))
