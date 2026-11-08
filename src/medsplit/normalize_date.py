import datetime as dt


def normalize_date(date: str) -> str:
    initial_date = date

    if "/" in initial_date:
        split_date = initial_date.split("/")
    elif "-" in initial_date:
        split_date = initial_date.split("-")
    elif "." in initial_date:
        split_date = initial_date.split(".")
