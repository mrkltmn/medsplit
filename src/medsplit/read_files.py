import os
import re
from contextlib import contextmanager
from functools import cache
from pathlib import Path

import pymupdf

from .pdf_pages import PDFpage

# A token that looks like a real word or number. Used to tell a real text layer
# from garbage (PDFs with broken fonts extract as strings like "KL1MN=8983").
WORD_PATTERN = re.compile(
    r"^(?:[A-Za-z][a-z]+|[A-Z]{2,}|\d[\d/.,:-]*)[.,:;)]?$"
)

# Below this share of real-looking words, the text layer is treated as missing.
MIN_TEXT_QUALITY = 0.5
MIN_TEXT_CHARS = 50
OCR_DPI = 300


class OcrUnavailableError(RuntimeError):
    pass


@cache
def tessdata_path() -> str:
    """
    Locates Tesseract's language data. PyMuPDF finds it by asking the installed
    tesseract binary, so this fails if Tesseract is not installed.
    """
    path = pymupdf.get_tessdata()
    if not path:
        raise OcrUnavailableError(
            "Tesseract language data not found. Install with: brew install tesseract"
        )
    return path


def text_quality(text: str) -> float:
    """
    Returns the share of whitespace-separated tokens that look like real words.
    """
    tokens = text.split()
    if not tokens:
        return 0.0
    return sum(bool(WORD_PATTERN.match(token)) for token in tokens) / len(tokens)


def needs_ocr(text: str) -> bool:
    """
    True when a page has no usable text layer: either (almost) no text, or text
    that is mostly garbage characters.
    """
    if len(text.strip()) < MIN_TEXT_CHARS:
        return True
    return text_quality(text) < MIN_TEXT_QUALITY


@contextmanager
def _quiet_stderr():
    """
    Tesseract prints harmless warnings ("Image too small to scale!!") straight
    to stderr from C code; hide them so the progress output stays readable.
    """
    saved = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(devnull)
        os.close(saved)


def ocr_page(page: pymupdf.Page) -> tuple[str, list[tuple[float, float, float, float, str]]]:
    """
    Runs Tesseract on a page. Returns the text and the word positions.
    The original PDF is never modified.
    """
    tessdata = tessdata_path()
    with _quiet_stderr():
        textpage = page.get_textpage_ocr(
            language="eng", dpi=OCR_DPI, full=True, tessdata=tessdata
        )
    text = page.get_text("text", textpage=textpage)
    words = [
        (w[0], w[1], w[2], w[3], w[4])
        for w in page.get_text("words", textpage=textpage)
    ]
    return text, words


def apply_ocr(pdf_page: PDFpage, page: pymupdf.Page) -> None:
    text, words = ocr_page(page)
    pdf_page.text = text
    pdf_page.ocr_words = words
    pdf_page.ocr_used = True


def read_file(pdf_path: Path, use_ocr: bool = True) -> list[PDFpage]:
    """
    Reads one PDF and creates a page data object for each page. Pages without a
    usable text layer are OCR'ed.
    """
    pages = []

    with pymupdf.open(pdf_path) as file:
        for page in file:
            text = page.get_text("text")
            pdf_page = PDFpage(
                source_pdf=pdf_path,
                page_number=page.number,
                text=text,
                has_images=bool(page.get_images()),
            )

            if use_ocr and needs_ocr(text):
                apply_ocr(pdf_page, page)

            pages.append(pdf_page)

    return pages


def ocr_second_chance(pdf_page: PDFpage) -> str:
    """
    OCRs a scanned page that already has a text layer but where no date could be
    found, and returns the OCR text (the page's text is left alone).
    """
    with pymupdf.open(pdf_page.source_pdf) as file:
        text, _ = ocr_page(file[pdf_page.page_number])
    return text


def list_pdfs(path: Path) -> list[Path]:
    """
    Returns the PDFs directly inside path, sorted by name.
    """
    return sorted(
        p for p in path.iterdir() if p.suffix.lower() == ".pdf" and p.is_file()
    )
