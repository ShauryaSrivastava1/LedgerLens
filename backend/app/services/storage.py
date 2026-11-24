"""
File storage abstraction. Milestone 2 implementation writes to local disk;
the interface is intentionally narrow (save/read two methods) so swapping
in S3/GCS later doesn't touch any calling code.
"""

import os
import uuid
from pathlib import Path

STORAGE_ROOT = Path(os.getenv("DOCUMENT_STORAGE_PATH", "/tmp/equity-platform/documents"))


def save_upload(company_id: uuid.UUID, document_id: uuid.UUID, filename: str, content: bytes) -> str:
    """
    Persist raw file bytes to disk under a company/document-scoped path.
    Returns the storage path (what gets saved on the Document row).
    """
    ext = Path(filename).suffix or ".pdf"
    target_dir = STORAGE_ROOT / str(company_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{document_id}{ext}"
    target_path.write_bytes(content)
    return str(target_path)


def read_file(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()
