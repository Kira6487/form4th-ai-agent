import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.core.auth import get_current_user
from app.main import app
from app.models import Company, Organization, OrganizationMember
from app.schemas.auth import AuthenticatedUser


def seed_tenants(session_factory):
    user_a = AuthenticatedUser(id=uuid4(), email="a@example.com")
    user_b = AuthenticatedUser(id=uuid4(), email="b@example.com")
    organization_a = Organization(name="Organization A", slug="organization-a")
    organization_b = Organization(name="Organization B", slug="organization-b")

    async def seed():
        async with session_factory() as session:
            session.add_all([organization_a, organization_b])
            await session.flush()
            session.add_all([
                OrganizationMember(organization_id=organization_a.id, user_id=user_a.id, role="owner"),
                OrganizationMember(organization_id=organization_b.id, user_id=user_b.id, role="owner"),
                Company(organization_id=organization_a.id, name="Company A"),
                Company(organization_id=organization_b.id, name="Company B"),
            ])
            await session.commit()

    asyncio.run(seed())
    return user_a, user_b, organization_a, organization_b


def test_users_can_only_access_their_own_organization(tenant_client) -> None:
    client, session_factory = tenant_client
    user_a, user_b, organization_a, organization_b = seed_tenants(session_factory)
    app.dependency_overrides[get_current_user] = lambda: user_a

    own_list = client.get("/api/v1/organizations")
    other_organization = client.get(f"/api/v1/organizations/{organization_b.id}")
    other_companies = client.get(f"/api/v1/organizations/{organization_b.id}/companies")

    assert own_list.status_code == 200
    assert [item["id"] for item in own_list.json()] == [str(organization_a.id)]
    assert other_organization.status_code == 403
    assert other_companies.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: user_b
    user_b_companies = client.get(f"/api/v1/organizations/{organization_b.id}/companies")
    user_b_other = client.get(f"/api/v1/organizations/{organization_a.id}/companies")
    assert user_b_companies.status_code == 200
    assert user_b_companies.json()[0]["name"] == "Company B"
    assert user_b_other.status_code == 403


def test_company_crud_and_role_authorization(tenant_client) -> None:
    client, session_factory = tenant_client
    user_a, _, organization_a, _ = seed_tenants(session_factory)
    app.dependency_overrides[get_current_user] = lambda: user_a

    created = client.post(
        f"/api/v1/organizations/{organization_a.id}/companies",
        json={"name": "New Company", "website": "https://example.com", "industry": "Technology"},
    )
    assert created.status_code == 201
    company_id = created.json()["id"]

    detail = client.get(f"/api/v1/organizations/{organization_a.id}/companies/{company_id}")
    updated = client.patch(
        f"/api/v1/organizations/{organization_a.id}/companies/{company_id}",
        json={"status": "archived", "description": "Archived profile"},
    )
    assert detail.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["status"] == "archived"

    async def demote_owner():
        async with session_factory() as session:
            member = await session.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == organization_a.id,
                    OrganizationMember.user_id == user_a.id,
                )
            )
            member.role = "member"
            await session.commit()

    asyncio.run(demote_owner())
    forbidden_create = client.post(
        f"/api/v1/organizations/{organization_a.id}/companies",
        json={"name": "Not Allowed"},
    )
    assert forbidden_create.status_code == 403
