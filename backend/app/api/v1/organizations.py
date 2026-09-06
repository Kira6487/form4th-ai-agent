import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.authorization import OrganizationContext, get_current_organization
from app.db.session import get_db_session
from app.schemas.auth import AuthenticatedUser
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.services.organization_service import create_organization, list_organizations

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create(
    data: OrganizationCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OrganizationRead:
    try:
        organization = await create_organization(session, user, data)
    except IntegrityError as exc:
        logger.info("Organization creation conflict")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug already exists") from exc
    return OrganizationRead.model_validate(organization)


@router.get("", response_model=list[OrganizationRead])
async def list_all(
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[OrganizationRead]:
    organizations = await list_organizations(session, user.id)
    return [OrganizationRead.model_validate(item) for item in organizations]


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_one(context: OrganizationContext = Depends(get_current_organization)) -> OrganizationRead:
    return OrganizationRead.model_validate(context.organization)
