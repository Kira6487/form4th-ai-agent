from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import OrganizationContext, require_organization_member, require_organization_role
from app.db.session import get_db_session
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.company_service import create_company, get_company, list_companies, update_company

router = APIRouter(prefix="/organizations/{organization_id}/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create(
    data: CompanyCreate,
    context: OrganizationContext = Depends(require_organization_role("owner", "admin")),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyRead:
    company = await create_company(session, context.organization.id, data)
    return CompanyRead.model_validate(company)


@router.get("", response_model=list[CompanyRead])
async def list_all(
    context: OrganizationContext = Depends(require_organization_member()),
    session: AsyncSession = Depends(get_db_session),
) -> list[CompanyRead]:
    companies = await list_companies(session, context.organization.id)
    return [CompanyRead.model_validate(item) for item in companies]


@router.get("/{company_id}", response_model=CompanyRead)
async def get_one(
    company_id: UUID,
    context: OrganizationContext = Depends(require_organization_member()),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyRead:
    company = await get_company(session, context.organization.id, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyRead.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyRead)
async def update(
    company_id: UUID,
    data: CompanyUpdate,
    context: OrganizationContext = Depends(require_organization_role("owner", "admin")),
    session: AsyncSession = Depends(get_db_session),
) -> CompanyRead:
    company = await get_company(session, context.organization.id, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    updated = await update_company(session, company, data)
    return CompanyRead.model_validate(updated)
