from sqlalchemy import text

from app.core.config import Settings
from app.db.session import DatabaseNotConfiguredError, engine_for_settings


async def check_database(settings: Settings) -> None:
    """Execute a real, read-only query against the configured PostgreSQL."""
    if not settings.database_url:
        raise DatabaseNotConfiguredError("DATABASE_URL is not configured")

    engine = engine_for_settings(settings)
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
