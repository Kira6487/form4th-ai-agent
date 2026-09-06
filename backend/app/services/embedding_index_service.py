import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeSource
from app.services.ai.embedding_service import GeminiEmbeddingService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingIndexResult:
    total: int
    processed: int
    embedded: int
    pending: int
    failed: int


def embedding_is_current(chunk: KnowledgeChunk, content_hash: str, model: str, dimensions: int) -> bool:
    return bool(chunk.embedding_status == "ready" and chunk.content_hash == content_hash and chunk.embedding_model == model and chunk.embedding_dimensions == dimensions)


def _safe_error(exc: Exception) -> str:
    message = re.sub(r"(?:AIza|sk|fc)[-_A-Za-z0-9]+", "[redacted]", str(exc))
    return message[:500] or "Embedding failed"


async def embedding_counts(session: AsyncSession, organization_id: UUID, company_id: UUID, source_id: UUID | None = None) -> tuple[int, int, int, int]:
    filters = [KnowledgeChunk.organization_id == organization_id, KnowledgeChunk.company_id == company_id, KnowledgeChunk.is_active.is_(True)]
    if source_id:
        filters.append(KnowledgeChunk.source_id == source_id)
    from sqlalchemy import func
    total = int(await session.scalar(select(func.count()).select_from(KnowledgeChunk).where(*filters)) or 0)
    ready = int(await session.scalar(select(func.count()).select_from(KnowledgeChunk).where(*filters, KnowledgeChunk.embedding_status == "ready")) or 0)
    pending = int(await session.scalar(select(func.count()).select_from(KnowledgeChunk).where(*filters, KnowledgeChunk.embedding_status.in_(["pending", "processing"]))) or 0)
    failed = int(await session.scalar(select(func.count()).select_from(KnowledgeChunk).where(*filters, KnowledgeChunk.embedding_status == "failed")) or 0)
    return total, ready, pending, failed


async def index_pending_embeddings(
    session: AsyncSession,
    organization_id: UUID,
    company_id: UUID,
    source_id: UUID | None = None,
    limit: int | None = None,
    settings: Settings | None = None,
    embedding_service: GeminiEmbeddingService | None = None,
) -> EmbeddingIndexResult:
    settings = settings or get_settings()
    batch_limit = min(limit or settings.embedding_batch_size, settings.embedding_batch_size)
    filters = [
        KnowledgeChunk.organization_id == organization_id,
        KnowledgeChunk.company_id == company_id,
        KnowledgeChunk.is_active.is_(True),
        KnowledgeChunk.embedding_status.in_(["pending", "failed"]),
        KnowledgeDocument.is_active.is_(True),
        KnowledgeSource.status != "disabled",
    ]
    if source_id:
        filters.append(KnowledgeChunk.source_id == source_id)
    rows = list(await session.scalars(select(KnowledgeChunk).join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id).join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id).where(*filters).order_by(KnowledgeChunk.created_at.asc()).limit(batch_limit)))
    total, _, _, _ = await embedding_counts(session, organization_id, company_id, source_id)
    if not rows:
        return EmbeddingIndexResult(total, 0, 0, 0, 0)
    original = [(chunk.id, chunk.content_hash) for chunk in rows]
    for chunk in rows:
        chunk.embedding_status = "processing"
        chunk.embedding_error = None
    await session.commit()
    service = embedding_service or GeminiEmbeddingService(settings)
    try:
        titles = []
        for chunk in rows:
            metadata = chunk.chunk_metadata if isinstance(chunk.chunk_metadata, dict) else {}
            titles.append((str(metadata.get("title") or metadata.get("document") or ""), chunk.content))
        vectors = await service.embed_documents(titles)
    except Exception as exc:
        message = _safe_error(exc if isinstance(exc, Exception) else RuntimeError(str(exc)))
        await session.execute(update(KnowledgeChunk).where(KnowledgeChunk.id.in_([item[0] for item in original]), KnowledgeChunk.embedding_status == "processing").values(embedding_status="failed", embedding_error=message))
        await session.commit()
        return EmbeddingIndexResult(total, len(rows), 0, 0, len(rows))
    embedded = 0
    for chunk, (_, original_hash), vector in zip(rows, original, vectors):
        current = await session.scalar(select(KnowledgeChunk).where(KnowledgeChunk.id == chunk.id, KnowledgeChunk.organization_id == organization_id, KnowledgeChunk.company_id == company_id))
        if current is None or not current.is_active or current.content_hash != original_hash:
            if current is not None:
                current.embedding_status = "pending"
            continue
        current.embedding = vector
        current.embedding_model = service.model
        current.embedding_dimensions = len(vector)
        current.embedded_at = datetime.now(timezone.utc)
        current.embedding_status = "ready"
        current.embedding_error = None
        embedded += 1
    await session.commit()
    _, _, pending, failed = await embedding_counts(session, organization_id, company_id, source_id)
    logger.info("embeddings indexed organization_id=%s company_id=%s source_id=%s embedded=%s", organization_id, company_id, source_id, embedded)
    return EmbeddingIndexResult(total, len(rows), embedded, pending, failed)


async def reset_source_embeddings(session: AsyncSession, organization_id: UUID, company_id: UUID, source_id: UUID, force: bool = False) -> int:
    source = await session.scalar(select(KnowledgeSource).where(KnowledgeSource.id == source_id, KnowledgeSource.organization_id == organization_id, KnowledgeSource.company_id == company_id))
    if source is None:
        return 0
    values = {"embedding_status": "pending", "embedding_error": None}
    filters = [KnowledgeChunk.organization_id == organization_id, KnowledgeChunk.company_id == company_id, KnowledgeChunk.source_id == source_id, KnowledgeChunk.is_active.is_(True)]
    if not force:
        settings = get_settings()
        from sqlalchemy import or_
        filters.append(or_(KnowledgeChunk.embedding_status != "ready", KnowledgeChunk.embedding_model != settings.gemini_embedding_model, KnowledgeChunk.embedding_dimensions != settings.gemini_embedding_dimensions))
    result = await session.execute(update(KnowledgeChunk).where(*filters).values(**values))
    await session.commit()
    return int(result.rowcount or 0)
