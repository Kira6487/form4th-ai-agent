import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.vector import Vector768

json_type = JSON().with_variant(JSONB(), "postgresql")


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        Index("ix_knowledge_sources_organization_id", "organization_id"),
        Index("ix_knowledge_sources_company_id", "company_id"),
        Index("ix_knowledge_sources_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[str] = mapped_column("type", String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    source_url: Mapped[str | None] = mapped_column(String(2000))
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    last_error: Mapped[str | None] = mapped_column(Text)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="knowledge_sources")
    company = relationship("Company", back_populates="knowledge_sources")
    ingestion_runs = relationship("KnowledgeIngestionRun", back_populates="source", cascade="all, delete-orphan")
    documents = relationship("KnowledgeDocument", back_populates="source", cascade="all, delete-orphan")
    chunks = relationship("KnowledgeChunk", back_populates="source", cascade="all, delete-orphan")


class KnowledgeIngestionRun(Base):
    __tablename__ = "knowledge_ingestion_runs"
    __table_args__ = (
        Index("ix_knowledge_ingestion_runs_organization_id", "organization_id"),
        Index("ix_knowledge_ingestion_runs_company_id", "company_id"),
        Index("ix_knowledge_ingestion_runs_source_id", "source_id"),
        Index("ix_knowledge_ingestion_runs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    provider: Mapped[str | None] = mapped_column(String(80))
    external_job_id: Mapped[str | None] = mapped_column(String(200))
    documents_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source = relationship("KnowledgeSource", back_populates="ingestion_runs")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index("ix_knowledge_documents_organization_id", "organization_id"),
        Index("ix_knowledge_documents_company_id", "company_id"),
        Index("ix_knowledge_documents_source_id", "source_id"),
        Index("ix_knowledge_documents_content_hash", "content_hash"),
        Index("ix_knowledge_documents_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge_ingestion_runs.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False, default="text/markdown")
    language: Mapped[str | None] = mapped_column(String(20))
    source_url: Mapped[str | None] = mapped_column(String(2000))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    document_metadata: Mapped[dict] = mapped_column("metadata", json_type, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    source = relationship("KnowledgeSource", back_populates="documents")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_knowledge_chunks_organization_id", "organization_id"),
        Index("ix_knowledge_chunks_company_id", "company_id"),
        Index("ix_knowledge_chunks_source_id", "source_id"),
        Index("ix_knowledge_chunks_document_id", "document_id"),
        Index("ix_knowledge_chunks_content_hash", "content_hash"),
        Index("ix_knowledge_chunks_is_active", "is_active"),
        Index("ix_knowledge_chunks_embedding_status", "embedding_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge_ingestion_runs.id", ondelete="SET NULL"))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    approx_token_count: Mapped[int | None] = mapped_column(Integer)
    chunk_metadata: Mapped[dict] = mapped_column("metadata", json_type, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector768(768), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    source = relationship("KnowledgeSource", back_populates="chunks")
    document = relationship("KnowledgeDocument", back_populates="chunks")
