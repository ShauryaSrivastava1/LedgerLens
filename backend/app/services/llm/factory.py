"""
Selects which LLM provider to use based on the LLM_PROVIDER environment
variable, so switching providers is a config change, not a code change —
per the spec's requirement that the platform work with OpenAI, Claude,
Gemini, or a local LLM interchangeably.

Only Anthropic and OpenAI adapters are implemented so far. Adding Gemini
or a local (Ollama/vLLM-served) model means writing one more class that
implements LLMClient and registering it below — nothing else in the
report-generation pipeline needs to change, since it only depends on the
LLMClient interface.
"""

import os
from functools import lru_cache

from app.services.llm.base import LLMClient


@lru_cache
def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "anthropic":
        from app.services.llm.anthropic_client import AnthropicLLMClient

        return AnthropicLLMClient()
    elif provider == "openai":
        from app.services.llm.openai_client import OpenAILLMClient

        return OpenAILLMClient()
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Supported: anthropic, openai "
            "(gemini/local: implement LLMClient and register here)."
        )
