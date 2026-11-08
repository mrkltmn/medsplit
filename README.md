# medsplit

Splits a folder of medical-record PDFs into encounters sorted by date.

Run it from inside a folder of PDFs:

```sh
cd "/Volumes/External/Some Case/Records"
medsplit
```

It creates `split_files/` in that folder:

```
split_files/
  _DWQ_and_Subpoenas/   subpoenas, DWQs, affidavits, notices, cover sheets
  _Undated/             medical pages before any date could be found
  20240304/             one folder per encounter date (YYYYMMDD)
    DEF DWQ 000123_DEF DWQ 000130.pdf
  _index.csv            every page: source, Bates, date chosen and why
```

- Each output PDF is one contiguous run of pages from one source file. Two
  visits on the same day land in the same date folder as separate files.
- Files are named `STARTBATES_ENDBATES.pdf`. If a source file has no Bates
  stamps, the name is `<source file name> p<first>-<last>.pdf` instead.
- Original PDFs are never modified.
- Pages with no usable text (scans, or PDFs with broken fonts) are OCR'd with
  Tesseract, and the OCR text is added invisibly to the split files so they
  are searchable.
- Pages without a date inherit the date of the page before them.

Check `_index.csv` to spot-check the result. `date_source` shows how each
page's date was chosen (a label such as `DOS`, an unlabeled date,
continuation of the previous page, or inherited).

## Options

```
medsplit [folder] [--bates-prefix "DEF DWQ"] [--overwrite] [--no-ocr]
```

- `--overwrite`: delete an existing `split_files/` first.
- `--bates-prefix`: Bates prefix to look for (default `DEF DWQ`).
- `--no-ocr`: skip OCR (faster, misses scanned pages).

## Install

Requires [uv](https://docs.astral.sh/uv/) and Tesseract (`brew install tesseract`).

```sh
cd ~/Coding/medsplit
uv tool install --editable .
```

This puts `medsplit` in `~/.local/bin` (run `uv tool update-shell` once if that
folder is not on your PATH). Because it is an editable install, code changes
in this repo take effect immediately.

## How dates are chosen

For each page, labeled dates are searched in tiers (see `constants.py`):

1. Primary labels: DOS, date of service, visit date, exam date...
2. Facility labels: admit/arrival/collection/report date...
3. Fallback labels: `Date:`, today's date, signed on...
4. Unlabeled dates.

Dates after excluded labels (DOB, date of injury, printed/fax dates...) are
skipped, and invalid dates from bad OCR (e.g. `16/30/2025`) are rejected.
A page that says `Page 2 of 3` or `(continued)` keeps the previous page's date
unless it has its own tier 1 or 2 date. Scanned pages with no reliable date
are OCR'd a second time to look for one.

## Development

```sh
uv run pytest
uv run medsplit /path/to/pdfs
```
