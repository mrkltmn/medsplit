import datetime
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from .constants import (
    ENCOUNTER_LABELS_FACILITY,
    ENCOUNTER_LABELS_FALLBACK,
    ENCOUNTER_LABELS_PRIMARY,
)

# def ocr_check():
#     """
#     Helper function designed to verify that a file has been OCR'ed prior to it being read and parsed out.
#     """
#     pass

SEP_SYMB = r"\s*[:#\-]?\s*"
DATE_TERM = (
    r"(?<!\d)"
    r"(?:"
    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"
    r"|"
    r"\d{1,2}[-/.]\d{1,2}[-/.](?:\d{4}|\d{2})"
    r")"
    r"(?!\d)"
)


def label_to_pattern(label: str) -> str:
    split_label = label.split()
    escaped_split = list(map(re.escape, split_label))
    joined_label = r"\s+".join(escaped_split)

    return joined_label


def label_alternatives_builder(labels: tuple[str, ...]) -> str:
    return "|".join(map(label_to_pattern, sorted(labels, key=len, reverse=True)))


def build_pattern(labels: tuple[str, ...]) -> re.Pattern[str]:

    label_search = label_alternatives_builder(labels)

    full_search = (
        "(?<![A-Za-z])" + "(" + label_search + ")" + SEP_SYMB + "(" + DATE_TERM + ")"
    )

    return re.compile(full_search, flags=re.IGNORECASE)


PRIMARY_PATTERN = build_pattern(ENCOUNTER_LABELS_PRIMARY)
FACILITY_PATTERN = build_pattern(ENCOUNTER_LABELS_FACILITY)
FALLBACK_PATTERN = build_pattern(ENCOUNTER_LABELS_FALLBACK)

SEARCH_TERMS = {
    "primary": PRIMARY_PATTERN,
    "facility": FACILITY_PATTERN,
    "fallback": FALLBACK_PATTERN,
}


@dataclass(frozen=True, kw_only=True)
class SearchResult:
    label: str
    date: str
    start: int
    end: int
    tier: int


def search_date(text: str) -> dict[str, list[SearchResult]]:
    """
    Searches the text passed to it and returns a dictionary with the key as the level of search term that resulted with a list of SearchResult dataclasses containing information about the result.
    """

    found_terms = {}

    for priority, (term, pattern) in enumerate(SEARCH_TERMS.items()):
        results = pattern.finditer(text)
        result_list = []

        for result in results:
            result_list.append(
                SearchResult(
                    label=result.group(1),
                    date=result.group(2),
                    start=result.start(),
                    end=result.end(),
                    tier=priority,
                )
            )

        found_terms[term] = result_list

    return found_terms


def read_files(path: Path):
    """
    Reads the files and creates page data objects for each page.
    """

    list_pdfs = path.glob("*.pdf")

    for pdf_path in list_pdfs:
        with pymupdf.open(pdf_path) as file:
            pass  # to be drafted
