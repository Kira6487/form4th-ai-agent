import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings


class ConversationProviderError(RuntimeError):
    """Raised when Gemini cannot produce a user-visible answer."""


@dataclass(frozen=True)
class ProviderUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class GeneratedAnswer:
    text: str
    model: str
    latency_ms: int
    usage: ProviderUsage


class GeminiConversationService:
    """Gemini Interactions adapter. It exposes visible text only."""

    provider_name = "gemini"

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.settings.gemini_api_key:
            raise ConversationProviderError("GEMINI_API_KEY is not configured")
        from google import genai

        self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    @staticmethod
    def _usage(interaction: Any) -> ProviderUsage:
        usage = getattr(interaction, "usage", None) or getattr(interaction, "total_usage", None)
        if usage is None:
            return ProviderUsage()
        return ProviderUsage(
            input_tokens=getattr(usage, "total_input_tokens", None) or getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "total_output_tokens", None) or getattr(usage, "output_tokens", None),
        )

    @staticmethod
    def _text(interaction: Any) -> str:
        text = getattr(interaction, "output_text", None)
        if text:
            return str(text).strip()
        outputs = getattr(interaction, "outputs", None) or []
        visible: list[str] = []
        for output in outputs:
            value = getattr(output, "text", None)
            if value:
                visible.append(str(value))
        return "\n".join(visible).strip()

    def _generation_config(self, temperature: float | None, max_output_tokens: int | None) -> dict[str, Any]:
        config: dict[str, Any] = {"temperature": self.settings.ai_default_temperature if temperature is None else temperature}
        if max_output_tokens is not None:
            config["max_output_tokens"] = max_output_tokens
        return config

    async def generate_response(self, *, model: str, system_instruction: str, user_input: str, temperature: float | None = None, max_output_tokens: int | None = None) -> GeneratedAnswer:
        started = time.perf_counter()
        try:
            interaction = await self._get_client().aio.interactions.create(
                model=model,
                input=user_input,
                system_instruction=system_instruction,
                generation_config=self._generation_config(temperature, max_output_tokens),
                store=False,
            )
        except Exception as exc:
            raise ConversationProviderError("Gemini interaction failed") from exc
        text = self._text(interaction)
        if not text:
            raise ConversationProviderError("Gemini returned no visible answer")
        return GeneratedAnswer(text, model, int((time.perf_counter() - started) * 1000), self._usage(interaction))

    async def stream_response(self, *, model: str, system_instruction: str, user_input: str, temperature: float | None = None, max_output_tokens: int | None = None) -> AsyncIterator[str]:
        try:
            stream = await self._get_client().aio.interactions.create(
                model=model,
                input=user_input,
                system_instruction=system_instruction,
                generation_config=self._generation_config(temperature, max_output_tokens),
                store=False,
                stream=True,
            )
            async for event in stream:
                delta = getattr(event, "delta", None)
                text = getattr(delta, "text", None) if delta is not None else getattr(event, "text", None)
                if text:
                    yield str(text)
        except ConversationProviderError:
            raise
        except Exception as exc:
            raise ConversationProviderError("Gemini interaction stream failed") from exc
