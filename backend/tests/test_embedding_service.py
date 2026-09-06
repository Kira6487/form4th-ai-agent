from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.services.ai.embedding_service import EmbeddingDimensionError, EmbeddingProviderError, GeminiEmbeddingService, format_document_for_embedding, format_query_for_embedding


class FakeEmbeddingModels:
    def __init__(self, dimensions: int = 768, failures: int = 0) -> None:
        self.dimensions = dimensions
        self.failures = failures
        self.calls: list[dict] = []

    async def embed_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.failures:
            self.failures -= 1
            raise RuntimeError("429 rate limit")
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.01] * self.dimensions) for _ in kwargs["contents"]])


class FakeClient:
    def __init__(self, models: FakeEmbeddingModels) -> None:
        self.aio = SimpleNamespace(models=models)


def settings() -> Settings:
    return Settings(_env_file=None, gemini_api_key="test-key", gemini_embedding_model="gemini-embedding-2", gemini_embedding_dimensions=768)


@pytest.mark.asyncio
async def test_embedding_formatting_and_explicit_dimensions() -> None:
    models = FakeEmbeddingModels()
    service = GeminiEmbeddingService(settings(), FakeClient(models), sleep=lambda _: _noop(), random_fn=lambda: 0)
    vectors = await service.embed_documents([("Policy", "Refunds are allowed."), (None, "Opening hours")])
    assert format_document_for_embedding("Policy", "Refunds are allowed.") == "title: Policy | text: Refunds are allowed."
    assert format_query_for_embedding("refund") == "task: search result | query: refund"
    assert len(vectors) == 2 and len(vectors[0]) == 768
    assert models.calls[0]["model"] == "gemini-embedding-2"
    assert models.calls[0]["config"].output_dimensionality == 768
    assert models.calls[0]["contents"][0] == "title: Policy | text: Refunds are allowed."


@pytest.mark.asyncio
async def test_query_uses_same_batch_adapter_and_retries_transient_error() -> None:
    models = FakeEmbeddingModels(failures=1)
    sleeps: list[float] = []

    async def no_sleep(value: float) -> None:
        sleeps.append(value)

    service = GeminiEmbeddingService(settings(), FakeClient(models), sleep=no_sleep, random_fn=lambda: 0)
    vector = await service.embed_query("What is the refund policy?")
    assert len(vector) == 768
    assert len(models.calls) == 2
    assert sleeps == [0.5]


@pytest.mark.asyncio
async def test_embedding_dimensions_are_rejected_and_non_transient_errors_are_not_retried() -> None:
    service = GeminiEmbeddingService(settings(), FakeClient(FakeEmbeddingModels(dimensions=3)), sleep=lambda _: _noop())
    with pytest.raises(EmbeddingDimensionError):
        await service.embed_query("test")

    class InvalidModels:
        calls = 0

        async def embed_content(self, **kwargs):
            self.calls += 1
            raise RuntimeError("400 invalid argument")

    invalid = InvalidModels()
    service = GeminiEmbeddingService(settings(), FakeClient(invalid), sleep=lambda _: _noop())
    with pytest.raises(EmbeddingProviderError):
        await service.embed_query("test")
    assert invalid.calls == 1


async def _noop() -> None:
    return None
