from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource
from app.models.vector import Vector768
from app.services.ai.embedding_service import GeminiEmbeddingService


class VectorDatabaseRequiredError(RuntimeError):
    """Raised when semantic retrieval is attempted without PostgreSQL/pgvector."""


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    source_id: UUID
    title: str
    content: str
    similarity: float
    source_url: str | None
    metadata: dict[str, Any]


def build_retrieval_statement(organization_id: UUID, company_id: UUID, query_vector: list[float], limit: int, min_similarity: float):
    vector_param = bindparam("query_embedding", query_vector, type_=Vector768(768))
    distance = KnowledgeChunk.embedding.op("<=>")(vector_param)
    source_url = func.coalesce(KnowledgeDocument.source_url, KnowledgeSource.source_url)
    return (
        select(KnowledgeChunk.id, KnowledgeChunk.document_id, KnowledgeChunk.source_id, KnowledgeDocument.title, KnowledgeChunk.content, (1 - distance).label("similarity"), source_url.label("source_url"), KnowledgeChunk.chunk_metadata)
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .where(
            KnowledgeChunk.organization_id == organization_id,
            KnowledgeChunk.company_id == company_id,
            KnowledgeChunk.is_active.is_(True),
            KnowledgeChunk.embedding_status == "ready",
            KnowledgeChunk.embedding.is_not(None),
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.company_id == company_id,
            KnowledgeDocument.is_active.is_(True),
            KnowledgeSource.organization_id == organization_id,
            KnowledgeSource.company_id == company_id,
            KnowledgeSource.status == "ready",
            distance <= (1 - min_similarity),
        )
        .order_by(distance.asc())
        .limit(limit)
    )


async def search_knowledge(
    session: AsyncSession,
    organization_id: UUID,
    company_id: UUID,
    query: str,
    limit: int | None = None,
    min_similarity: float | None = None,
    settings: Settings | None = None,
    embedding_service: GeminiEmbeddingService | None = None,
) -> list[RetrievedChunk]:
    settings = settings or get_settings()
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        raise VectorDatabaseRequiredError("Semantic retrieval requires PostgreSQL with pgvector")
    top_k = min(limit or settings.rag_default_top_k, settings.rag_max_top_k)
    threshold = settings.rag_min_similarity if min_similarity is None else min_similarity
    service = embedding_service or GeminiEmbeddingService(settings)
    query_vector = await service.embed_query(query)
    result = await session.execute(build_retrieval_statement(organization_id, company_id, query_vector, top_k, threshold))
    items: list[RetrievedChunk] = []
    for row in result:
        mapping = row._mapping
        items.append(RetrievedChunk(
            chunk_id=mapping[KnowledgeChunk.id], document_id=mapping[KnowledgeChunk.document_id], source_id=mapping[KnowledgeChunk.source_id],
            title=mapping[KnowledgeDocument.title], content=mapping[KnowledgeChunk.content], similarity=float(mapping["similarity"]),
            source_url=mapping["source_url"], metadata=mapping[KnowledgeChunk.chunk_metadata] if isinstance(mapping[KnowledgeChunk.chunk_metadata], dict) else {},
        ))
    return [item for item in items if item.similarity >= threshold]
