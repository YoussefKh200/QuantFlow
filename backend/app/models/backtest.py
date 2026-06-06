"""Backtest model."""
from __future__ import annotations
import uuid
from datetime import date
from typing import Optional
from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Backtest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "backtests"
    name: Mapped[Optional[str]] = mapped_column(String(100))
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    universe: Mapped[Optional[list]] = mapped_column(ARRAY(Text))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    annualized_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    annualized_vol: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    win_rate: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    profit_factor: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    num_trades: Mapped[Optional[int]] = mapped_column(Integer)
    avg_trade_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    equity_curve: Mapped[Optional[dict]] = mapped_column(JSONB)
    trade_log: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
