from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import OrganizationContext, require_organization_member, require_organization_role
from app.core.config import get_settings
from app.db.session import get_db_session
from app.repositories.knowledge_repository import get_latest_run
from app.schemas.knowledge import (
    KnowledgeChunkRead,
    KnowledgeDocumentRead,
    KnowledgeIngestionRunRead,
    KnowledgeSourceRead,
    KnowledgeStatusRead,
    KnowledgeSearchRequest, KnowledgeSearchResponse, KnowledgeSearchResult, RagPreviewResponse,
    EmbeddingIndexRequest, EmbeddingIndexResponse, EmbeddingReindexRequest,
    ManualSourceCreate,
    PaginatedChunks,
    PaginatedDocuments,
    WebsiteSourceCreate,
)
from app.services.knowledge_service import (
    KnowledgeError,
    create_manual_source,
    create_pdf_source,
    create_website_source,
    disable_source,
    get_source_for_request,
    company_for_source,
    list_knowledge_chunks,
    list_knowledge_documents,
    list_knowledge_sources,
    poll_website_source,
    reindex_source,
)
from app.services.ai.embedding_service import EmbeddingConfigurationError, EmbeddingProviderError
from app.services.embedding_index_service import index_pending_embeddings, reset_source_embeddings
from app.services.rag.context_builder import build_rag_context
from app.services.rag.retrieval_service import VectorDatabaseRequiredError, search_knowledge

router = APIRouter(prefix="/organizations/{organization_id}/companies/{company_id}/knowledge", tags=["knowledge"])


def _error(exc: KnowledgeError) -> HTTPException:
    code = 404 if exc.code in {"company_not_found", "source_not_found"} else 409 if exc.code == "source_already_processing" else 503 if exc.code in {"crawler_unavailable", "storage_unavailable"} else 422
    return HTTPException(status_code=code, detail=str(exc))


def _source_read(source) -> KnowledgeSourceRead:
    return KnowledgeSourceRead.model_validate({
        "id": source.id, "organization_id": source.organization_id, "company_id": source.company_id,
        "type": source.source_type, "name": source.name, "description": source.description, "source_url": source.source_url,
        "storage_path": source.storage_path, "status": source.status, "last_error": source.last_error,
        "last_indexed_at": source.last_indexed_at, "created_by": source.created_by,
        "created_at": source.created_at, "updated_at": source.updated_at,
        "documents_count": getattr(source, "documents_count", 0), "chunks_count": getattr(source, "chunks_count", 0),
        "embedded_chunks_count": getattr(source, "embedded_chunks_count", 0),
        "pending_embeddings_count": getattr(source, "pending_embeddings_count", 0),
        "failed_embeddings_count": getattr(source, "failed_embeddings_count", 0),
    })


async def _source(context: OrganizationContext, session: AsyncSession, company_id: UUID, source_id: UUID):
    try:
        return await get_source_for_request(session, context.organization.id, company_id, source_id)
    except KnowledgeError as exc:
        raise _error(exc) from exc


@router.get("/sources", response_model=list[KnowledgeSourceRead])
async def list_sources(
    company_id: UUID,
    context: OrganizationContext = Depends(require_organization_member()),
    session: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeSourceRead]:
    try:
        if await company_for_source(session, context.organization.id, company_id) is None:
            raise KnowledgeError("company_not_found", "Company not found")
        items = await list_knowledge_sources(session, context.organization.id, company_id)
    except KnowledgeError as exc:
        raise _error(exc) from exc
    return [_source_read(item) for item in items]


@router.get("/sources/{source_id}", response_model=KnowledgeSourceRead)
async def get_one(source_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> KnowledgeSourceRead:
    return _source_read(await _source(context, session, company_id, source_id))


@router.post("/sources/manual", response_model=KnowledgeSourceRead, status_code=status.HTTP_201_CREATED)
async def create_manual(data: ManualSourceCreate, company_id: UUID, context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> KnowledgeSourceRead:
    try:
        source = await create_manual_source(session, context.organization.id, company_id, context.user.id, data.name, data.title, data.content, data.description)
    except KnowledgeError as exc:
        raise _error(exc) from exc
    return _source_read(source)


@router.post("/sources/website", response_model=KnowledgeSourceRead, status_code=status.HTTP_201_CREATED)
async def create_website(data: WebsiteSourceCreate, company_id: UUID, context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> KnowledgeSourceRead:
    try:
        source = await create_website_source(session, context.organization.id, company_id, context.user.id, data.name, str(data.source_url), data.description)
    except KnowledgeError as exc:
        raise _error(exc) from exc
    return _source_read(source)


@router.post("/sources/pdf", response_model=KnowledgeSourceRead, status_code=status.HTTP_201_CREATED)
async def create_pdf(name: str = Form(min_length=2, max_length=200), description: str | None = Form(default=None, max_length=1000), company_id: UUID = ..., file: UploadFile = File(...), context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> KnowledgeSourceRead:
    data = await file.read((get_settings().max_pdf_size_mb * 1024 * 1024) + 1)
    try:
        source = await create_pdf_source(session, context.organization.id, company_id, context.user.id, name, file.filename, file.content_type, data, description)
    except KnowledgeError as exc:
        raise _error(exc) from exc
    return _source_read(source)


@router.post("/sources/{source_id}/reindex", response_model=KnowledgeSourceRead)
async def reindex(source_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> KnowledgeSourceRead:
    source = await _source(context, session, company_id, source_id)
    try:
        result = await reindex_source(session, source, context.user.id)
    except KnowledgeError as exc:
        raise _error(exc) from exc
    return _source_read(result)


@router.post("/sources/{source_id}/disable", response_model=KnowledgeSourceRead)
async def disable(source_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> KnowledgeSourceRead:
    source = await _source(context, session, company_id, source_id)
    return _source_read(await disable_source(session, source))


@router.get("/sources/{source_id}/status", response_model=KnowledgeStatusRead)
async def status_check(source_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> KnowledgeStatusRead:
    source = await _source(context, session, company_id, source_id)
    if source.source_type == "website" and source.status == "processing":
        await poll_website_source(session, source)
        source = await _source(context, session, company_id, source_id)
    run = await get_latest_run(session, source.id)
    return KnowledgeStatusRead(source=_source_read(source), run=KnowledgeIngestionRunRead.model_validate(run) if run else None)


@router.get("/sources/{source_id}/documents", response_model=PaginatedDocuments)
async def documents(source_id: UUID, company_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> PaginatedDocuments:
    await _source(context, session, company_id, source_id)
    items, total = await list_knowledge_documents(session, context.organization.id, company_id, source_id, page, page_size)
    return PaginatedDocuments(items=[KnowledgeDocumentRead.model_validate(item) for item in items], page=page, page_size=page_size, total=total)


@router.get("/documents/{document_id}/chunks", response_model=PaginatedChunks)
async def chunks(document_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)) -> PaginatedChunks:
    items, total = await list_knowledge_chunks(session, context.organization.id, company_id, document_id, page, page_size)
    if not items and total == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return PaginatedChunks(items=[KnowledgeChunkRead.model_validate(item) for item in items], page=page, page_size=page_size, total=total)


def _retrieval_error(exc: Exception) -> HTTPException:
    if isinstance(exc, VectorDatabaseRequiredError):
        return HTTPException(status_code=503, detail="Semantic retrieval requires PostgreSQL with pgvector")
    if isinstance(exc, EmbeddingConfigurationError):
        return HTTPException(status_code=503, detail="Embedding service is not configured")
    if isinstance(exc, EmbeddingProviderError):
        return HTTPException(status_code=503, detail="Embedding service is temporarily unavailable")
    return HTTPException(status_code=503, detail="Knowledge search is temporarily unavailable")


def _search_result(item) -> KnowledgeSearchResult:
    return KnowledgeSearchResult(chunk_id=item.chunk_id, document_id=item.document_id, source_id=item.source_id, title=item.title, content=item.content, similarity=round(item.similarity, 6), source_url=item.source_url, metadata=item.metadata)


@router.post("/embeddings/index", response_model=EmbeddingIndexResponse)
async def index_embeddings(data: EmbeddingIndexRequest, company_id: UUID, context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> EmbeddingIndexResponse:
    if await company_for_source(session, context.organization.id, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if data.source_id:
        await _source(context, session, company_id, data.source_id)
    result = await index_pending_embeddings(session, context.organization.id, company_id, data.source_id, data.limit)
    return EmbeddingIndexResponse(total=result.total, processed=result.processed, embedded=result.embedded, pending=result.pending, failed=result.failed)


@router.post("/sources/{source_id}/embeddings/reindex", response_model=EmbeddingIndexResponse)
async def reindex_embeddings(source_id: UUID, data: EmbeddingReindexRequest, company_id: UUID, context: OrganizationContext = Depends(require_organization_role("owner", "admin")), session: AsyncSession = Depends(get_db_session)) -> EmbeddingIndexResponse:
    await _source(context, session, company_id, source_id)
    await reset_source_embeddings(session, context.organization.id, company_id, source_id, data.force)
    result = await index_pending_embeddings(session, context.organization.id, company_id, source_id, data.limit)
    return EmbeddingIndexResponse(total=result.total, processed=result.processed, embedded=result.embedded, pending=result.pending, failed=result.failed)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search(data: KnowledgeSearchRequest, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> KnowledgeSearchResponse:
    if await company_for_source(session, context.organization.id, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        items = await search_knowledge(session, context.organization.id, company_id, data.query, data.top_k, data.min_similarity)
    except Exception as exc:
        raise _retrieval_error(exc) from exc
    return KnowledgeSearchResponse(query=data.query, results=[_search_result(item) for item in items])


@router.post("/rag-preview", response_model=RagPreviewResponse)
async def rag_preview(data: KnowledgeSearchRequest, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> RagPreviewResponse:
    if await company_for_source(session, context.organization.id, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        items = await search_knowledge(session, context.organization.id, company_id, data.query, data.top_k, data.min_similarity)
    except Exception as exc:
        raise _retrieval_error(exc) from exc
    citations = [_search_result(item) for item in items]
    return RagPreviewResponse(query=data.query, context=build_rag_context(items), citations=citations)
