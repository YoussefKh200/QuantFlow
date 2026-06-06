"""Options flow scanner API endpoints."""
from fastapi import APIRouter
from app.dependencies import CurrentUser
router = APIRouter()

@router.get("/scanner", summary="Live flow feed")
async def get_scanner(user: CurrentUser):
    return {"flows": [], "status": "stub"}

@router.get("/unusual", summary="Unusual activity")
async def get_unusual(user: CurrentUser):
    return {"flows": [], "status": "stub"}

@router.get("/sentiment/{symbol}", summary="Bull/bear flow score")
async def get_sentiment(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "sentiment": None, "status": "stub"}
