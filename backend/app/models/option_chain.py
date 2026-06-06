"""Option chain hypertable model (snapshot per timestamp)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class OptionChain(Base):
    __tablename__ = "option_chains"
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("option_contracts.id"), primary_key=True)
    underlying: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    spot_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    bid: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    ask: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    mid: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    last: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    volume: Mapped[int] = mapped_column(BigInteger, default=0)
    open_interest: Mapped[int] = mapped_column(BigInteger, default=0)
    iv: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    intrinsic: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    extrinsic: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))
    dte: Mapped[Optional[int]] = mapped_column(SmallInteger)
