from typing import Protocol


class TextGenerationProvider(Protocol):
    async def generate_text(self, prompt: str) -> str:
        """Generate text from a prompt using a configured provider."""
