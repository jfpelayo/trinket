"""Document text extraction and local-model event parsing.

Shared by the HTTP upload routes and the standalone document worker, so it
must not import the web app or its Redis scheduler.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Literal

import fitz  # PyMuPDF
import httpx
import pytz
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, field_validator
from starlette.concurrency import run_in_threadpool

from . import config  # noqa: F401  (loads root + backend .env)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_EXTRACTION_TEXT_CHARS = 60_000
OLLAMA_CHUNK_CHARS = 12_000
logger = logging.getLogger(__name__)

SUPPORTED_UPLOADS = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".bmp": {"image/bmp", "image/x-ms-bmp"},
    ".tif": {"image/tiff"},
    ".tiff": {"image/tiff"},
}


class EventExtractionError(Exception):
    """The configured Ollama service returned unusable extraction data."""


class DocumentInputError(Exception):
    """The uploaded document cannot be processed within supported limits."""


# EasyOCR reader is created lazily so importing this module (tests,
# router wiring) does not trigger the model download.
_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(['en'], gpu=False)
    return _ocr_reader

# --- Data Schemas ---
class EventItem(BaseModel):
    title: str
    category: Literal["meeting", "study", "deadline", "other"]
    event_date: str

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("event_date must be a valid ISO 8601 date or datetime") from exc
        return value

class ExtractedData(BaseModel):
    events: List[EventItem]

# --- Helper Functions ---
def extract_raw_text(file_bytes: bytes, filename: str) -> str:
    text = ""
    if filename.lower().endswith(".pdf"):
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            if len(doc) > MAX_PDF_PAGES:
                raise DocumentInputError(
                    f"PDF exceeds the {MAX_PDF_PAGES}-page limit"
                )
            for page in doc:
                page_text = page.get_text()
                if page_text.strip():
                    text += page_text + "\n"
                else:
                    pix = page.get_pixmap()
                    results = get_ocr_reader().readtext(pix.tobytes())
                    text += " ".join([res[1] for res in results]) + "\n"
    else:
        results = get_ocr_reader().readtext(file_bytes)
        text = " ".join([res[1] for res in results])
    return text

async def parse_events_with_ollama(
    extracted_text: str, user_tz_str: str
) -> ExtractedData:
    user_timezone = pytz.timezone(user_tz_str)
    if len(extracted_text) > MAX_EXTRACTION_TEXT_CHARS:
        raise DocumentInputError(
            f"Extracted text exceeds the {MAX_EXTRACTION_TEXT_CHARS}-character limit"
        )

    today = datetime.now(user_timezone).date().isoformat()
    chunks = [
        extracted_text[start : start + OLLAMA_CHUNK_CHARS]
        for start in range(0, len(extracted_text), OLLAMA_CHUNK_CHARS)
    ]
    events = []
    try:
        async with httpx.AsyncClient() as client:
            for index, chunk in enumerate(chunks, start=1):
                prompt = f"""
Extract events, deadlines, project dates, and meeting times from this document section.
User local timezone: {user_tz_str}
Today's date in that timezone: {today}.
Use a year explicitly stated in the document. If a date omits its year, infer
the nearest upcoming date relative to today; do not invent an academic term.
Return only events supported by the text. Use valid ISO 8601 dates/timestamps.
This is section {index} of {len(chunks)}.

Document content:
{chunk}
"""
                response = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "format": ExtractedData.model_json_schema(),
                        "stream": False,
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
                result_json = response.json()["response"]
                events.extend(
                    ExtractedData.model_validate_json(result_json).events
                )
    except (
        httpx.HTTPError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        logger.warning("Ollama event extraction failed", exc_info=True)
        raise EventExtractionError("Ollama returned unusable extraction data") from exc

    unique_events = []
    seen = set()
    for event in events:
        key = (event.title, event.category, event.event_date)
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
    return ExtractedData(events=unique_events)


async def read_upload_text(file: UploadFile) -> str:
    """Validate an upload and return its extracted text (may be blank)."""
    suffix = Path(file.filename or "").suffix.lower()
    if file.content_type not in SUPPORTED_UPLOADS.get(suffix, set()):
        raise HTTPException(
            status_code=415,
            detail="Upload must be a PDF or a supported JPEG, PNG, BMP, or TIFF image",
        )
    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"Upload exceeds the {MAX_UPLOAD_MB} MB limit"
        )
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    try:
        raw_text = await run_in_threadpool(
            extract_raw_text, file_bytes, file.filename or ""
        )
    except DocumentInputError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        raise HTTPException(status_code=422, detail="Uploaded PDF is invalid") from exc
    if len(raw_text) > MAX_EXTRACTION_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Extracted text exceeds the {MAX_EXTRACTION_TEXT_CHARS}-character limit",
        )
    return raw_text
