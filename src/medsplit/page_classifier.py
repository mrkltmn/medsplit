from .constants import LEGAL_KEYWORDS
from .pdf_pages import PDFpage

# A page needs this many different legal phrases to count as a legal page.
MIN_LEGAL_HITS = 2


def legal_hits(text: str) -> int:
    lowered = " ".join(text.lower().split())
    return sum(keyword in lowered for keyword in LEGAL_KEYWORDS)


def classify_pages(pages: list[PDFpage]) -> None:
    """
    Marks subpoenas, DWQs, affidavits, notices and cover sheets as legal pages.

    A single unmatched page sitting between two legal pages (for example the
    last page of a DWQ that is mostly signature lines) is also treated as legal.
    """
    for page in pages:
        page.is_legal = legal_hits(page.text) >= MIN_LEGAL_HITS

    for i in range(1, len(pages) - 1):
        if pages[i - 1].is_legal and pages[i + 1].is_legal:
            pages[i].is_legal = True
