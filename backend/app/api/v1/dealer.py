"""Dealer positioning API endpoints."""
from fastapi import APIRouter
from app.dependencies import CurrentUser
router = APIRouter()

@router.get("/gex/{symbol}", summary="GEX per strike")
async def get_gex(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.get("/summary/{symbol}", summary="Aggregate dealer positioning")
async def get_summary(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.get("/levels/{symbol}", summary="Call wall, put wall, gamma flip")
async def get_levels(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "gamma_flip": None, "call_wall": None, "put_wall": None, "status": "stub"}

@router.get("/heatmap/{symbol}", summary="GEX heatmap data")
async def get_heatmap(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.get("/history/{symbol}", summary="Historical GEX time series")
async def get_history(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}
