"""Shared helpers for the user-scoped Supabase routers.

Every query runs on the request-scoped client from `get_profile_context`,
so RLS applies with the caller's own token; routers still filter by the
verified user id as defense in depth.
"""

from typing import Callable, Dict, TypeVar

import httpx
from fastapi import HTTPException
from postgrest.exceptions import APIError

T = TypeVar("T")

DOCUMENT_FIELDS = (
    "id", "user_id", "filename", "mime_type", "status", "timezone",
    "error_code", "created_at", "updated_at",
)
DOCUMENT_COLUMNS = ",".join(DOCUMENT_FIELDS)
EVENT_FIELDS = (
    "id,user_id,document_id,title,category,starts_at,all_day,source,status,"
    "reminder_offset_minutes,created_at,updated_at"
)


def public_document(row: Dict) -> Dict:
    """Drop raw text and worker lease fields before returning a document."""
    return {field: row.get(field) for field in DOCUMENT_FIELDS}


def run_query(query: Callable[[], T], conflicts: Dict[str, str] = None) -> T:
    """Execute a PostgREST call, mapping failures to sanitized HTTP errors."""
    try:
        return query()
    except APIError as exc:
        detail = (conflicts or {}).get(exc.code)
        if detail:
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=502, detail="Database error") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Database error") from exc


def not_found(kind: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{kind} not found")
