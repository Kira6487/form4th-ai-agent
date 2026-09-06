from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import OrganizationContext, require_organization_member, require_organization_role
from app.db.session import get_db_session
from app.schemas.agent import AIAgentCreate, AIAgentRead, AIAgentUpdate
from app.services.agent_service import create_agent, get_agent, get_company, list_agents, update_agent

router = APIRouter(prefix="/organizations/{organization_id}/companies/{company_id}/agents", tags=["agents"])


async def _company_or_404(session: AsyncSession, organization_id: UUID, company_id: UUID) -> None:
    if await get_company(session, organization_id, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")


@router.post("", response_model=AIAgentRead, status_code=status.HTTP_201_CREATED)
async def create(data: AIAgentCreate, company_id: UUID, context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> AIAgentRead:
    await _company_or_404(session, context.organization.id, company_id)
    return AIAgentRead.model_validate(await create_agent(session, context.organization.id, company_id, data))


@router.get("", response_model=list[AIAgentRead])
async def list_all(company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> list[AIAgentRead]:
    await _company_or_404(session, context.organization.id, company_id)
    return [AIAgentRead.model_validate(agent) for agent in await list_agents(session, context.organization.id, company_id)]


@router.get("/{agent_id}", response_model=AIAgentRead)
async def get_one(agent_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> AIAgentRead:
    agent = await get_agent(session, context.organization.id, company_id, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="AI agent not found")
    return AIAgentRead.model_validate(agent)


@router.patch("/{agent_id}", response_model=AIAgentRead)
async def update(agent_id: UUID, data: AIAgentUpdate, company_id: UUID, context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> AIAgentRead:
    agent = await get_agent(session, context.organization.id, company_id, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="AI agent not found")
    return AIAgentRead.model_validate(await update_agent(session, agent, data))
