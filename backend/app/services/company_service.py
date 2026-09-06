from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.repositories import company_repository
from app.schemas.company import CompanyCreate, CompanyUpdate


async def list_companies(session: AsyncSession, organization_id: UUID) -> list[Company]:
    return await company_repository.list_for_organization(session, organization_id)


async def get_company(session: AsyncSession, organization_id: UUID, company_id: UUID) -> Company | None:
    return await company_repository.get_for_organization(session, organization_id, company_id)


async def create_company(session: AsyncSession, organization_id: UUID, data: CompanyCreate) -> Company:
    values = data.model_dump()
    if values.get("website") is not None:
        values["website"] = str(values["website"])
    company = Company(organization_id=organization_id, **values)
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


async def update_company(session: AsyncSession, company: Company, data: CompanyUpdate) -> Company:
    values = data.model_dump(exclude_unset=True)
    if values.get("website") is not None:
        values["website"] = str(values["website"])
    for field, value in values.items():
        setattr(company, field, value)
    await session.commit()
    await session.refresh(company)
    return company
