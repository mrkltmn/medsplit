import csv
import re
from pathlib import Path

import pymupdf

from .bates import format_bates
from .constants import LEGAL_FOLDER, UNDATED_FOLDER
from .normalize_date import to_folder_name
from .pdf_grouping import PageRun
from .pdf_pages import PDFpage


def folder_for(run: PageRun) -> str:
    first = run.pages[0]
    if first.is_legal:
        return LEGAL_FOLDER
    if first.date_of_encounter is None:
        return UNDATED_FOLDER
    return to_folder_name(first.date_of_encounter)


def _safe(name: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', "-", name).strip()


def file_name_for(run: PageRun, bates_prefix: str) -> str:
    """
    Names the output STARTBATES_ENDBATES.pdf. When the source has no Bates
    stamps, falls back to "<source file name> p<first>-<last>" (1-based pages).
    """
    first, last = run.pages[0], run.pages[-1]

    if first.bates_number and last.bates_number:
        start = format_bates(bates_prefix, first.bates_number)
        end = format_bates(bates_prefix, last.bates_number)
        return _safe(f"{start}_{end}") + ".pdf"

    stem = first.source_pdf.stem
    return _safe(f"{stem} p{first.page_number + 1}-{last.page_number + 1}") + ".pdf"


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while (candidate := path.with_stem(f"{path.stem} ({counter})")).exists():
        counter += 1
    return candidate


def _add_hidden_text(page: pymupdf.Page, pdf_page: PDFpage) -> None:
    """
    Puts the OCR words on the output page as invisible text so the split PDFs
    are searchable, without changing how the page looks.
    """
    writer = pymupdf.TextWriter(page.rect)
    font = pymupdf.Font("helv")
    for x0, y0, x1, y1, word in pdf_page.ocr_words:
        height = y1 - y0
        if height <= 0:
            continue
        try:
            writer.append((x0, y1 - height * 0.2), word, font=font, fontsize=height * 0.9)
        except ValueError:
            continue
    writer.write_text(page, render_mode=3)


def write_run(run: PageRun, output_dir: Path, bates_prefix: str) -> Path:
    folder = output_dir / folder_for(run)
    folder.mkdir(parents=True, exist_ok=True)
    target = _unique(folder / file_name_for(run, bates_prefix))

    first, last = run.pages[0], run.pages[-1]
    with pymupdf.open(first.source_pdf) as source, pymupdf.open() as out:
        out.insert_pdf(source, from_page=first.page_number, to_page=last.page_number)
        for out_page, pdf_page in zip(out, run.pages):
            if pdf_page.ocr_words:
                _add_hidden_text(out_page, pdf_page)
        out.save(target, garbage=3, deflate=True)

    return target


def write_index(rows: list[dict[str, str]], output_dir: Path) -> Path:
    """
    Writes _index.csv listing every page and where it went, so the sorting can
    be spot-checked.
    """
    path = output_dir / "_index.csv"
    if not rows:
        return path
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
