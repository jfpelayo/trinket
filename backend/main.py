import os
import fitz  # PyMuPDF
import pytz
from pathlib import Path
from urllib.parse import unquote, urlsplit
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from . import config  # noqa: F401  (loads root + backend .env)
from .chatbot import router as chatbot_router
from .routers.devices import router as devices_router
from .routers.documents import router as documents_router
from .routers.events import router as events_router
from .routers.profiles import router as profiles_router
from .extraction import (  # noqa: F401  (re-exported for the legacy route/tests)
    MAX_EXTRACTION_TEXT_CHARS,
    MAX_PDF_PAGES,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    OLLAMA_CHUNK_CHARS,
    OLLAMA_MODEL,
    OLLAMA_URL,
    SUPPORTED_UPLOADS,
    DocumentInputError,
    EventExtractionError,
    EventItem,
    ExtractedData,
    extract_raw_text,
    get_ocr_reader,
    parse_events_with_ollama,
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_CORS_ORIGINS = "http://localhost:8081,http://localhost:8082,http://localhost:19006"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

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
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location"],
)

app.include_router(chatbot_router)
app.include_router(profiles_router)
app.include_router(documents_router)
app.include_router(events_router)
app.include_router(devices_router)


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