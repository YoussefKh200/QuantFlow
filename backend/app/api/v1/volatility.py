"""Volatility regime API endpoints."""
from fastapi import APIRouter
from app.dependencies import CurrentUser
router = APIRouter()

@router.get("/regime/{symbol}", summary="Current volatility regime")
async def get_regime(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "regime": None, "status": "stub"}

@router.get("/metrics/{symbol}", summary="HV, IV, rank, percentile")
async def get_metrics(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.get("/history/{symbol}", summary="Regime history")
async def get_history(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}
