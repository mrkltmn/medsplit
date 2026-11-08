import datetime as dt
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from .pdf_pages import PDFpage
from .search_function import STRONG_TIERS, PageDate, excluded_dates, pick_page_date

PAGE_X_OF_Y = re.compile(
    r"\bpage\s*:?\s*(\d{1,3})\s*[.,]?\s*(?:of|/)\s*(\d{1,3})\b", re.IGNORECASE
)
CONTINUED = re.compile(r"\(\s*continued\s*\)|\bcontinued from\b", re.IGNORECASE)
FAX_CONTEXT = re.compile(r"fax|from\s*:", re.IGNORECASE)

# An unlabeled date on at least this share of a file's pages, and later than
# every labeled date, is assumed to be a print/fax stamp, not a visit date.
BOILERPLATE_SHARE = 0.6
BOILERPLATE_MIN_PAGES = 5


def _page_counters(text: str) -> set[tuple[int, int]]:
    """
    Returns every "Page k of n" found on the page, skipping fax-header counters.
    """
    counters = set()
    for match in PAGE_X_OF_Y.finditer(text):
        before = text[max(0, match.start() - 80) : match.start()]
        if FAX_CONTEXT.search(before):
            continue
        counters.add((int(match.group(1)), int(match.group(2))))
    return counters


def is_continuation(page: PDFpage, previous: PDFpage | None) -> bool:
    """
    True when the page says it continues the previous one: either "(continued)"
    near the top, or a "Page k of n" counter with k > 1. (The previous page's
    counter is not required to match because OCR often garbles it.)
    """
    if previous is None:
        return False
    if CONTINUED.search(page.text[:600]):
        return True

    return any(1 < k <= n for k, n in _page_counters(page.text))


def _boilerplate_dates(page_dates: list[PageDate | None]) -> set[dt.date]:
    """
    Finds unlabeled dates that are stamped on most pages of a file and are later
    than every labeled date (e.g. "printed 7/10/26" with no label).
    """
    unlabeled = [pd for pd in page_dates if pd is not None and pd.label is None]
    if len(unlabeled) < BOILERPLATE_MIN_PAGES:
        return set()

    labeled = [pd.date for pd in page_dates if pd is not None and pd.label is not None]
    latest_labeled = max(labeled) if labeled else None

    counts = Counter(pd.date for pd in unlabeled)
    return {
        date
        for date, count in counts.items()
        if count / len(page_dates) >= BOILERPLATE_SHARE
        and (latest_labeled is None or date > latest_labeled)
    }


def assign_dates(
    pages: list[PDFpage],
    second_chance: Callable[[PDFpage], str] | None = None,
) -> None:
    """
    Gives each non-legal page of one file an encounter date.

    Order of preference:
        1. A strongly labeled date on the page (DOS, visit date, admit date...).
        2. The previous page's date, if this page continues the previous one.
        3. A weaker date on the page (a bare "Date:", or an unlabeled date).
        4. The previous page's date.
    Pages before the first dated page stay undated.

    second_chance: optional function returning fresh OCR text for scanned pages.
    It is used when the existing text layer gave no date or only a weak one
    (often an unreadable DOS label); a strong date from the new OCR wins.
    """
    medical = [p for p in pages if not p.is_legal]

    # Patient DOB / date of injury etc., wherever they appear in the file.
    file_excluded: set[dt.date] = set()
    for page in medical:
        file_excluded |= excluded_dates(page.text)[1]

    page_dates = [pick_page_date(p.text, file_excluded) for p in medical]

    boilerplate = _boilerplate_dates(page_dates)
    if boilerplate:
        file_excluded |= boilerplate
        page_dates = [pick_page_date(p.text, file_excluded) for p in medical]

    if second_chance is not None:
        for i, page in enumerate(medical):
            found = page_dates[i]
            if found is not None and found.tier in STRONG_TIERS:
                continue
            if not page.has_images or page.ocr_used:
                continue
            retry = pick_page_date(second_chance(page), file_excluded)
            if retry is not None and (found is None or retry.tier in STRONG_TIERS):
                page_dates[i] = retry

    previous: PDFpage | None = None
    for page, found in zip(medical, page_dates):
        strong = found is not None and found.tier in STRONG_TIERS
        inherited = previous.date_of_encounter if previous else None

        if strong:
            page.date_of_encounter = found.date
            page.date_source = f"label '{found.label}'"
        elif inherited and is_continuation(page, previous):
            page.date_of_encounter = inherited
            page.date_source = "continuation of previous page"
        elif found is not None:
            page.date_of_encounter = found.date
            page.date_source = f"label '{found.label}'" if found.label else "unlabeled date"
        elif inherited:
            page.date_of_encounter = inherited
            page.date_source = "inherited from previous page"
        else:
            page.date_source = "no date found"

        previous = page


@dataclass
class PageRun:
    """
    Consecutive pages of one source PDF that belong in the same output folder.
    """

    pages: list[PDFpage]

    @property
    def key(self) -> tuple[bool, dt.date | None]:
        first = self.pages[0]
        return first.is_legal, first.date_of_encounter


def build_runs(pages: list[PDFpage]) -> list[PageRun]:
    """
    Splits one file's pages into runs wherever the date or legal/medical status
    changes. Each run becomes one output PDF.
    """
    runs: list[PageRun] = []

    for page in pages:
        key = (page.is_legal, None if page.is_legal else page.date_of_encounter)
        if runs and runs[-1].key == key and (
            runs[-1].pages[-1].page_number == page.page_number - 1
        ):
            runs[-1].pages.append(page)
        else:
            runs.append(PageRun(pages=[page]))

    return runs
