from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

LeadIntent = Literal[
    "general_inquiry",
    "purchase_interest",
    "request_quote",
    "request_demo",
    "contact_request",
    "appointment_interest",
    "other_commercial",
]
LeadStatus = Literal["new", "qualified", "contacted", "converted", "lost"]
LeadSource = Literal["dashboard_test", "widget", "whatsapp", "email", "api"]


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    digits = "".join(character for character in raw if character.isdigit())
    if not 7 <= len(digits) <= 15:
        raise ValueError("phone must contain between 7 and 15 digits")
    return ("+" if raw.startswith("+") else "") + digits


class LeadAssessment(BaseModel):
    has_commercial_intent: bool
    intent: LeadIntent
    confidence: float = Field(ge=0, le=1)
    interest: str | None = Field(default=None, max_length=1000)
    name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    consent_to_contact: bool
    missing_fields: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("interest", "name")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        return _normalize_phone(value)


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    company_id: UUID
    agent_id: UUID | None
    conversation_id: UUID
    name: str | None
    email: EmailStr | None
    phone: str | None
    interest: str | None
    intent: LeadIntent
    confidence: float
    status: LeadStatus
    source: LeadSource
    consent_to_contact: bool
    detected_at: datetime
    qualified_at: datetime | None
    last_user_message_id: UUID | None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="lead_metadata", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime


class LeadUpdate(BaseModel):
    status: LeadStatus | None = None
    name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    interest: str | None = Field(default=None, max_length=1000)
    consent_to_contact: bool | None = None

    @field_validator("name", "interest")
    @classmethod
    def strip_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_update_phone(cls, value: str | None) -> str | None:
        return _normalize_phone(value)


class LeadPage(BaseModel):
    items: list[LeadRead]
    page: int
    page_size: int
    total: int


class LeadSignal(BaseModel):
    id: UUID
    status: LeadStatus
