from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_name: str = "form4th-ai-agent"
    frontend_origin: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    gemini_api_key: str | None = Field(default=None, repr=False)
    gemini_model: str = "gemini-3.7-flash"
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimensions: int = 768

    supabase_url: str = "https://vytmhyerzlxqheisordr.supabase.co"
    supabase_publishable_key: str | None = Field(default=None, repr=False)
    supabase_anon_key: str | None = Field(default=None, repr=False)
    supabase_service_role_key: str | None = Field(default=None, repr=False)
    database_url: str | None = Field(default=None, repr=False)
    firecrawl_api_key: str | None = Field(default=None, repr=False)

    allowed_origins: str = "http://localhost:3000"

    @property
    def supabase_jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_jwt_issuer}/.well-known/jwks.json"

    @property
    def supabase_jwt_audience(self) -> str:
        return "authenticated"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
