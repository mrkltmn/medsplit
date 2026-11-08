import datetime as dt
import re

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# Anything earlier than this is treated as an OCR error rather than a real date.
MIN_YEAR = 1900


def _expand_year(year: int) -> int:
    """
    Turns a two digit year into a four digit year. Years that would land in the
    future are assumed to be from the 1900s (e.g. "70" -> 1970, "24" -> 2024).
    """
    if year >= 100:
        return year

    current_two_digit = dt.date.today().year % 100
    if year <= current_two_digit:
        return 2000 + year
    return 1900 + year


def _build_date(year: int, month: int, day: int) -> dt.date | None:
    """
    Builds a date, returning None if the numbers do not make a real calendar
    date (e.g. 16/30/2025 from bad OCR) or the date is implausible.
    """
    year = _expand_year(year)

    try:
        date = dt.date(year, month, day)
    except ValueError:
        return None

    if date.year < MIN_YEAR or date > dt.date.today():
        return None

    return date


def normalize_date(date: str) -> dt.date | None:
    """
    Converts a date string found by the search function into a datetime.date.

    Handles:
        - MM/DD/YYYY, MM-DD-YY, MM.DD.YYYY (US order is assumed)
        - YYYY-MM-DD
        - March 6, 2024 / Mar 6th 2024
        - 6 March 2024 / 6-Mar-24

    Returns None when the string is not a valid date.
    """
    initial_date = date.strip().lower()
    initial_date = re.sub(r"(\d)(?:st|nd|rd|th)\b", r"\1", initial_date)  # 6th -> 6

    # Text dates: pull out the month name and the numbers around it.
    month_match = re.search(r"[a-z]+", initial_date)
    if month_match:
        month = MONTHS.get(month_match.group()[:3])
        if month is None:
            return None

        numbers = [int(n) for n in re.findall(r"\d+", initial_date)]
        if len(numbers) != 2:
            return None

        # "March 6, 2024" and "6 March 2024" both give [day, year].
        day, year = numbers
        return _build_date(year, month, day)

    split_date = re.split(r"[-/.]", initial_date)
    if len(split_date) != 3 or not all(part.isdigit() for part in split_date):
        return None

    first, second, third = (int(part) for part in split_date)

    if len(split_date[0]) == 4:
        return _build_date(first, second, third)  # YYYY-MM-DD

    return _build_date(third, first, second)  # MM/DD/YYYY


def to_folder_name(date: dt.date) -> str:
    """
    Formats a date as YYYYMMDD for use as a folder name.
    """
    return date.strftime("%Y%m%d")
