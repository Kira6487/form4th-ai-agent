from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


async def list_for_organization(session: AsyncSession, organization_id: UUID) -> list[Company]:
    result = await session.scalars(
        select(Company).where(Company.organization_id == organization_id).order_by(Company.updated_at.desc())
    )
    return list(result)


async def get_for_organization(session: AsyncSession, organization_id: UUID, company_id: UUID) -> Company | None:
    return await session.scalar(
        select(Company).where(Company.organization_id == organization_id, Company.id == company_id)
    )
