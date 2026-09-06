from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import auth
from app.core.config import Settings
from app.schemas.auth import AuthenticatedUser


def test_protected_endpoint_requires_token(client) -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_invalid_token_is_rejected(client, monkeypatch) -> None:
    async def reject(_token: str):
        raise auth.InvalidAccessTokenError("invalid")

    monkeypatch.setattr(auth, "verify_access_token", reject)
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired access token"}


def test_valid_authenticated_user_is_accepted(client, monkeypatch) -> None:
    user = AuthenticatedUser(id=uuid4(), email="member@example.com")

    async def accept(_token: str):
        return user

    monkeypatch.setattr(auth, "verify_access_token", accept)
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer valid"})

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


@pytest.mark.asyncio
async def test_supabase_jwt_is_verified_with_cached_signing_key(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    user_id = uuid4()
    settings = Settings(_env_file=None, supabase_url="https://project.example")
    token = jwt.encode(
        {
            "sub": str(user_id),
            "aud": "authenticated",
            "iss": settings.supabase_jwt_issuer,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "email": "verified@example.com",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    async def cached_key(_kid: str, _settings: Settings):
        return private_key.public_key()

    monkeypatch.setattr(auth.jwks_client, "get_key", cached_key)
    user = await auth.verify_access_token(token, settings)

    assert user.id == user_id
    assert str(user.email) == "verified@example.com"


@pytest.mark.asyncio
async def test_expired_supabase_jwt_is_rejected(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(_env_file=None, supabase_url="https://project.example")
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "iss": settings.supabase_jwt_issuer,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    async def cached_key(_kid: str, _settings: Settings):
        return private_key.public_key()

    monkeypatch.setattr(auth.jwks_client, "get_key", cached_key)
    with pytest.raises(auth.InvalidAccessTokenError):
        await auth.verify_access_token(token, settings)
