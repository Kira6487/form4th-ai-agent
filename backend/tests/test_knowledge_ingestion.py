import asyncio
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import select

from app.core.auth import get_current_user
from app.main import app
from app.models import Company, KnowledgeChunk, KnowledgeDocument, KnowledgeSource, Organization, OrganizationMember
from app.schemas.auth import AuthenticatedUser
from app.core.config import Settings
from app.services.ingestion.firecrawl_provider import WebCrawlerProvider
from app.services.knowledge_service import _extract_pdf_text, create_website_source, poll_website_source, reindex_source, source_with_counts
from app.services.ingestion.chunker import chunk_content
from app.services.ingestion.hashing import content_hash
from app.services.ingestion.normalizer import normalize_content
from app.services.ingestion.pdf_validation import validate_pdf_bytes
from app.services.ingestion.url_validation import validate_website_url


def seed_knowledge_tenants(session_factory):
    user_a = AuthenticatedUser(id=uuid4(), email="knowledge-a@example.com")
    user_b = AuthenticatedUser(id=uuid4(), email="knowledge-b@example.com")
    org_a = Organization(name="Knowledge A", slug=f"knowledge-a-{uuid4().hex[:8]}")
    org_b = Organization(name="Knowledge B", slug=f"knowledge-b-{uuid4().hex[:8]}")

    async def seed():
        async with session_factory() as session:
            session.add_all([org_a, org_b])
            await session.flush()
            session.add_all([
                OrganizationMember(organization_id=org_a.id, user_id=user_a.id, role="owner"),
                OrganizationMember(organization_id=org_b.id, user_id=user_b.id, role="owner"),
                Company(organization_id=org_a.id, name="Knowledge Company A"),
                Company(organization_id=org_b.id, name="Knowledge Company B"),
            ])
            await session.commit()

    asyncio.run(seed())

    async def find_companies():
        async with session_factory() as session:
            companies = list((await session.scalars(select(Company).order_by(Company.name))).all())
            return companies

    companies = asyncio.run(find_companies())
    return user_a, user_b, org_a, org_b, companies[0], companies[1]


def test_normalizer_hash_and_semantic_chunking() -> None:
    normalized = normalize_content("# Heading\r\n\r\n\r\nParagraph   one.\r\n\r\n- item\r\n")
    assert normalized == "# Heading\n\nParagraph one.\n\n- item"
    assert content_hash(normalized) == content_hash(normalized)
    chunks = chunk_content("# Heading\n\n" + "Sentence one. " * 80, target_tokens=60, overlap_tokens=10)
    assert len(chunks) > 1
    assert all(piece.content and piece.approx_token_count > 0 for piece in chunks)
    assert all("chunk_index" in piece.metadata for piece in chunks)


@pytest.mark.parametrize("value", ["file:///tmp/a", "http://localhost/a", "http://127.0.0.1/a", "ftp://example.com"])
def test_website_url_rejects_unsafe_destinations(value: str) -> None:
    with pytest.raises(ValueError):
        validate_website_url(value)


def test_pdf_validation_checks_magic_mime_and_size() -> None:
    assert validate_pdf_bytes("../safe.pdf", "application/pdf", b"%PDF-1.7 body", 100) == "safe.pdf"
    with pytest.raises(ValueError):
        validate_pdf_bytes("file.pdf", "text/plain", b"%PDF-1.7 body", 100)
    with pytest.raises(ValueError):
        validate_pdf_bytes("file.pdf", "application/pdf", b"not a pdf", 100)
    with pytest.raises(ValueError):
        validate_pdf_bytes("file.pdf", "application/pdf", b"%PDF-1.7 body", 5)


def test_pypdf_extracts_text_and_empty_pdf_is_detectable() -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 200 Td (Hello PDF) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    assert _extract_pdf_text(buffer.getvalue()) == "Hello PDF"

    empty = PdfWriter()
    empty.add_blank_page(width=300, height=300)
    empty_buffer = BytesIO()
    empty.write(empty_buffer)
    assert _extract_pdf_text(empty_buffer.getvalue()) == ""


def test_manual_source_is_tenant_scoped_and_reindex_preserves_previous(tenant_client, monkeypatch) -> None:
    client, session_factory = tenant_client
    user_a, user_b, org_a, org_b, company_a, company_b = seed_knowledge_tenants(session_factory)
    app.dependency_overrides[get_current_user] = lambda: user_a

    created = client.post(
        f"/api/v1/organizations/{org_a.id}/companies/{company_a.id}/knowledge/sources/manual",
        json={"name": "Product guide", "title": "Guide", "content": "Version one content."},
    )
    assert created.status_code == 201, created.text
    source_id = created.json()["id"]
    assert created.json()["status"] == "ready"
    assert created.json()["documents_count"] == 1
    assert created.json()["chunks_count"] == 1

    own_docs = client.get(f"/api/v1/organizations/{org_a.id}/companies/{company_a.id}/knowledge/sources/{source_id}/documents")
    assert own_docs.status_code == 200
    assert own_docs.json()["items"][0]["content"] == "Version one content."

    cross_tenant = client.get(f"/api/v1/organizations/{org_b.id}/companies/{company_b.id}/knowledge/sources/{source_id}")
    assert cross_tenant.status_code == 403

    other_user = lambda: user_b
    app.dependency_overrides[get_current_user] = other_user
    assert client.get(f"/api/v1/organizations/{org_a.id}/companies/{company_a.id}/knowledge/sources/{source_id}/documents").status_code == 403

    app.dependency_overrides[get_current_user] = lambda: user_a
    disabled = client.post(f"/api/v1/organizations/{org_a.id}/companies/{company_a.id}/knowledge/sources/{source_id}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"

    async def verify_inactive():
        async with session_factory() as session:
            source_uuid = UUID(source_id)
            source = await session.get(KnowledgeSource, source_uuid)
            documents = list((await session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source_id == source_uuid))).all())
            chunks = list((await session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_uuid))).all())
            return source.status, [doc.is_active for doc in documents], [chunk.is_active for chunk in chunks]

    assert asyncio.run(verify_inactive()) == ("disabled", [False], [False])


class FakeCrawler(WebCrawlerProvider):
    def __init__(self):
        self.job_id = "fake-job-1"

    async def start_crawl(self, url: str, max_pages: int) -> str:
        assert url == "https://example.com"
        assert max_pages == 3
        return self.job_id

    async def get_crawl_status(self, external_job_id: str) -> dict:
        assert external_job_id == self.job_id
        return {"status": "completed", "data": [{"markdown": "# Home\n\nWelcome.", "metadata": {"title": "Home", "sourceURL": "https://example.com"}}]}


def test_website_provider_flow_is_async_and_persists_markdown(tenant_client) -> None:
    _, session_factory = tenant_client
    user_a, _, org_a, _, company_a, _ = seed_knowledge_tenants(session_factory)
    crawler = FakeCrawler()

    async def run():
        async with session_factory() as session:
            settings = Settings(firecrawl_api_key="test", firecrawl_max_pages=3)
            source = await create_website_source(session, org_a.id, company_a.id, user_a.id, "Example", "https://example.com", settings=settings, provider=crawler)
            assert source.status == "processing"
            run_state = await poll_website_source(session, source, settings, crawler)
            await source_with_counts(session, source)
            return source, run_state

    source, run_state = asyncio.run(run())
    assert run_state.status == "completed"
    assert source.status == "ready"
    assert source.documents_count == 1
    assert source.chunks_count == 1


def test_failed_reindex_keeps_previous_active_version(tenant_client, monkeypatch) -> None:
    _, session_factory = tenant_client
    user_a, _, org_a, _, company_a, _ = seed_knowledge_tenants(session_factory)
    app.dependency_overrides[get_current_user] = lambda: user_a
    client = tenant_client[0]
    created = client.post(f"/api/v1/organizations/{org_a.id}/companies/{company_a.id}/knowledge/sources/manual", json={"name": "Guide", "title": "V1", "content": "Good version"})
    source_id = created.json()["id"]

    async def fail_activation(*args, **kwargs):
        from app.services.knowledge_service import KnowledgeError
        raise KnowledgeError("reindex_failed", "simulated processing failure")

    monkeypatch.setattr("app.services.knowledge_service._activate_content", fail_activation)
    response = client.post(f"/api/v1/organizations/{org_a.id}/companies/{company_a.id}/knowledge/sources/{source_id}/reindex")
    assert response.status_code == 422

    async def verify():
        async with session_factory() as session:
            docs = list((await session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source_id == UUID(source_id)))).all())
            source = await session.get(KnowledgeSource, UUID(source_id))
            return source.status, [(doc.content, doc.is_active) for doc in docs]

    assert asyncio.run(verify()) == ("failed", [("Good version", True)])
