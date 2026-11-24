"""
Chunking: splits per-page text into overlapping windows suitable for
embedding. Character-based (not token-based) to avoid an extra tokenizer
dependency — good enough at this stage since the embedding model itself
truncates at its own max sequence length regardless.
"""

from dataclasses import dataclass

from app.services.text_extraction import PageText

DEFAULT_CHUNK_SIZE = 1200   # characters
DEFAULT_CHUNK_OVERLAP = 150  # characters


@dataclass
class Chunk:
    chunk_index: int
    page_number: int
    text: str


def chunk_pages(
    pages: list[PageText],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    Chunk each page's text independently (chunks never span pages), so a
    chunk's page_number is always unambiguous for citation purposes. A
    page longer than chunk_size is split into multiple overlapping chunks;
    a page shorter than chunk_size becomes exactly one chunk.
    """
    chunks: list[Chunk] = []
    index = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        if len(text) <= chunk_size:
            chunks.append(Chunk(chunk_index=index, page_number=page.page_number, text=text))
            index += 1
            continue

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    Chunk(chunk_index=index, page_number=page.page_number, text=piece)
                )
                index += 1
            if end == len(text):
                break
            start = end - overlap  # step forward, re-including the overlap window

    return chunks
