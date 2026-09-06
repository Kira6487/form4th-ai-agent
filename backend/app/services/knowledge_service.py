import logging
import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

from pypdf import PdfReader
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.company import Company
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeIngestionRun, KnowledgeSource
from app.repositories.knowledge_repository import (
    get_active_run,
    get_latest_run,
    get_source,
    list_chunks,
    list_documents,
    list_sources,
    source_counts,
)
from app.services.ingestion.chunker import chunk_content
from app.services.ingestion.firecrawl_provider import FirecrawlProvider, WebCrawlerProvider
from app.services.ingestion.hashing import content_hash
from app.services.ingestion.normalizer import normalize_content
from app.services.ingestion.pdf_validation import validate_pdf_bytes
from app.services.ingestion.storage import StorageError, SupabaseStorage, storage_path
from app.services.ingestion.url_validation import validate_website_url

logger = logging.getLogger(__name__)


class KnowledgeError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def company_for_source(session: AsyncSession, organization_id: UUID, company_id: UUID) -> Company | None:
    return await session.scalar(select(Company).where(Company.id == company_id, Company.organization_id == organization_id))


async def source_with_counts(session: AsyncSession, source: KnowledgeSource) -> KnowledgeSource:
    await session.refresh(source)
    documents, chunks = await source_counts(session, source.id)
    source.documents_count = documents  # type: ignore[attr-defined]
    source.chunks_count = chunks  # type: ignore[attr-defined]
    return source


def _safe_error(error: Exception) -> str:
    message = re.sub(r"(?:fc|sk|AIza)[-_A-Za-z0-9]+", "[redacted]", str(error))
    return message[:500] or "Ingestion failed"


async def _new_run(session: AsyncSession, source: KnowledgeSource, provider: str | None = None) -> KnowledgeIngestionRun:
    active = await get_active_run(session, source.id)
    if active:
        raise KnowledgeError("source_already_processing", "This source is already being processed")
    run = KnowledgeIngestionRun(
        organization_id=source.organization_id,
        company_id=source.company_id,
        source_id=source.id,
        status="pending",
        provider=provider,
    )
    session.add(run)
    await session.flush()
    source.status = "processing"
    source.last_error = None
    return run


async def _fail_run(session: AsyncSession, source: KnowledgeSource, run: KnowledgeIngestionRun, code: str, error: Exception | str) -> None:
    message = _safe_error(error if isinstance(error, Exception) else RuntimeError(error))
    source_id, run_id = source.id, run.id
    await session.rollback()
    source = await session.get(KnowledgeSource, source_id) or source
    run = await session.get(KnowledgeIngestionRun, run_id) or run
    source.status = "failed"
    source.last_error = message
    run.status = "failed"
    run.error_code = code
    run.error_message = message
    run.completed_at = _now()
    await session.commit()
    logger.warning(
        "ingestion failed organization_id=%s company_id=%s source_id=%s ingestion_run_id=%s error_code=%s",
        source.organization_id, source.company_id, source.id, run.id, code,
    )


def _crawl_pages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pages = payload.get("data") or payload.get("results") or payload.get("pages") or []
    if isinstance(pages, dict):
        pages = pages.get("data") or pages.get("results") or []
    return [page if isinstance(page, dict) else {} for page in pages]


def _page_content(page: dict[str, Any]) -> tuple[str, str, str | None, dict[str, Any]]:
    metadata = page.get("metadata") if isinstance(page.get("metadata"), dict) else {}
    content = page.get("markdown") or page.get("content") or page.get("text") or ""
    title = metadata.get("title") or page.get("title") or page.get("url") or "Website page"
    source_url = metadata.get("sourceURL") or metadata.get("source_url") or page.get("url")
    language = metadata.get("language") or metadata.get("lang")
    return str(title), str(content), str(source_url) if source_url else None, {
        "title": title,
        "description": metadata.get("description"),
        "language": language,
        "source_url": source_url,
        "status_code": metadata.get("statusCode") or metadata.get("status_code"),
    }


def _extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    return normalize_content("\n\n".join(page.extract_text() or "" for page in reader.pages))


async def _activate_content(
    session: AsyncSession,
    source: KnowledgeSource,
    run: KnowledgeIngestionRun,
    pages: list[dict[str, Any]],
    settings: Settings,
) -> tuple[int, int]:
    documents: list[KnowledgeDocument] = []
    chunks: list[KnowledgeChunk] = []
    seen_hashes: set[str] = set()
    for page in pages:
        title, raw_content, source_url, metadata = _page_content(page)
        normalized = normalize_content(raw_content)
        if not normalized:
            continue
        digest = content_hash(normalized)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        document = KnowledgeDocument(
            organization_id=source.organization_id,
            company_id=source.company_id,
            source_id=source.id,
            ingestion_run_id=run.id,
            title=title[:500],
            content=normalized,
            content_type="text/markdown",
            language=metadata.get("language"),
            source_url=source_url,
            content_hash=digest,
            document_metadata=metadata,
            is_active=False,
        )
        documents.append(document)
        for piece in chunk_content(normalized, settings.chunk_target_approx_tokens, settings.chunk_overlap_approx_tokens):
            chunk_metadata = {
                **piece.metadata,
                "source": source.name,
                "document": title[:500],
                "title": title[:500],
            }
            chunks.append(KnowledgeChunk(
                organization_id=source.organization_id,
                company_id=source.company_id,
                source_id=source.id,
                document_id=document.id,
                ingestion_run_id=run.id,
                chunk_index=piece.metadata["chunk_index"],
                content=piece.content,
                content_hash=content_hash(piece.content),
                approx_token_count=piece.approx_token_count,
                chunk_metadata=chunk_metadata,
                is_active=False,
            ))
    if not documents:
        raise KnowledgeError("no_content", "No extractable content was found")
    session.add_all(documents)
    await session.flush()
    # Chunks are created after document ids are assigned. The default UUID is available after flush.
    for chunk, document in zip(chunks, [doc for doc in documents for _ in chunk_content(doc.content, settings.chunk_target_approx_tokens, settings.chunk_overlap_approx_tokens)]):
        chunk.document_id = document.id
    session.add_all(chunks)
    await session.flush()
    await session.execute(update(KnowledgeDocument).where(KnowledgeDocument.source_id == source.id, KnowledgeDocument.ingestion_run_id != run.id).values(is_active=False))
    await session.execute(update(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id, KnowledgeChunk.ingestion_run_id != run.id).values(is_active=False))
    await session.execute(update(KnowledgeDocument).where(KnowledgeDocument.ingestion_run_id == run.id).values(is_active=True))
    await session.execute(update(KnowledgeChunk).where(KnowledgeChunk.ingestion_run_id == run.id).values(is_active=True))
    run.documents_processed = len(documents)
    run.chunks_created = len(chunks)
    run.status = "completed"
    run.completed_at = _now()
    source.status = "ready"
    source.last_indexed_at = _now()
    source.last_error = None
    await session.commit()
    logger.info(
        "ingestion completed organization_id=%s company_id=%s source_id=%s ingestion_run_id=%s documents=%s chunks=%s",
        source.organization_id, source.company_id, source.id, run.id, len(documents), len(chunks),
    )
    return len(documents), len(chunks)


async def create_manual_source(session: AsyncSession, organization_id: UUID, company_id: UUID, user_id: UUID, name: str, title: str, content: str, description: str | None, settings: Settings | None = None) -> KnowledgeSource:
    company = await company_for_source(session, organization_id, company_id)
    if company is None:
        raise KnowledgeError("company_not_found", "Company not found")
    settings = settings or get_settings()
    source = KnowledgeSource(organization_id=organization_id, company_id=company_id, source_type="manual", name=name, description=description, created_by=user_id)
    session.add(source)
    await session.flush()
    run = await _new_run(session, source)
    run.status = "processing"
    run.started_at = _now()
    await session.commit()
    try:
        await _activate_content(session, source, run, [{"title": title, "content": content}], settings)
    except Exception as exc:
        await _fail_run(session, source, run, getattr(exc, "code", "processing_failed"), exc)
        raise
    return await source_with_counts(session, source)


async def create_website_source(session: AsyncSession, organization_id: UUID, company_id: UUID, user_id: UUID, name: str, source_url: str, description: str | None = None, settings: Settings | None = None, provider: WebCrawlerProvider | None = None) -> KnowledgeSource:
    company = await company_for_source(session, organization_id, company_id)
    if company is None:
        raise KnowledgeError("company_not_found", "Company not found")
    try:
        source_url = validate_website_url(source_url)
    except ValueError as exc:
        raise KnowledgeError("invalid_url", str(exc)) from exc
    settings = settings or get_settings()
    source = KnowledgeSource(organization_id=organization_id, company_id=company_id, source_type="website", name=name, description=description, source_url=source_url, created_by=user_id)
    session.add(source)
    await session.flush()
    run = await _new_run(session, source, provider="firecrawl")
    await session.commit()
    try:
        provider = provider or FirecrawlProvider(settings)
        run.external_job_id = await provider.start_crawl(source_url, min(settings.firecrawl_max_pages, 100))
        run.status = "processing"
        run.started_at = _now()
        await session.commit()
    except Exception as exc:
        await _fail_run(session, source, run, "crawler_unavailable" if "not configured" in str(exc).lower() else "crawl_start_failed", exc)
        raise KnowledgeError("crawler_unavailable", "Website crawler is unavailable") from exc
    logger.info("ingestion started organization_id=%s company_id=%s source_id=%s ingestion_run_id=%s provider=firecrawl", organization_id, company_id, source.id, run.id)
    return await source_with_counts(session, source)


async def create_pdf_source(session: AsyncSession, organization_id: UUID, company_id: UUID, user_id: UUID, name: str, filename: str | None, content_type: str | None, data: bytes, description: str | None = None, settings: Settings | None = None) -> KnowledgeSource:
    company = await company_for_source(session, organization_id, company_id)
    if company is None:
        raise KnowledgeError("company_not_found", "Company not found")
    settings = settings or get_settings()
    try:
        safe_name = validate_pdf_bytes(filename, content_type, data, settings.max_pdf_size_mb * 1024 * 1024)
        content = _extract_pdf_text(data)
        if not content:
            raise KnowledgeError("pdf_no_text", "No extractable text found. OCR is not supported in Phase 3.")
    except KnowledgeError:
        raise
    except Exception as exc:
        raise KnowledgeError("invalid_pdf", "The uploaded file could not be processed as a PDF") from exc
    source = KnowledgeSource(organization_id=organization_id, company_id=company_id, source_type="pdf", name=name, description=description, created_by=user_id)
    session.add(source)
    await session.flush()
    object_id = uuid4()
    path = storage_path(organization_id, company_id, source.id, object_id)
    source.storage_path = path
    run = await _new_run(session, source, provider="pypdf")
    run.status = "processing"
    run.started_at = _now()
    await session.commit()
    storage = None
    try:
        storage = SupabaseStorage(settings)
        await storage.upload_pdf(path, data)
        await _activate_content(session, source, run, [{"title": safe_name, "content": content}], settings)
    except StorageError as exc:
        if storage:
            try:
                await storage.delete(path)
            except StorageError:
                logger.warning("storage cleanup failed source_id=%s", source.id)
        await _fail_run(session, source, run, "storage_unavailable", exc)
        raise KnowledgeError("storage_unavailable", "Private PDF storage is unavailable") from exc
    except Exception as exc:
        if storage:
            try:
                await storage.delete(path)
            except StorageError:
                logger.warning("storage cleanup failed source_id=%s", source.id)
        await _fail_run(session, source, run, getattr(exc, "code", "processing_failed"), exc)
        raise KnowledgeError("pdf_processing_failed", "The PDF could not be processed") from exc
    return await source_with_counts(session, source)


async def poll_website_source(session: AsyncSession, source: KnowledgeSource, settings: Settings | None = None, provider: WebCrawlerProvider | None = None) -> KnowledgeIngestionRun:
    settings = settings or get_settings()
    run = await get_active_run(session, source.id)
    if run is None or not run.external_job_id:
        latest = await get_latest_run(session, source.id)
        return latest  # type: ignore[return-value]
    try:
        provider = provider or FirecrawlProvider(settings)
        payload = await provider.get_crawl_status(run.external_job_id)
        state = str(payload.get("status") or "processing").lower()
        if state in {"failed", "error", "cancelled", "canceled"}:
            await _fail_run(session, source, run, "crawl_failed", payload.get("error") or "Website crawl failed")
        elif state in {"completed", "complete", "done"}:
            await _activate_content(session, source, run, _crawl_pages(payload), settings)
        else:
            run.status = "processing"
            await session.commit()
    except Exception as exc:
        if isinstance(exc, KnowledgeError):
            await _fail_run(session, source, run, exc.code, exc)
        else:
            await _fail_run(session, source, run, "crawl_status_failed", exc)
    return run


async def reindex_source(session: AsyncSession, source: KnowledgeSource, user_id: UUID, settings: Settings | None = None, provider: WebCrawlerProvider | None = None) -> KnowledgeSource:
    settings = settings or get_settings()
    if source.status == "disabled":
        raise KnowledgeError("source_disabled", "Disabled sources cannot be reindexed")
    run = await _new_run(session, source, provider="firecrawl" if source.source_type == "website" else "local")
    await session.commit()
    if source.source_type == "website":
        try:
            provider = provider or FirecrawlProvider(settings)
            run.external_job_id = await provider.start_crawl(source.source_url or "", min(settings.firecrawl_max_pages, 100))
            run.status = "processing"
            run.started_at = _now()
            await session.commit()
        except Exception as exc:
            await _fail_run(session, source, run, "crawl_start_failed", exc)
            raise KnowledgeError("crawler_unavailable", "Website crawler is unavailable") from exc
        return await source_with_counts(session, source)
    run.status = "processing"
    run.started_at = _now()
    await session.commit()
    try:
        if source.source_type == "pdf":
            if not source.storage_path:
                raise KnowledgeError("storage_unavailable", "Stored PDF path is missing")
            data = await SupabaseStorage(settings).download(source.storage_path)
            content = _extract_pdf_text(data)
            if not content:
                raise KnowledgeError("pdf_no_text", "No extractable text found. OCR is not supported in Phase 3.")
            pages = [{"title": source.name, "content": content}]
        else:
            active_docs = list(await session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source_id == source.id, KnowledgeDocument.is_active.is_(True)).order_by(KnowledgeDocument.created_at.asc())))
            if not active_docs:
                raise KnowledgeError("no_previous_content", "No previous content is available for reindex")
            pages = [{"title": doc.title, "content": doc.content, "url": doc.source_url} for doc in active_docs]
        await _activate_content(session, source, run, pages, settings)
    except Exception as exc:
        await _fail_run(session, source, run, getattr(exc, "code", "reindex_failed"), exc)
        raise
    return await source_with_counts(session, source)


async def disable_source(session: AsyncSession, source: KnowledgeSource) -> KnowledgeSource:
    source.status = "disabled"
    active_run = await get_active_run(session, source.id)
    if active_run:
        active_run.status = "failed"
        active_run.error_code = "source_disabled"
        active_run.error_message = "Source disabled while ingestion was processing"
        active_run.completed_at = _now()
    await session.execute(update(KnowledgeDocument).where(KnowledgeDocument.source_id == source.id).values(is_active=False))
    await session.execute(update(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id).values(is_active=False))
    await session.commit()
    return await source_with_counts(session, source)


async def get_source_for_request(session: AsyncSession, organization_id: UUID, company_id: UUID, source_id: UUID) -> KnowledgeSource:
    source = await get_source(session, organization_id, company_id, source_id)
    if source is None:
        raise KnowledgeError("source_not_found", "Knowledge source not found")
    return await source_with_counts(session, source)


async def list_knowledge_sources(session: AsyncSession, organization_id: UUID, company_id: UUID) -> list[KnowledgeSource]:
    sources = await list_sources(session, organization_id, company_id)
    for source in sources:
        await source_with_counts(session, source)
    return sources


async def list_knowledge_documents(session: AsyncSession, organization_id: UUID, company_id: UUID, source_id: UUID, page: int, page_size: int):
    return await list_documents(session, organization_id, company_id, source_id, page, page_size)


async def list_knowledge_chunks(session: AsyncSession, organization_id: UUID, company_id: UUID, document_id: UUID, page: int, page_size: int):
    return await list_chunks(session, organization_id, company_id, document_id, page, page_size)
