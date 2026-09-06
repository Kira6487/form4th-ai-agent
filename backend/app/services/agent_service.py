from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.agent import AIAgent
from app.models.company import Company


async def get_company(session: AsyncSession, organization_id: UUID, company_id: UUID) -> Company | None:
    return await session.scalar(select(Company).where(Company.id == company_id, Company.organization_id == organization_id))


async def get_agent(session: AsyncSession, organization_id: UUID, company_id: UUID, agent_id: UUID) -> AIAgent | None:
    return await session.scalar(select(AIAgent).where(AIAgent.id == agent_id, AIAgent.organization_id == organization_id, AIAgent.company_id == company_id))


async def list_agents(session: AsyncSession, organization_id: UUID, company_id: UUID) -> list[AIAgent]:
    return list(await session.scalars(select(AIAgent).where(AIAgent.organization_id == organization_id, AIAgent.company_id == company_id).order_by(AIAgent.created_at.asc())))


async def create_agent(session: AsyncSession, organization_id: UUID, company_id: UUID, data, settings: Settings | None = None) -> AIAgent:
    settings = settings or get_settings()
    agent = AIAgent(organization_id=organization_id, company_id=company_id, model=data.model or settings.gemini_model, **data.model_dump(exclude={"model"}))
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def update_agent(session: AsyncSession, agent: AIAgent, data, settings: Settings | None = None) -> AIAgent:
    values = data.model_dump(exclude_unset=True)
    if values.get("model") is None:
        values["model"] = (settings or get_settings()).gemini_model
    for key, value in values.items():
        setattr(agent, key, value)
    await session.commit()
    await session.refresh(agent)
    return agent
