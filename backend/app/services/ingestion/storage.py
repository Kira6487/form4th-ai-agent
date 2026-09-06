from typing import Protocol
from uuid import UUID

import httpx

from app.core.config import Settings


class StorageError(RuntimeError):
    pass


class PrivateFileStorage(Protocol):
    async def upload_pdf(self, path: str, data: bytes) -> None: ...
    async def download(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> None: ...


class SupabaseStorage:
    def __init__(self, settings: Settings):
        secret_key = settings.supabase_secret_key or settings.supabase_service_role_key
        if not secret_key:
            raise StorageError("Supabase Storage is not configured")
        self.base_url = settings.supabase_url.rstrip("/")
        self.bucket = settings.supabase_storage_bucket
        self.headers = {
            "Authorization": f"Bearer {secret_key}",
            "apikey": secret_key,
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

    async def download(self, path: str) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/storage/v1/object/{self.bucket}/{path}",
                headers=self.headers,
            )
            if response.status_code != 200:
                raise StorageError("Unable to read PDF from private storage")
            return response.content


def storage_path(organization_id: UUID, company_id: UUID, source_id: UUID, object_id: UUID) -> str:
    return f"organizations/{organization_id}/companies/{company_id}/sources/{source_id}/{object_id}.pdf"
