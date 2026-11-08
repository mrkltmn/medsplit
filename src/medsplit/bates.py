import re

import pymupdf

from .pdf_pages import PDFpage

# Characters OCR commonly confuses with each other in Bates prefixes.
OCR_LOOKALIKES = {
    "O": "[O0Q]",
    "Q": "[QO0]",
    "0": "[0OQ]",
    "I": "[I1l]",
    "1": "[1Il]",
    "L": "[L1I]",
    "S": "[S5]",
    "5": "[5S]",
}

# Bates stamps are usually in the bottom part of the page.
BOTTOM_SHARE = 0.15


def build_bates_pattern(prefix: str) -> re.Pattern[str]:
    """
    Turns a prefix like "DEF DWQ" into a regex that matches "DEF DWQ 000123",
    "DEF_DWQ000123", "DEF-DW0 000123" (OCR error), etc.
    """
    words = []
    for word in prefix.split():
        words.append("".join(OCR_LOOKALIKES.get(ch.upper(), re.escape(ch)) for ch in word))

    joined = r"[\s_\-]*".join(words)
    return re.compile(
        r"(?<![A-Za-z0-9])" + joined + r"[\s_\-]*(?P<number>\d{3,})(?!\d)",
        flags=re.IGNORECASE,
    )


def find_bates(text: str, pattern: re.Pattern[str]) -> str | None:
    """
    Returns the number part of the last Bates stamp in the text.
    """
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    return matches[-1].group("number")


def assign_bates(pages: list[PDFpage], pattern: re.Pattern[str]) -> None:
    """
    Finds the Bates number for each page of one file.

    The bottom of the page is checked first, then the whole page (including any
    OCR text). Pages where no stamp could be read get a number inferred from the
    nearest stamped page, since Bates numbers run in page order.
    """
    if not pages:
        return

    numbers: list[str | None] = []
    with pymupdf.open(pages[0].source_pdf) as file:
        for pdf_page in pages:
            page = file[pdf_page.page_number]
            rect = page.rect
            bottom = pymupdf.Rect(0, rect.height * (1 - BOTTOM_SHARE), rect.width, rect.height)
            number = find_bates(page.get_text("text", clip=bottom), pattern)
            if number is None:
                number = find_bates(pdf_page.text, pattern)
            numbers.append(number)

    known = [(i, n) for i, n in enumerate(numbers) if n is not None]
    if not known:
        return

    for i, pdf_page in enumerate(pages):
        if numbers[i] is not None:
            pdf_page.bates_number = numbers[i]
            continue

        nearest_index, nearest_number = min(known, key=lambda k: abs(k[0] - i))
        value = int(nearest_number) + (i - nearest_index)
        if value < 0:
            continue
        pdf_page.bates_number = str(value).zfill(len(nearest_number))
        pdf_page.bates_inferred = True


def format_bates(prefix: str, number: str) -> str:
    return f"{prefix} {number}"
