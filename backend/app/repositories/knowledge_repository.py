from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeIngestionRun, KnowledgeSource


async def get_source(session: AsyncSession, organization_id: UUID, company_id: UUID, source_id: UUID) -> KnowledgeSource | None:
    return await session.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.organization_id == organization_id,
            KnowledgeSource.company_id == company_id,
        )
    )


async def list_sources(session: AsyncSession, organization_id: UUID, company_id: UUID) -> list[KnowledgeSource]:
    result = await session.scalars(
        select(KnowledgeSource)
        .where(KnowledgeSource.organization_id == organization_id, KnowledgeSource.company_id == company_id)
        .order_by(KnowledgeSource.updated_at.desc())
    )
    return list(result)


async def get_active_run(session: AsyncSession, source_id: UUID) -> KnowledgeIngestionRun | None:
    return await session.scalar(
        select(KnowledgeIngestionRun)
        .where(KnowledgeIngestionRun.source_id == source_id, KnowledgeIngestionRun.status.in_(["pending", "processing"]))
        .order_by(KnowledgeIngestionRun.created_at.desc())
    )


async def get_latest_run(session: AsyncSession, source_id: UUID) -> KnowledgeIngestionRun | None:
    return await session.scalar(
        select(KnowledgeIngestionRun).where(KnowledgeIngestionRun.source_id == source_id).order_by(KnowledgeIngestionRun.created_at.desc())
    )


async def list_documents(session: AsyncSession, organization_id: UUID, company_id: UUID, source_id: UUID, page: int, page_size: int) -> tuple[list[KnowledgeDocument], int]:
    base = select(KnowledgeDocument).where(
        KnowledgeDocument.organization_id == organization_id,
        KnowledgeDocument.company_id == company_id,
        KnowledgeDocument.source_id == source_id,
        KnowledgeDocument.is_active.is_(True),
    )
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    items = list(await session.scalars(base.order_by(KnowledgeDocument.created_at.asc()).offset((page - 1) * page_size).limit(page_size)))
    return items, total


async def list_chunks(session: AsyncSession, organization_id: UUID, company_id: UUID, document_id: UUID, page: int, page_size: int) -> tuple[list[KnowledgeChunk], int]:
    base = select(KnowledgeChunk).where(
        KnowledgeChunk.organization_id == organization_id,
        KnowledgeChunk.company_id == company_id,
        KnowledgeChunk.document_id == document_id,
        KnowledgeChunk.is_active.is_(True),
    )
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    items = list(await session.scalars(base.order_by(KnowledgeChunk.chunk_index.asc()).offset((page - 1) * page_size).limit(page_size)))
    return items, total


async def source_counts(session: AsyncSession, source_id: UUID) -> tuple[int, int]:
    documents = int(await session.scalar(select(func.count()).where(KnowledgeDocument.source_id == source_id, KnowledgeDocument.is_active.is_(True))) or 0)
    chunks = int(await session.scalar(select(func.count()).where(KnowledgeChunk.source_id == source_id, KnowledgeChunk.is_active.is_(True))) or 0)
    return documents, chunks
