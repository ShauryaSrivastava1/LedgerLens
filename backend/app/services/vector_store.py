"""
Vector store wrapper around ChromaDB. All embedding vectors are computed
by our own EmbeddingService and passed in explicitly — we never rely on
Chroma's built-in embedding function, so this module never triggers a
surprise model download.
"""

import os
import uuid
from dataclasses import dataclass
from functools import lru_cache

import chromadb

CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "/tmp/equity-platform/chroma")
COLLECTION_NAME = "document_chunks"


@dataclass
class VectorQueryResult:
    vector_id: str
    text: str
    metadata: dict
    distance: float


class VectorStore:
    def __init__(self, client: chromadb.ClientAPI):
        self._client = client
        self._collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> list[str]:
        """Adds chunks, returns the generated vector ids (one per chunk)."""
        if not texts:
            return []
        ids = [str(uuid.uuid4()) for _ in texts]
        self._collection.add(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
        )
        return ids

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[VectorQueryResult]:
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
        out: list[VectorQueryResult] = []
        if not result["ids"] or not result["ids"][0]:
            return out
        for i in range(len(result["ids"][0])):
            out.append(
                VectorQueryResult(
                    vector_id=result["ids"][0][i],
                    text=result["documents"][0][i],
                    metadata=result["metadatas"][0][i],
                    distance=result["distances"][0][i],
                )
            )
        return out

    def delete_by_document(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})


@lru_cache
def get_persistent_vector_store() -> VectorStore:
    """Production singleton: on-disk persistent Chroma client."""
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
    return VectorStore(client)


def build_ephemeral_vector_store() -> VectorStore:
    """In-memory Chroma client — used by tests, no persistence, no network."""
    client = chromadb.EphemeralClient()
    return VectorStore(client)
