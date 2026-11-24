import os

from app.services.llm.base import LLMClient

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


class OpenAILLMClient(LLMClient):
    """Adapter over OpenAI's Chat Completions API. Same lazy-import
    pattern as the Anthropic adapter — see there for why."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None):
        self._model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model
