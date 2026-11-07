from pathlib import Path

import pymupdf

# def ocr_check():
#     """
#     Helper function designed to verify that a file has been OCR'ed prior to it being read and parsed out.
#     """
#     pass


def read_files(path: Path):
    """
    Reads the files and creates page data objects for each page.
    """

    list_pdfs = path.glob("*.pdf")

    for pdf_path in list_pdfs:
        with pymupdf.open(pdf_path) as file:
            pass  # to be drafted
