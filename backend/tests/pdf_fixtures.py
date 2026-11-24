"""
Generates small real PDF files for tests, so text_extraction/chunking/
the full pipeline are exercised against an actual PDF rather than mocked
away. Uses reportlab (test-only dependency).
"""

import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def make_pdf_bytes(pages_text: list[str]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    for text in pages_text:
        y = 800
        for line in text.split("\n"):
            c.drawString(50, y, line[:110])  # keep lines within page width
            y -= 15
        c.showPage()
    c.save()
    return buffer.getvalue()
