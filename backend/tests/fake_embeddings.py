"""
Deterministic fake embedder for tests. Real embeddings come from
sentence-transformers, which downloads a model on first use — not
something a unit test should depend on. This produces stable,
low-dimensional vectors derived from text hashing so similarity queries
in tests are still meaningful (same text -> same vector).
"""

import hashlib

from app.services.embeddings import EmbeddingService

DIMENSIONS = 16


class FakeEmbeddingService(EmbeddingService):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Map bytes to floats in [-1, 1], deterministic per input text.
        return [(b / 127.5) - 1.0 for b in digest[:DIMENSIONS]]

    @property
    def dimensions(self) -> int:
        return DIMENSIONS
