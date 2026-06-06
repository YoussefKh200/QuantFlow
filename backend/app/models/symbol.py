"""Symbol model — the root entity for all market data."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Symbol(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "symbols"

    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    multiplier: Mapped[float] = mapped_column(Numeric(12, 4), default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    has_options: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<Symbol {self.ticker} [{self.asset_class}]>"
