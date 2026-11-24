import os

from app.services.llm.base import LLMClient

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")


class AnthropicLLMClient(LLMClient):
    """Adapter over Anthropic's Messages API. SDK imported lazily so this
    module can be imported (e.g. by tests) without the `anthropic` package
    installed unless this class is actually instantiated."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None):
        self._model = model
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
        client = self._get_client()
        response = client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model
