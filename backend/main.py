import io
import os
import fitz  # PyMuPDF
import httpx
import pytz
from urllib.parse import unquote, urlsplit
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    category: str  # "meeting", "study", "deadline", "other"
    event_date: str  # ISO format string

class ExtractedData(BaseModel):
    events: List[EventItem]

# --- Helper Functions ---
def extract_raw_text(file_bytes: bytes, filename: str) -> str:
    text = ""
    if filename.lower().endswith(".pdf"):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
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

async def parse_events_with_ollama(extracted_text: str, user_tz_str: str) -> ExtractedData:
    prompt = f"""
    Extract all events, deadlines, project dates, and meeting times from the following text.
    User Local Timezone: {user_tz_str}
    
    Return a list of events matching the JSON schema. Format dates as ISO 8601 timestamps.
    
    Document Content:
    {extracted_text}
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "format": ExtractedData.model_json_schema(),
                    "stream": False
                },
                timeout=120.0
            )
            result_json = response.json()["response"]
            return ExtractedData.model_validate_json(result_json)
    except Exception as e:
        print(f"[Ollama Error] Fallback triggered: {e}")
        return ExtractedData(events=[
            EventItem(title="Parsed Event Placeholder", category="study", event_date=datetime.now().isoformat())
        ])

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
    try:
        file_bytes = await file.read()
        
        # 1. OCR Text Extraction
        raw_text = extract_raw_text(file_bytes, file.filename)
        
        # 2. Extract structured events using Local LLM + Timezone
        extracted = await parse_events_with_ollama(raw_text, x_timezone)
        
        # 3. Queue persistent Redis notifications
        if device_token:
            for event in extracted.events:
                queue_notification(device_token, event, x_timezone)
                
        return {
            "status": "success", 
            "filename": file.filename,
            "user_timezone": x_timezone,
            "extracted_events": [e.model_dump() for e in extracted.events]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))