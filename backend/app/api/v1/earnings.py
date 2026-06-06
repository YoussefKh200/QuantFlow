"""Earnings and PEAD API endpoints."""
from fastapi import APIRouter
from app.dependencies import CurrentUser
router = APIRouter()

@router.get("/calendar", summary="Upcoming earnings")
async def get_calendar(user: CurrentUser):
    return {"earnings": [], "status": "stub"}

@router.get("/history/{symbol}", summary="Historical earnings")
async def get_history(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "earnings": [], "status": "stub"}

@router.get("/pead/{symbol}", summary="PEAD drift statistics")
async def get_pead(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.get("/signals", summary="Active PEAD signals")
async def get_signals(user: CurrentUser):
    return {"signals": [], "status": "stub"}
