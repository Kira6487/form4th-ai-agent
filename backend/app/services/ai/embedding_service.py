import asyncio
import random
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from app.core.config import Settings, get_settings


class EmbeddingConfigurationError(RuntimeError):
    """Raised when the server cannot call the configured embedding provider."""


class EmbeddingProviderError(RuntimeError):
    """Raised when the embedding provider returns an error."""


class EmbeddingDimensionError(EmbeddingProviderError):
    """Raised when Gemini returns vectors with an unexpected dimension."""


def format_document_for_embedding(title: str | None, content: str) -> str:
    return f"title: {title or ''} | text: {content}"


def format_query_for_embedding(query: str) -> str:
    return f"task: search result | query: {query}"


class GeminiEmbeddingService:
    """Central Gemini embedding adapter; generation remains in GeminiService."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: Any | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        random_fn: Callable[[], float] = random.random,
        max_attempts: int = 3,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client
        self._sleep = sleep
        self._random = random_fn
        self.max_attempts = max(1, max_attempts)

    @property
    def model(self) -> str:
        return self.settings.gemini_embedding_model

    @property
    def dimensions(self) -> int:
        return self.settings.gemini_embedding_dimensions

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.settings.gemini_api_key:
            raise EmbeddingConfigurationError("GEMINI_API_KEY is not configured")
        from google import genai

        self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError)):
            return True
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        if status in {408, 429, 500, 502, 503, 504}:
            return True
        message = str(exc).lower()
        return any(token in message for token in ("429", "rate limit", "timeout", "timed out", " 500", " 502", " 503", " 504"))

    async def _embed(self, contents: Sequence[str]) -> list[list[float]]:
        if not contents:
            return []
        client = self._get_client()
        try:
            from google.genai import types

            config = types.EmbedContentConfig(output_dimensionality=self.dimensions)
        except ImportError as exc:
            raise EmbeddingProviderError("google-genai does not expose embedding configuration") from exc

        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                response = await client.aio.models.embed_content(model=self.model, contents=list(contents), config=config)
                raw_embeddings = getattr(response, "embeddings", None) or []
                vectors = [list(getattr(item, "values", item)) for item in raw_embeddings]
                if len(vectors) != len(contents):
                    raise EmbeddingProviderError("Gemini returned an unexpected number of embeddings")
                for vector in vectors:
                    if len(vector) != self.dimensions:
                        raise EmbeddingDimensionError(f"Expected {self.dimensions} embedding dimensions")
                return [[float(value) for value in vector] for vector in vectors]
            except EmbeddingDimensionError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= self.max_attempts or not self._is_transient(exc):
                    raise EmbeddingProviderError("Gemini embedding request failed") from exc
                delay = min(8.0, 0.5 * (2**attempt)) + self._random() * 0.25
                await self._sleep(delay)
        raise EmbeddingProviderError("Gemini embedding request failed") from last_error

    async def embed_documents(self, documents: Sequence[tuple[str | None, str]]) -> list[list[float]]:
        contents = [format_document_for_embedding(title, content) for title, content in documents]
        return await self._embed(contents)

    async def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            raise ValueError("query must not be empty")
        vectors = await self._embed([format_query_for_embedding(query.strip())])
        return vectors[0]
