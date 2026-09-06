import re
from pathlib import PurePath


def sanitize_filename(filename: str | None) -> str:
    raw = (filename or "document.pdf").replace("\x00", "")
    name = PurePath(raw).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    if not name or not name.lower().endswith(".pdf"):
        raise ValueError("Only PDF filenames are supported")
    return name[:180]


def validate_pdf_bytes(filename: str | None, content_type: str | None, data: bytes, max_size_bytes: int) -> str:
    safe_name = sanitize_filename(filename)
    if content_type not in {"application/pdf", "application/octet-stream", None}:
        raise ValueError("Unsupported file type. Upload a PDF.")
    if len(data) > max_size_bytes:
        raise ValueError("PDF file is too large")
    if not data.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF")
    return safe_name
