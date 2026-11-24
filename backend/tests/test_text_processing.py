from tests.pdf_fixtures import make_pdf_bytes
from app.services import text_extraction, chunking


def test_extract_pages_returns_text_per_page(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(make_pdf_bytes(["Page one content here.", "Page two content here."]))

    pages = text_extraction.extract_pages(str(pdf_path))

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "Page one" in pages[0].text
    assert pages[1].page_number == 2
    assert "Page two" in pages[1].text


def test_chunk_pages_short_page_single_chunk():
    pages = [text_extraction.PageText(page_number=1, text="Short text.")]
    chunks = chunking.chunk_pages(pages)
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0


def test_chunk_pages_long_page_splits_with_overlap():
    long_text = "word " * 1000  # much longer than default chunk_size
    pages = [text_extraction.PageText(page_number=3, text=long_text)]
    chunks = chunking.chunk_pages(pages, chunk_size=200, overlap=20)

    assert len(chunks) > 1
    assert all(c.page_number == 3 for c in chunks)
    # chunk_index should be sequential starting at 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_pages_skips_blank_pages():
    pages = [
        text_extraction.PageText(page_number=1, text="   "),
        text_extraction.PageText(page_number=2, text="Real content"),
    ]
    chunks = chunking.chunk_pages(pages)
    assert len(chunks) == 1
    assert chunks[0].page_number == 2
