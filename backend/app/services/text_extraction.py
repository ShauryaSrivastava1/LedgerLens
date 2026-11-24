"""
PDF text extraction. Returns text page-by-page (not one giant blob) because
every downstream consumer — chunking, citations, metric extraction — needs
to know which page a piece of text came from.
"""

from dataclasses import dataclass

import pdfplumber


@dataclass
class PageText:
    page_number: int  # 1-indexed, matches what a human sees in a PDF viewer
    text: str


def extract_pages(pdf_path: str) -> list[PageText]:
    """
    Extract text from every page of a PDF.

    Note: this handles text-based PDFs. Scanned/image-only PDFs will yield
    empty or near-empty text per page — OCR fallback (e.g. pytesseract) is
    a known gap, flagged for a later milestone rather than silently
    guessing at scanned content.
    """
    pages: list[PageText] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageText(page_number=i, text=text))
    return pages
