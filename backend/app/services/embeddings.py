"""
Embedding generation. Wraps Sentence Transformers behind a small interface
so (a) the model is loaded once and reused, not once per request, and
(b) tests can swap in a fake embedder — sentence-transformers pulls a
~90MB model from the internet on first use, which has no place running
in a unit test.
"""

import os
from abc import ABC, abstractmethod
from functools import lru_cache

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")


class EmbeddingService(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        ...


class SentenceTransformerEmbeddingService(EmbeddingService):
    """Production embedding service. Model is loaded once, lazily, on first use."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            # Imported here, not at module level, so importing this file
            # never requires torch/sentence-transformers to be installed
            # unless this class is actually instantiated and used.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return [vec.tolist() for vec in embeddings]

    @property
    def dimensions(self) -> int:
        return self._get_model().get_sentence_embedding_dimension()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """FastAPI dependency / app-wide singleton accessor."""
    return SentenceTransformerEmbeddingService()
