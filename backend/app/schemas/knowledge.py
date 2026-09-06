from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, AliasChoices, BaseModel, ConfigDict, Field, field_validator


KnowledgeType = Literal["website", "manual", "pdf"]
KnowledgeStatus = Literal["pending", "processing", "ready", "failed", "disabled"]


class ManualSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    title: str = Field(min_length=2, max_length=500)
    content: str = Field(min_length=1, max_length=2_000_000)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name", "title", "content")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        return value


class WebsiteSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    source_url: AnyHttpUrl

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be empty")
        return value


class KnowledgeSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    company_id: UUID
    type: KnowledgeType = Field(validation_alias=AliasChoices("source_type", "type"))
    name: str
    description: str | None
    source_url: str | None
    storage_path: str | None
    status: KnowledgeStatus
    last_error: str | None
    last_indexed_at: datetime | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    documents_count: int = 0
    chunks_count: int = 0


class KnowledgeIngestionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    status: str
    provider: str | None
    external_job_id: str | None
    documents_processed: int
    chunks_created: int
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class KnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    ingestion_run_id: UUID | None
    title: str
    content: str
    content_type: str
    language: str | None
    source_url: str | None
    content_hash: str
    metadata: dict[str, Any] = Field(validation_alias=AliasChoices("document_metadata", "metadata"))
    is_active: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    document_id: UUID
    ingestion_run_id: UUID | None
    chunk_index: int
    content: str
    content_hash: str
    approx_token_count: int | None
    metadata: dict[str, Any] = Field(validation_alias=AliasChoices("chunk_metadata", "metadata"))
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PaginatedDocuments(BaseModel):
    items: list[KnowledgeDocumentRead]
    page: int
    page_size: int
    total: int


class PaginatedChunks(BaseModel):
    items: list[KnowledgeChunkRead]
    page: int
    page_size: int
    total: int


class KnowledgeStatusRead(BaseModel):
    source: KnowledgeSourceRead
    run: KnowledgeIngestionRunRead | None = None
