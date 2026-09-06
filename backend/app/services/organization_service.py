import re
import unicodedata
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMember
from app.repositories import organization_repository
from app.schemas.auth import AuthenticatedUser
from app.schemas.organization import OrganizationCreate


def make_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug or "workspace"


async def create_organization(session: AsyncSession, user: AuthenticatedUser, data: OrganizationCreate) -> Organization:
    slug = data.slug or make_slug(data.name)
    async with session.begin():
        organization = Organization(name=data.name.strip(), slug=slug)
        session.add(organization)
        await session.flush()
        session.add(OrganizationMember(organization_id=organization.id, user_id=user.id, role="owner"))
    return organization


async def list_organizations(session: AsyncSession, user_id: UUID) -> list[Organization]:
    return await organization_repository.list_for_user(session, user_id)
