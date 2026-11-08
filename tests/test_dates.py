import datetime as dt

from medsplit.bates import build_bates_pattern, find_bates
from medsplit.normalize_date import normalize_date, to_folder_name
from medsplit.pdf_grouping import _page_counters
from medsplit.search_function import pick_page_date


def test_normalize_formats():
    assert normalize_date("03/04/2024") == dt.date(2024, 3, 4)
    assert normalize_date("3-4-24") == dt.date(2024, 3, 4)
    assert normalize_date("2024-03-04") == dt.date(2024, 3, 4)
    assert normalize_date("March 6, 2024") == dt.date(2024, 3, 6)
    assert normalize_date("6th Mar 2024") == dt.date(2024, 3, 6)
    assert normalize_date("2/3/70") == dt.date(1970, 2, 3)


def test_normalize_rejects_bad_ocr():
    assert normalize_date("16/30/2025") is None
    assert normalize_date("12/24/2625") is None  # future


def test_folder_name():
    assert to_folder_name(dt.date(2024, 3, 4)) == "20240304"


def test_labeled_beats_unlabeled_and_dob_is_ignored():
    text = "DOB: 02/03/1970\nPrinted on 07/10/2026\nDOS: 03/04/2024\nseen 03/05/2024"
    found = pick_page_date(text)
    assert found is not None
    assert found.date == dt.date(2024, 3, 4)


def test_birth_date_not_used_by_bare_date_label():
    text = "Birth Date: 02/03/1970\nletter written March 6, 2024"
    found = pick_page_date(text)
    assert found is not None
    assert found.date == dt.date(2024, 3, 6)


def test_print_stamp_ignored():
    text = "Generated for Printing on: 01/20/2026 12:18 PM"
    assert pick_page_date(text) is None


def test_bates_pattern_tolerates_ocr():
    pattern = build_bates_pattern("DEF DWQ")
    assert find_bates("footer DEF DWQ 000123", pattern) == "000123"
    assert find_bates("DEF_DW0-000124", pattern) == "000124"
    assert find_bates("no stamp here 000125", pattern) is None


def test_fax_page_counter_ignored():
    assert _page_counters("Page 2 of 3") == {(2, 3)}
    assert _page_counters("From: Records Fax: 555 Page: 9 of 24") == set()
