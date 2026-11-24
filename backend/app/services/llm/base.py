"""
Provider-agnostic LLM interface. The report generator only ever talks to
this abstraction — swapping Claude for GPT, Gemini, or a local model means
adding one small adapter class here, not touching prompt construction,
parsing, or citation-verification logic.
"""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
        """Returns the raw text completion. Callers that need structured
        output are responsible for instructing the model to return JSON
        and parsing/validating it themselves — this interface stays
        provider-neutral rather than assuming any one vendor's
        structured-output feature."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
