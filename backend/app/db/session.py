from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when a database operation is requested without DATABASE_URL."""


def async_database_url(database_url: str) -> str:
    """Return a PostgreSQL URL using the asyncpg SQLAlchemy dialect."""
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")
    elif url.drivername == "postgresql+psycopg":
        url = url.set(drivername="postgresql+asyncpg")
    return url.render_as_string(hide_password=False)


@lru_cache
def get_engine(database_url: str) -> AsyncEngine:
    if not database_url:
        raise DatabaseNotConfiguredError("DATABASE_URL is not configured")
    return create_async_engine(async_database_url(database_url), pool_pre_ping=True)


def engine_for_settings(settings: Settings | None = None) -> AsyncEngine:
    configured = settings or get_settings()
    return get_engine(configured.database_url or "")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = engine_for_settings()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
