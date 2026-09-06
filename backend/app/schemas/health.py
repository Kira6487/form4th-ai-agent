from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str


class AIHealthResponse(BaseModel):
    status: str
    provider: str
    model: str
