"""
FastAPI dependency injection providers.
Used with Depends() in route handlers.
"""
from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.cache import Cache, get_redis
from app.core.database import AsyncSession, get_session
from app.core.rate_limiter import rate_limiter
from app.core.security import jwt_manager
from app.models.user import User
from sqlalchemy import select

bearer_scheme = HTTPBearer(auto_error=True)


# ----------------------------------------------------------------
# DB session dependency
# ----------------------------------------------------------------
SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ----------------------------------------------------------------
# Cache dependency
# ----------------------------------------------------------------
def get_cache() -> Cache:
    return Cache(get_redis())


CacheDep = Annotated[Cache, Depends(get_cache)]


# ----------------------------------------------------------------
# Auth dependencies
# ----------------------------------------------------------------
async def get_current_user(
    session: SessionDep,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """
    Validates Bearer JWT and returns the authenticated User.
    Raises 401 on any token error.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt_manager.verify_token(credentials.credentials, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    # Check Redis blacklist (logout)
    cache = Cache(get_redis())
    from app.core.cache import CacheKey
    if await cache.exists(CacheKey.blacklisted_token(payload.get("jti", ""))):
        raise credentials_exception

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    """Role-based access control — usage: Depends(require_role('admin', 'trader'))"""
    async def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized for this endpoint",
            )
        return user
    return _check


AdminOnly = Depends(require_role("admin"))
TraderOrAbove = Depends(require_role("admin", "trader"))
AnalystOrAbove = Depends(require_role("admin", "trader", "analyst"))
