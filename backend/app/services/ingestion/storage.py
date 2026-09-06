from typing import Protocol
from uuid import UUID

import httpx

from app.core.config import Settings


class StorageError(RuntimeError):
    pass


class PrivateFileStorage(Protocol):
    async def upload_pdf(self, path: str, data: bytes) -> None: ...
    async def delete(self, path: str) -> None: ...


class SupabaseStorage:
    def __init__(self, settings: Settings):
        if not settings.supabase_service_role_key:
            raise StorageError("Supabase Storage is not configured")
        self.base_url = settings.supabase_url.rstrip("/")
        self.bucket = settings.supabase_storage_bucket
        self.headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        }

    async def _ensure_private_bucket(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            f"{self.base_url}/storage/v1/bucket",
            headers=self.headers,
            json={"id": self.bucket, "name": self.bucket, "public": False},
        )
        if response.status_code not in {200, 201, 400, 409}:
            raise StorageError("Unable to initialize private storage bucket")

    async def upload_pdf(self, path: str, data: bytes) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            await self._ensure_private_bucket(client)
            response = await client.post(
                f"{self.base_url}/storage/v1/object/{self.bucket}/{path}",
                headers={**self.headers, "Content-Type": "application/pdf", "x-upsert": "false"},
                content=data,
            )
            if response.status_code not in {200, 201}:
                raise StorageError("Unable to upload PDF to private storage")

    async def delete(self, path: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self.base_url}/storage/v1/object/{self.bucket}/{path}",
                headers=self.headers,
            )
            if response.status_code not in {200, 204, 404}:
                raise StorageError("Unable to clean up stored PDF")


def storage_path(organization_id: UUID, company_id: UUID, source_id: UUID, object_id: UUID) -> str:
    return f"organizations/{organization_id}/companies/{company_id}/sources/{source_id}/{object_id}.pdf"
