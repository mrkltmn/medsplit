import argparse
import shutil
import sys
from pathlib import Path

from .bates import assign_bates, build_bates_pattern, format_bates
from .constants import DEFAULT_BATES_PREFIX, OUTPUT_FOLDER
from .copy_files import write_index, write_run
from .page_classifier import classify_pages
from .pdf_grouping import assign_dates, build_runs
from .read_files import OcrUnavailableError, list_pdfs, ocr_second_chance, read_file


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="medsplit",
        description=(
            "Split the medical-record PDFs in the current folder into encounters "
            f"by date, saved under ./{OUTPUT_FOLDER}/YYYYMMDD/STARTBATES_ENDBATES.pdf."
        ),
    )
    parser.add_argument(
        "folder",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="folder containing the PDFs (default: current folder)",
    )
    parser.add_argument(
        "--bates-prefix",
        default=DEFAULT_BATES_PREFIX,
        help=f'Bates prefix to look for (default: "{DEFAULT_BATES_PREFIX}")',
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=f"delete an existing {OUTPUT_FOLDER} folder first",
    )
    parser.add_argument(
        "--no-ocr", action="store_true", help="never OCR (faster, less accurate)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    folder: Path = args.folder.resolve()
    output_dir = folder / OUTPUT_FOLDER

    pdfs = list_pdfs(folder)
    if not pdfs:
        print(f"No PDFs found in {folder}")
        return 1

    if output_dir.exists():
        if not args.overwrite:
            print(f"{output_dir} already exists. Re-run with --overwrite to replace it.")
            return 1
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    bates_pattern = build_bates_pattern(args.bates_prefix)
    use_ocr = not args.no_ocr
    index_rows: list[dict[str, str]] = []
    written = 0

    for number, pdf_path in enumerate(pdfs, start=1):
        print(f"[{number}/{len(pdfs)}] {pdf_path.name}", flush=True)
        try:
            pages = read_file(pdf_path, use_ocr=use_ocr)
        except OcrUnavailableError as error:
            print(f"  {error}")
            return 1
        except Exception as error:  # damaged or password-protected PDFs
            print(f"  skipped: could not read ({error})")
            continue

        classify_pages(pages)
        assign_bates(pages, bates_pattern)
        assign_dates(pages, second_chance=ocr_second_chance if use_ocr else None)
        runs = build_runs(pages)

        for run in runs:
            target = write_run(run, output_dir, args.bates_prefix)
            written += 1
            for page in run.pages:
                index_rows.append(
                    {
                        "source_file": pdf_path.name,
                        "page": str(page.page_number + 1),
                        "bates": format_bates(args.bates_prefix, page.bates_number)
                        if page.bates_number
                        else "",
                        "bates_inferred": "yes" if page.bates_inferred else "",
                        "category": "legal" if page.is_legal else "medical",
                        "date": page.date_of_encounter.isoformat()
                        if page.date_of_encounter
                        else "",
                        "date_source": page.date_source,
                        "ocr": "yes" if page.ocr_used else "",
                        "output_file": str(target.relative_to(output_dir)),
                    }
                )

        ocr_count = sum(p.ocr_used for p in pages)
        missing_bates = sum(p.bates_number is None for p in pages)
        print(
            f"  {len(pages)} pages -> {len(runs)} files"
            + (f", {ocr_count} pages OCR'd" if ocr_count else "")
            + (f", {missing_bates} pages without Bates" if missing_bates else "")
        )

    index_path = write_index(index_rows, output_dir)
    print(f"\nDone: {written} files written to {output_dir}")
    print(f"Page-by-page details: {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
