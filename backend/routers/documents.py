"""Document uploads and review.

POST stores extracted text as a `processing` document and returns 202; the
standalone worker (`backend.document_worker`) runs the model and saves draft
events. Confirmation records the review only; reminders are Phase 4.
"""

from typing import Optional
from uuid import UUID

import pytz
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from ..extraction import read_upload_text
from ._db import DOCUMENT_COLUMNS, EVENT_FIELDS, not_found, public_document, run_query
from .profiles import ProfileContext, get_profile_context

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

MAX_FILENAME_CHARS = 255


def resolve_timezone(ctx: ProfileContext, header_timezone: Optional[str]) -> str:
    """Profile timezone wins; the client header is only a fallback."""
    rows = run_query(
        lambda: ctx.client.table("profiles").select("timezone")
        .eq("id", ctx.user_id).execute().data
    )
    timezone = (rows[0].get("timezone") if rows else None) or header_timezone or "UTC"
    try:
        pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError as exc:
        raise HTTPException(status_code=422, detail="Unknown timezone") from exc
    return timezone


def display_filename(filename: Optional[str]) -> str:
    name = "".join(ch for ch in (filename or "") if ch.isprintable()).strip()
    name = name.replace("/", "_").replace("\\", "_")
    if not name:
        raise HTTPException(status_code=422, detail="Upload needs a file name")
    return name[-MAX_FILENAME_CHARS:]


@router.post("", status_code=202)
async def create_document(
    file: UploadFile = File(...),
    x_timezone: Optional[str] = Header(None),
    ctx: ProfileContext = Depends(get_profile_context),
):
    filename = display_filename(file.filename)
    raw_text = await read_upload_text(file)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No text found in document")
    timezone = await run_in_threadpool(resolve_timezone, ctx, x_timezone)
    rows = await run_in_threadpool(
        run_query,
        lambda: ctx.client.table("documents").insert({
            "user_id": ctx.user_id,
            "filename": filename,
            "mime_type": file.content_type,
            "raw_text": raw_text,
            "timezone": timezone,
        }).execute().data,
    )
    if not rows:
        raise HTTPException(status_code=502, detail="Database error")
    document = public_document(rows[0])
    return JSONResponse(
        status_code=202,
        content={"document": document, "events": []},
        headers={"Location": f"/api/v1/documents/{document['id']}"},
    )


@router.get("")
def list_documents(ctx: ProfileContext = Depends(get_profile_context)):
    rows = run_query(
        lambda: ctx.client.table("documents").select(DOCUMENT_COLUMNS)
        .eq("user_id", ctx.user_id).order("created_at", desc=True).order("id")
        .limit(100).execute().data
    )
    return {"documents": [public_document(row) for row in rows]}


@router.get("/{document_id}")
def get_document(
    document_id: UUID, ctx: ProfileContext = Depends(get_profile_context)
):
    rows = run_query(
        lambda: ctx.client.table("documents").select(DOCUMENT_COLUMNS)
        .eq("user_id", ctx.user_id).eq("id", str(document_id)).execute().data
    )
    if not rows:
        raise not_found("Document")
    events = run_query(
        lambda: ctx.client.table("events").select(EVENT_FIELDS)
        .eq("user_id", ctx.user_id).eq("document_id", str(document_id))
        .order("starts_at").order("id").execute().data
    )
    return {"document": public_document(rows[0]), "events": events}


@router.post("/{document_id}/confirm")
def confirm_document(
    document_id: UUID, ctx: ProfileContext = Depends(get_profile_context)
):
    rows = run_query(
        lambda: ctx.client.rpc(
            "confirm_document", {"p_document_id": str(document_id)}
        ).execute().data,
        conflicts={"P0001": "Document is not ready for confirmation"},
    )
    if not rows:
        raise not_found("Document")
    return {"document": public_document(rows[0]), "reminders_scheduled": False}
