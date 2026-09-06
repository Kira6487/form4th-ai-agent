import pytest

from app.core.config import Settings
from app.services.ai.gemini_service import GeminiConfigurationError, GeminiService


class FakeResponse:
    text = " OK "


class FakeModels:
    async def generate_content(self, *, model: str, contents: str) -> FakeResponse:
        assert model == "test-model"
        assert contents == "Reply with OK only."
        return FakeResponse()


class FakeAio:
    models = FakeModels()


class FakeClient:
    aio = FakeAio()


@pytest.mark.asyncio
async def test_gemini_service_uses_centralized_model_and_client() -> None:
    settings = Settings(_env_file=None, gemini_api_key="test-key", gemini_model="test-model")
    service = GeminiService(settings=settings, client=FakeClient())

    assert await service.generate_text("Reply with OK only.") == "OK"


@pytest.mark.asyncio
async def test_gemini_service_requires_server_key() -> None:
    service = GeminiService(Settings(_env_file=None))

    with pytest.raises(GeminiConfigurationError):
        await service.generate_text("test")
