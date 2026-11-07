from dataclasses import dataclass
from pathlib import Path


@dataclass
class PDFpage:
    source_pdf: Path
    page_number: int
    bates_number: str
    date_of_encounter: str | None = None
