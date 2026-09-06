from uuid import UUID

from pydantic import BaseModel, EmailStr


class AuthenticatedUser(BaseModel):
    id: UUID
    email: EmailStr | None = None
    role: str | None = None


class MeResponse(AuthenticatedUser):
    pass
