import re
from dataclasses import dataclass

from .constants import (
    ENCOUNTER_LABELS_FACILITY,
    ENCOUNTER_LABELS_FALLBACK,
    ENCOUNTER_LABELS_PRIMARY,
)

SEP_SYMB = r"\s*[:#\-]?\s*"
MONTH = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?"
    r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\.?(?![A-Za-z])"
)
ORDINAL = r"(?:st|nd|rd|th)?"

ISO_DATE = r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"
NUMERIC_DATE = r"\d{1,2}[-/.]\d{1,2}[-/.](?:\d{4}|\d{2})"
TEXT_MDY = MONTH + r"\s+\d{1,2}" + ORDINAL + r"(?:,\s*|\s+)\d{4}"
TEXT_DMY = r"\d{1,2}" + ORDINAL + r"[\s\-]+" + MONTH + r"[\s\-,]+(?:\d{4}|\d{2})"

DATE_TERM = (
    r"(?<!\d)(?:"
    + ISO_DATE
    + "|"
    + NUMERIC_DATE
    + "|"
    + TEXT_MDY
    + "|"
    + TEXT_DMY
    + r")(?!\d)"
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
        "(?<![A-Za-z])"
        + "(?P<label>"
        + label_search
        + ")"
        + SEP_SYMB
        + "(?P<date>"
        + DATE_TERM
        + ")"
    )

    return re.compile(full_search, flags=re.IGNORECASE)


PRIMARY_PATTERN = build_pattern(ENCOUNTER_LABELS_PRIMARY)
FACILITY_PATTERN = build_pattern(ENCOUNTER_LABELS_FACILITY)
FALLBACK_PATTERN = build_pattern(ENCOUNTER_LABELS_FALLBACK)
UNLABELED_PATTERN = re.compile(
    r"(?<![A-Za-z])(?P<date>" + DATE_TERM + ")",
    flags=re.IGNORECASE,
)

SEARCH_TERMS = {
    "primary": PRIMARY_PATTERN,
    "facility": FACILITY_PATTERN,
    "fallback": FALLBACK_PATTERN,
    "unlabeled": UNLABELED_PATTERN,
}


@dataclass(frozen=True, kw_only=True)
class SearchResult:
    label: str | None
    date: str | None
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
                    label=result.groupdict().get("label"),
                    date=result.groupdict().get("date"),
                    start=result.start(),
                    end=result.end(),
                    tier=priority,
                )
            )

        found_terms[term] = result_list

    return found_terms
