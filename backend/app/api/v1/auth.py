"""
Authentication endpoints.
POST /auth/login  → JWT pair
POST /auth/refresh → new access token
POST /auth/logout  → blacklist refresh token
GET  /auth/me      → current user
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update

from app.core.cache import CacheKey, CacheTTL, Cache, get_redis
from app.core.security import hash_password, jwt_manager, verify_password
from app.dependencies import CurrentUser, SessionDep
from app.models.user import User

router = APIRouter()


# ----------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


# ----------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------
@router.post("/login", response_model=TokenResponse, summary="Issue JWT token pair")
async def login(body: LoginRequest, session: SessionDep, request: Request):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    # Update last login
    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login=datetime.now(tz=timezone.utc))
    )

    access_token = jwt_manager.create_access_token(str(user.id), user.role)
    refresh_token, _ = jwt_manager.create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=60 * 15,  # 15 minutes
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh(body: RefreshRequest, session: SessionDep):
    try:
        payload = jwt_manager.verify_token(body.refresh_token, expected_type="refresh")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Check blacklist
    cache = Cache(get_redis())
    jti = payload.get("jti", "")
    if await cache.exists(CacheKey.blacklisted_token(jti)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    result = await session.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = jwt_manager.create_access_token(str(user.id), user.role)
    new_refresh, new_jti = jwt_manager.create_refresh_token(str(user.id))

    # Blacklist old refresh token
    import time
    ttl = int(payload["exp"] - time.time())
    if ttl > 0:
        await cache.set(CacheKey.blacklisted_token(jti), "1", ttl)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=60 * 15,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke refresh token")
async def logout(body: RefreshRequest):
    try:
        payload = jwt_manager.decode_unverified(body.refresh_token)
        jti = payload.get("jti", "")
        exp = payload.get("exp", 0)
        import time
        ttl = max(int(exp - time.time()), 1)
        cache = Cache(get_redis())
        await cache.set(CacheKey.blacklisted_token(jti), "1", ttl)
    except Exception:
        pass  # Always return 204 — client-side logout regardless


@router.get("/me", response_model=UserResponse, summary="Current user profile")
async def me(user: CurrentUser):
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: SessionDep):
    """Create a new user account (open registration — disable in production behind admin check)."""
    result = await session.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="analyst",
    )
    session.add(user)
    await session.flush()
    return user
