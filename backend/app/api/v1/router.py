"""V1 API router — aggregates all sub-routers."""
from fastapi import APIRouter

from app.api.v1 import auth, options, dealer, volatility, flow, earnings, alerts

v1_router = APIRouter()

v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(options.router, prefix="/options", tags=["options"])
v1_router.include_router(dealer.router, prefix="/dealer", tags=["dealer"])
v1_router.include_router(volatility.router, prefix="/volatility", tags=["volatility"])
v1_router.include_router(flow.router, prefix="/flow", tags=["flow"])
v1_router.include_router(earnings.router, prefix="/earnings", tags=["earnings"])
v1_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
