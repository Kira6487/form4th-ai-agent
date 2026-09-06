from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.me import router as me_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.companies import router as companies_router
from app.api.v1.knowledge import router as knowledge_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(me_router)
api_router.include_router(organizations_router)
api_router.include_router(companies_router)
api_router.include_router(knowledge_router)
