import io
import json
import logging
import os
import fitz  # PyMuPDF
import httpx
import pytz
from pathlib import Path
from urllib.parse import unquote, urlsplit
from datetime import datetime, timedelta
from typing import List, Literal, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from starlette.concurrency import run_in_threadpool

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from . import config  # noqa: F401  (loads root + backend .env)
from .chatbot import router as chatbot_router
from .routers.profiles import router as profiles_router

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
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


def redis_job_store_from_url(redis_url: str) -> RedisJobStore:
    parsed = urlsplit(redis_url)
    if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
        raise ValueError("REDIS_URL must be a valid redis:// or rediss:// URL")

    connect_args = {
        "host": parsed.hostname,
        "port": parsed.port or 6379,
    }
    if parsed.username:
        connect_args["username"] = unquote(parsed.username)
    if parsed.password:
        connect_args["password"] = unquote(parsed.password)
    if parsed.scheme == "rediss":
        connect_args["ssl"] = True

    db_path = parsed.path.strip("/")
    db = int(db_path) if db_path else 0
    return RedisJobStore(db=db, **connect_args)

# --- Phase 2: Configure Redis-Backed Scheduler ---
jobstores = {
    'default': redis_job_store_from_url(REDIS_URL)
}
executors = {
    'default': ThreadPoolExecutor(20)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores, 
    executors=executors, 
    job_defaults=job_defaults,
    timezone=pytz.utc
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    print("[SERVER] Persistent Redis Scheduler started.")
    yield
    scheduler.shutdown()
    print("[SERVER] Scheduler stopped.")

app = FastAPI(title="DocExtract Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatbot_router)
app.include_router(profiles_router)

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

def trigger_notification_job(event_title: str, device_token: str):
    """Execution function called by APScheduler when notification time arrives"""
    print(f"\n[PUSH TRIGGERED] Delivering notification to {device_token}: '{event_title}'")

def queue_notification(device_token: str, event: EventItem, user_tz_str: str):
    """Schedules job into Redis store with client timezone normalization"""
    try:
        user_tz = pytz.timezone(user_tz_str)
        # Parse ISO string and assign client timezone
        naive_dt = datetime.fromisoformat(event.event_date)
        local_dt = user_tz.localize(naive_dt) if naive_dt.tzinfo is None else naive_dt
        
        # Calculate trigger time (15 minutes prior) in UTC
        trigger_time = (local_dt - timedelta(minutes=15)).astimezone(pytz.utc)
        
        # Save persistent job in Redis
        job = scheduler.add_job(
            trigger_notification_job,
            'date',
            run_date=trigger_time,
            args=[event.title, device_token],
            id=f"job_{event.title}_{device_token}_{trigger_time.timestamp()}",
            replace_existing=True
        )
        print(f"[REDIS SAVED] Job '{job.id}' scheduled for UTC: {trigger_time}")
    except Exception as e:
        print(f"[Scheduler Error] Could not schedule event: {e}")

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "DocExtract Backend Running with Redis Scheduler"}

@app.post("/api/v1/upload")
async def upload_document(
    file: UploadFile = File(...), 
    device_token: Optional[str] = Form(None),
    x_timezone: Optional[str] = Header("UTC")  # Accepts client timezone from headers
):
    suffix = Path(file.filename or "").suffix.lower()
    accepted_mime_types = SUPPORTED_UPLOADS.get(suffix)
    if accepted_mime_types is None or file.content_type not in accepted_mime_types:
        raise HTTPException(
            status_code=415,
            detail="Upload must be a PDF or a supported JPEG, PNG, BMP, or TIFF image",
        )

    try:
        file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeds the {MAX_UPLOAD_MB} MB limit",
            )
        if not file_bytes:
            raise HTTPException(status_code=422, detail="Uploaded file is empty")

        raw_text = await run_in_threadpool(
            extract_raw_text, file_bytes, file.filename or ""
        )
        if len(raw_text) > MAX_EXTRACTION_TEXT_CHARS:
            raise DocumentInputError(
                f"Extracted text exceeds the {MAX_EXTRACTION_TEXT_CHARS}-character limit"
            )
        if not raw_text.strip():
            return JSONResponse(
                status_code=422, content={"status": "no_text_found"}
            )
        extracted = await parse_events_with_ollama(raw_text, x_timezone or "UTC")

        # Upload results are drafts; reminders are scheduled only after review.
        return {
            "status": "success", 
            "filename": file.filename,
            "user_timezone": x_timezone or "UTC",
            "review_required": True,
            "extracted_events": [e.model_dump() for e in extracted.events]
        }
    except HTTPException:
        raise
    except DocumentInputError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        raise HTTPException(status_code=422, detail="Uploaded PDF is invalid") from exc
    except pytz.UnknownTimeZoneError as exc:
        raise HTTPException(status_code=422, detail="Unknown timezone") from exc
    except EventExtractionError:
        return JSONResponse(
            status_code=502, content={"status": "extraction_failed"}
        )