from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db_session
from app.models.organization import Organization, OrganizationMember
from app.repositories.organization_repository import get_by_id, get_membership
from app.schemas.auth import AuthenticatedUser


@dataclass(frozen=True)
class OrganizationContext:
    organization: Organization
    member: OrganizationMember
    user: AuthenticatedUser


async def get_current_organization(
    organization_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OrganizationContext:
    organization = await get_by_id(session, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    membership = await get_membership(session, organization_id, user.id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this organization")
    return OrganizationContext(organization=organization, member=membership, user=user)


def require_organization_member():
    async def dependency(context: OrganizationContext = Depends(get_current_organization)) -> OrganizationContext:
        return context

    return dependency


def require_organization_role(*roles: str):
    async def dependency(context: OrganizationContext = Depends(get_current_organization)) -> OrganizationContext:
        if context.member.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient organization permissions")
        return context

    return dependency
