import pytest
from sqlalchemy import URL

from app.core.config import Settings
from app.db.session import DatabaseNotConfiguredError, async_database_url
from app.services.database_health import check_database


def test_database_health_reports_missing_configuration(client, monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.health.get_settings", lambda: Settings(_env_file=None))
    response = client.get("/api/v1/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is not configured"}


def test_database_url_supports_encoded_special_characters() -> None:
    raw_url = URL.create(
        drivername="postgresql",
        username="postgres",
        password="p@ss:word",
        host="db.example.test",
        port=5432,
        database="postgres",
    ).render_as_string(hide_password=False)
    url = async_database_url(raw_url)

    assert url == "postgresql+asyncpg://postgres:p%40ss%3Aword@db.example.test:5432/postgres"


@pytest.mark.asyncio
async def test_database_service_rejects_missing_url_without_connecting() -> None:
    with pytest.raises(DatabaseNotConfiguredError):
        await check_database(Settings(_env_file=None))
