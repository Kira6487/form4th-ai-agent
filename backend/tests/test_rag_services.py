from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.models.knowledge import KnowledgeChunk
from app.services.embedding_index_service import embedding_is_current
from app.services.rag.context_builder import build_rag_context
from app.services.rag.retrieval_service import RetrievedChunk, build_retrieval_statement


def test_reuse_requires_hash_model_dimensions_and_ready_status() -> None:
    chunk = KnowledgeChunk(content_hash="same", embedding_status="ready", embedding_model="gemini-embedding-2", embedding_dimensions=768, content="x")
    assert embedding_is_current(chunk, "same", "gemini-embedding-2", 768)
    assert not embedding_is_current(chunk, "changed", "gemini-embedding-2", 768)
    assert not embedding_is_current(chunk, "same", "other-model", 768)
    chunk.embedding_status = "pending"
    assert not embedding_is_current(chunk, "same", "gemini-embedding-2", 768)


def test_retrieval_statement_has_tenant_active_and_threshold_filters() -> None:
    organization_id, company_id = uuid4(), uuid4()
    statement = build_retrieval_statement(organization_id, company_id, [0.0] * 768, 5, 0.55)
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "knowledge_chunks.organization_id" in sql
    assert "knowledge_chunks.company_id" in sql
    assert "knowledge_chunks.is_active" in sql
    assert "knowledge_chunks.embedding_status" in sql
    assert "knowledge_documents.is_active" in sql
    assert "knowledge_sources.status" in sql
    assert "<=>" in sql
    assert "LIMIT" in sql


def test_context_preserves_source_document_chunk_citations_without_vectors() -> None:
    item = RetrievedChunk(uuid4(), uuid4(), uuid4(), "Returns", "Refunds are allowed.", 0.91, "https://example.test/returns", {"title": "Returns"})
    context = build_rag_context([item])
    assert "source_id=" in context and "document_id=" in context and "chunk_id=" in context
    assert "https://example.test/returns" in context
    assert "Refunds are allowed." in context
    assert "0.91" not in context
