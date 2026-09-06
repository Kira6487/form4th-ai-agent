import logging

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.schemas.health import AIHealthResponse, DatabaseHealthResponse
from app.services.ai.gemini_service import GeminiConfigurationError, GeminiService, GeminiServiceError
from app.services.database_health import DatabaseNotConfiguredError, check_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/db", response_model=DatabaseHealthResponse)
async def database_health() -> DatabaseHealthResponse:
    """Check the configured PostgreSQL database with a real SELECT 1 query."""
    try:
        await check_database(get_settings())
    except DatabaseNotConfiguredError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is not configured")
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable")

    return DatabaseHealthResponse(status="ok", database="connected")


@router.get("/ai", response_model=AIHealthResponse)
async def ai_health() -> AIHealthResponse:
    """Run a minimal, non-streaming Gemini smoke check when configured."""
    service = GeminiService(get_settings())
    try:
        await service.health_check()
    except GeminiConfigurationError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Gemini is not configured")
    except GeminiServiceError:
        logger.exception("Gemini health check failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Gemini is unavailable")

    return AIHealthResponse(status="ok", provider="gemini", model=service.model)
