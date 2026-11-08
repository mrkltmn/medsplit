import datetime as dt
import re
from collections import Counter
from dataclasses import dataclass

from .constants import (
    ENCOUNTER_LABELS_FACILITY,
    ENCOUNTER_LABELS_FALLBACK,
    ENCOUNTER_LABELS_PRIMARY,
    EXCLUDE_LABELS,
    FILE_WIDE_EXCLUDE_LABELS,
    OCR_LABEL_VARIANTS,
    UNLABELED_CONTEXT_EXCLUDE,
)
from .normalize_date import normalize_date

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


PRIMARY_PATTERN = build_pattern(ENCOUNTER_LABELS_PRIMARY + OCR_LABEL_VARIANTS)
FACILITY_PATTERN = build_pattern(ENCOUNTER_LABELS_FACILITY)
FALLBACK_PATTERN = build_pattern(ENCOUNTER_LABELS_FALLBACK)
EXCLUDE_PATTERN = build_pattern(EXCLUDE_LABELS)
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


# Tiers 0 (primary) and 1 (facility) are trusted enough to override a
# "continued from the previous page" signal; tiers 2 and 3 are not.
STRONG_TIERS = (0, 1)

CONTEXT_EXCLUDE_PATTERN = re.compile(
    "|".join(map(re.escape, UNLABELED_CONTEXT_EXCLUDE)), flags=re.IGNORECASE
)


@dataclass(frozen=True, kw_only=True)
class PageDate:
    date: dt.date
    tier: int
    label: str | None


def excluded_dates(text: str) -> tuple[list[tuple[int, int]], set[dt.date]]:
    """
    Finds dates that sit right after an excluded label (DOB, date of injury,
    printed on, etc.). Returns the positions of all of them in the text, plus
    the set of patient-level dates (DOB, date of injury...) that should be
    ignored everywhere in the file.
    """
    spans = []
    patient_dates = set()

    for match in EXCLUDE_PATTERN.finditer(text):
        spans.append(match.span("date"))
        label = " ".join(match.group("label").lower().split())
        if label in FILE_WIDE_EXCLUDE_LABELS:
            date = normalize_date(match.group("date"))
            if date is not None:
                patient_dates.add(date)

    return spans, patient_dates


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < span_end and span_start < end for span_start, span_end in spans)


def _line_around(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    return text[line_start : line_end if line_end != -1 else len(text)]


def pick_page_date(
    text: str, ignore_unlabeled: set[dt.date] | None = None
) -> PageDate | None:
    """
    Chooses the most likely encounter date for one page.

    The best (lowest number) tier that has a usable date wins. Within a tier the
    date that appears most often wins, and ties go to the one closest to the top
    of the page. Dates that follow an excluded label (DOB, date of injury, print
    date, ...) or fail validation are skipped.

    ignore_unlabeled: dates that should never be chosen from unlabeled matches,
    such as the patient's DOB or the date of injury found elsewhere in the file.
    """
    ignore_unlabeled = ignore_unlabeled or set()
    exclude_spans, _ = excluded_dates(text)

    for tier_results in search_date(text).values():
        counts: Counter[dt.date] = Counter()
        first_seen: dict[dt.date, SearchResult] = {}

        for result in tier_results:
            if result.date is None:
                continue

            date_start = result.end - len(result.date)
            if _overlaps(date_start, result.end, exclude_spans):
                continue

            date = normalize_date(result.date)
            if date is None:
                continue

            if result.label is None:
                if date in ignore_unlabeled:
                    continue
                if CONTEXT_EXCLUDE_PATTERN.search(
                    _line_around(text, date_start, result.end)
                ):
                    continue

            counts[date] += 1
            first_seen.setdefault(date, result)

        if counts:
            best = max(counts, key=lambda d: (counts[d], -first_seen[d].start))
            result = first_seen[best]
            return PageDate(date=best, tier=result.tier, label=result.label)

    return None
