from typing import Any

from app.core.config import Settings, get_settings


class GeminiConfigurationError(RuntimeError):
    """Raised when Gemini cannot run because server configuration is missing."""


class GeminiServiceError(RuntimeError):
    """Raised when the Gemini provider fails or returns no text."""


class GeminiService:
    """Central adapter for Google Gemini, isolated from API and domain code."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    @property
    def model(self) -> str:
        return self.settings.gemini_model

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.settings.gemini_api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY is not configured")

        from google import genai

        self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    async def generate_text(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        client = self._get_client()
        try:
            response = await client.aio.models.generate_content(model=self.model, contents=prompt)
        except Exception as exc:
            raise GeminiServiceError("Gemini request failed") from exc

        generated_text = getattr(response, "text", None)
        if not generated_text or not generated_text.strip():
            raise GeminiServiceError("Gemini returned an empty response")
        return generated_text.strip()

    async def health_check(self) -> None:
        await self.generate_text("Reply with OK only.")
