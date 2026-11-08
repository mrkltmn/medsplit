import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

# (x0, y0, x1, y1, word) from OCR, used to make OCR'd output pages searchable.
OcrWord = tuple[float, float, float, float, str]


@dataclass
class PDFpage:
    source_pdf: Path
    page_number: int  # 0-based index in source_pdf
    text: str = ""
    bates_number: str | None = None
    bates_inferred: bool = False
    is_legal: bool = False
    date_of_encounter: dt.date | None = None
    date_source: str = ""  # how the date was chosen, for the index CSV
    ocr_used: bool = False
    ocr_words: list[OcrWord] = field(default_factory=list)
    has_images: bool = False
