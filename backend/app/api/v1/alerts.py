"""Alert management endpoints."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel
from app.dependencies import CurrentUser, SessionDep
from app.models.alert import Alert
from sqlalchemy import select
router = APIRouter()

class AlertCreate(BaseModel):
    alert_type: str
    underlying: str | None = None
    condition: dict
    message: str | None = None
    severity: str = "info"

@router.post("", status_code=status.HTTP_201_CREATED, summary="Create alert")
async def create_alert(body: AlertCreate, user: CurrentUser, session: SessionDep):
    alert = Alert(user_id=user.id, **body.model_dump())
    session.add(alert)
    await session.flush()
    return {"id": str(alert.id), "status": "created"}

@router.get("", summary="List my alerts")
async def list_alerts(user: CurrentUser, session: SessionDep):
    result = await session.execute(select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc()).limit(100))
    return {"alerts": [{"id": str(a.id), "alert_type": a.alert_type, "severity": a.severity} for a in result.scalars()]}

@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete alert")
async def delete_alert(alert_id: uuid.UUID, user: CurrentUser, session: SessionDep):
    result = await session.execute(select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id))
    alert = result.scalar_one_or_none()
    if alert:
        await session.delete(alert)
