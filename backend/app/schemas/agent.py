from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.lead import LeadSignal

AgentStatus = Literal["draft", "active", "disabled"]


class AIAgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    role: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    objective: str = Field(min_length=2, max_length=1000)
    tone: str = Field(min_length=2, max_length=120)
    language: str = Field(min_length=2, max_length=80)
    system_instructions: str = Field(min_length=1, max_length=12000)
    model: str | None = Field(default=None, max_length=120)
    status: AgentStatus = "draft"
    temperature: float | None = Field(default=None, ge=0, le=1)
    max_output_tokens: int | None = Field(default=None, ge=1, le=10000)

    @field_validator("name", "role", "objective", "tone", "language", "system_instructions")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        return value


class AIAgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    role: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    objective: str | None = Field(default=None, min_length=2, max_length=1000)
    tone: str | None = Field(default=None, min_length=2, max_length=120)
    language: str | None = Field(default=None, min_length=2, max_length=80)
    system_instructions: str | None = Field(default=None, min_length=1, max_length=12000)
    model: str | None = Field(default=None, max_length=120)
    status: AgentStatus | None = None
    temperature: float | None = Field(default=None, ge=0, le=1)
    max_output_tokens: int | None = Field(default=None, ge=1, le=10000)


class AIAgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    company_id: UUID
    name: str
    role: str
    description: str | None
    objective: str
    tone: str
    language: str
    system_instructions: str
    model: str
    status: AgentStatus
    temperature: float | None
    max_output_tokens: int | None
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    channel: str = Field(default="dashboard", min_length=2, max_length=40)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    company_id: UUID
    agent_id: UUID
    created_by: UUID | None
    channel: str
    status: Literal["active", "closed"]
    started_at: datetime
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    retrieved_chunk_ids: list[str] | None
    sources: list[dict[str, Any]] | None
    provider: str | None
    model: str | None
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    status: Literal["completed", "failed"]
    created_at: datetime


class ChatMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be empty")
        return value


class ChatSource(BaseModel):
    title: str
    url: str | None = None
    chunk_id: UUID
    source_id: UUID
    document_id: UUID


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    sources: list[ChatSource]
    model: str | None
    lead: LeadSignal | None = None
