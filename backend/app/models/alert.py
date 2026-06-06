"""Alert model."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Alert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "alerts"
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    underlying: Mapped[Optional[str]] = mapped_column(String(20))
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(10), default="info")
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
