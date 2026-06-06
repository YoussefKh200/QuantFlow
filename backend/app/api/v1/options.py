"""Options analytics API endpoints."""
from fastapi import APIRouter, Query
from app.dependencies import CurrentUser, SessionDep, CacheDep
router = APIRouter()

@router.get("/chain/{symbol}", summary="Full option chain")
async def get_option_chain(symbol: str, user: CurrentUser, session: SessionDep, cache: CacheDep):
    return {"symbol": symbol, "status": "stub — implement with options service"}

@router.get("/greeks/{symbol}", summary="Greeks for all contracts")
async def get_greeks(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.get("/iv-surface/{symbol}", summary="Volatility surface data")
async def get_iv_surface(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.get("/iv-rank/{symbol}", summary="IV rank and percentile")
async def get_iv_rank(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "iv_rank": None, "iv_percentile": None, "status": "stub"}

@router.get("/term-structure/{symbol}", summary="Term structure curve")
async def get_term_structure(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.get("/skew/{symbol}", summary="Volatility skew metrics")
async def get_skew(symbol: str, user: CurrentUser):
    return {"symbol": symbol, "status": "stub"}

@router.post("/price", summary="Price a single contract")
async def price_contract(user: CurrentUser):
    return {"status": "stub"}
