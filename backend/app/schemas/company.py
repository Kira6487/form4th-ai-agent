from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    legal_name: str | None = Field(default=None, max_length=200)
    website: AnyHttpUrl | None = None
    description: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=80)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("name must contain at least two non-space characters")
        return normalized


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    legal_name: str | None = Field(default=None, max_length=200)
    website: AnyHttpUrl | None = None
    description: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, pattern="^(active|inactive|archived)$")

    @field_validator("name")
    @classmethod
    def normalize_update_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("name must contain at least two non-space characters")
        return normalized


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    legal_name: str | None
    website: str | None
    description: str | None
    industry: str | None
    country: str | None
    timezone: str | None
    status: str
    created_at: datetime
    updated_at: datetime
