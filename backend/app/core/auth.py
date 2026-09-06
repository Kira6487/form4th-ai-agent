import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.schemas.auth import AuthenticatedUser

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


class InvalidAccessTokenError(RuntimeError):
    """Raised when a Supabase access token cannot be verified."""


class SupabaseJWKSClient:
    """Small TTL cache for Supabase's public signing keys."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._keys: dict[str, Any] = {}
        self._expires_at = datetime.min.replace(tzinfo=timezone.utc)

    async def get_key(self, kid: str, settings: Settings) -> Any:
        now = datetime.now(timezone.utc)
        if kid not in self._keys or now >= self._expires_at:
            await self._refresh(settings)
        key = self._keys.get(kid)
        if key is None:
            await self._refresh(settings)
            key = self._keys.get(kid)
        if key is None:
            raise InvalidAccessTokenError("Unknown token signing key")
        return key

    async def _refresh(self, settings: Settings) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(settings.supabase_jwks_url)
            response.raise_for_status()
            payload = response.json()
        keys = payload.get("keys", [])
        self._keys = {item["kid"]: jwt.PyJWK.from_dict(item).key for item in keys if item.get("kid")}
        self._expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)


jwks_client = SupabaseJWKSClient()


async def verify_access_token(token: str, settings: Settings | None = None) -> AuthenticatedUser:
    configured = settings or get_settings()
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        algorithm = header.get("alg")
        if not kid or algorithm not in {"RS256", "ES256"}:
            raise InvalidAccessTokenError("Token has no signing key identifier")
        key = await jwks_client.get_key(kid, configured)
        claims = jwt.decode(
            token,
            key=key,
            algorithms=[algorithm],
            audience=configured.supabase_jwt_audience,
            issuer=configured.supabase_jwt_issuer,
        )
        user_id = UUID(str(claims["sub"]))
    except (httpx.HTTPError, jwt.PyJWTError, KeyError, TypeError, ValueError, InvalidAccessTokenError) as exc:
        raise InvalidAccessTokenError("Invalid access token") from exc

    return AuthenticatedUser(id=user_id, email=claims.get("email"), role=claims.get("role"))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await verify_access_token(credentials.credentials)
    except InvalidAccessTokenError:
        logger.info("Rejected invalid access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
