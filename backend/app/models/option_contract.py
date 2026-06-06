"""Option contract model — one row per listed contract."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OptionContract(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "option_contracts"

    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False
    )
    osi_symbol: Mapped[str] = mapped_column(String(25), unique=True, nullable=False, index=True)
    underlying: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    expiration: Mapped[date] = mapped_column(Date, nullable=False)
    strike: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    option_type: Mapped[str] = mapped_column(String(1), nullable=False)  # C or P
    multiplier: Mapped[float] = mapped_column(Numeric(8, 2), default=100.0)
    style: Mapped[str] = mapped_column(String(10), default="american")

    symbol = relationship("Symbol", lazy="select")

    def __repr__(self) -> str:
        return f"<Option {self.osi_symbol}>"
