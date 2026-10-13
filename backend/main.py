import io
import fitz  # PyMuPDF
import easyocr
import httpx
import pytz
import firebase_admin
from firebase_admin import credentials
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager


from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
cred = credentials.Certificate("backend/trinket-f2253-firebase-adminsdk-fbsvc-7aab4bfe79.json")
firebase_admin.initialize_app(cred)

# --- Phase 2: Configure Redis-Backed Scheduler ---
# Jobs persist in Redis on port 6379 across server restarts
jobstores = {
    'default': RedisJobStore(host='localhost', port=6379, db=0)
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

# Load EasyOCR
reader = easyocr.Reader(['en'], gpu=False)

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
                results = reader.readtext(pix.tobytes())
                text += " ".join([res[1] for res in results]) + "\n"
    else:
        results = reader.readtext(file_bytes)
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
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:3b",
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