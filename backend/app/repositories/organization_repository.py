from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMember


async def list_for_user(session: AsyncSession, user_id: UUID) -> list[Organization]:
    result = await session.scalars(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == user_id)
        .order_by(Organization.name)
    )
    return list(result)


async def get_by_id(session: AsyncSession, organization_id: UUID) -> Organization | None:
    return await session.get(Organization, organization_id)


async def get_membership(session: AsyncSession, organization_id: UUID, user_id: UUID) -> OrganizationMember | None:
    return await session.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
