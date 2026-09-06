from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import OrganizationContext, require_organization_member, require_organization_role
from app.db.session import get_db_session
from app.schemas.lead import LeadIntent, LeadPage, LeadRead, LeadSource, LeadStatus, LeadUpdate
from app.services.agent_service import get_company
from app.services.leads.lead_service import LeadError, get_lead, list_leads, update_lead

router = APIRouter(prefix="/organizations/{organization_id}/companies/{company_id}/leads", tags=["leads"])


async def _company_or_404(session: AsyncSession, organization_id: UUID, company_id: UUID) -> None:
    if await get_company(session, organization_id, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")


@router.get("", response_model=LeadPage)
async def list_company_leads(
    company_id: UUID,
    status: LeadStatus | None = Query(default=None),
    intent: LeadIntent | None = Query(default=None),
    source: LeadSource | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: OrganizationContext = Depends(require_organization_member()),
    session: AsyncSession = Depends(get_db_session),
) -> LeadPage:
    await _company_or_404(session, context.organization.id, company_id)
    items, total = await list_leads(session, context.organization.id, company_id, status=status, intent=intent, source=source, search=search, page=page, page_size=page_size)
    return LeadPage(items=[LeadRead.model_validate(item) for item in items], page=page, page_size=page_size, total=total)


@router.get("/{lead_id}", response_model=LeadRead)
async def get_company_lead(
    lead_id: UUID,
    company_id: UUID,
    context: OrganizationContext = Depends(require_organization_member()),
    session: AsyncSession = Depends(get_db_session),
) -> LeadRead:
    lead = await get_lead(session, context.organization.id, company_id, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadRead.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadRead)
async def patch_company_lead(
    data: LeadUpdate,
    lead_id: UUID,
    company_id: UUID,
    context: OrganizationContext = Depends(require_organization_role("owner", "admin")),
    session: AsyncSession = Depends(get_db_session),
) -> LeadRead:
    lead = await get_lead(session, context.organization.id, company_id, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        updated = await update_lead(session, lead, data.model_dump(exclude_unset=True))
    except LeadError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return LeadRead.model_validate(updated)
