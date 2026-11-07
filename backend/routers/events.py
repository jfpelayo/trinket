"""Calendar events: list, manual add, edit, confirm, delete.

Confirming records the user's review only; reminder scheduling is Phase 4.
"""

from typing import Annotated, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field

from ._db import EVENT_FIELDS, not_found, run_query
from .profiles import ProfileContext, get_profile_context

router = APIRouter(prefix="/api/v1/events", tags=["events"])

Category = Literal["meeting", "study", "deadline", "other"]
MAX_REMINDER_OFFSET_MINUTES = 7 * 24 * 60


def _title(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("title cannot be empty")
    return value


Title = Annotated[str, Field(max_length=300), AfterValidator(_title)]


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    category: Category
    starts_at: AwareDatetime
    all_day: bool = False
    reminder_offset_minutes: int = Field(15, ge=0, le=MAX_REMINDER_OFFSET_MINUTES)


class EventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[Title] = None
    category: Optional[Category] = None
    starts_at: Optional[AwareDatetime] = None
    all_day: Optional[bool] = None
    reminder_offset_minutes: Optional[int] = Field(
        None, ge=0, le=MAX_REMINDER_OFFSET_MINUTES
    )
    status: Optional[Literal["draft", "dismissed"]] = None


def _row_payload(model: BaseModel, exclude_unset: bool) -> dict:
    payload = model.model_dump(mode="json", exclude_unset=exclude_unset)
    if None in payload.values():
        raise HTTPException(status_code=422, detail="Fields cannot be null")
    return payload


def _get_event(ctx: ProfileContext, event_id: UUID) -> dict:
    rows = run_query(
        lambda: ctx.client.table("events").select(EVENT_FIELDS)
        .eq("user_id", ctx.user_id).eq("id", str(event_id)).execute().data
    )
    if not rows:
        raise not_found("Event")
    return rows[0]


@router.get("")
def list_events(
    from_: Optional[AwareDatetime] = Query(None, alias="from"),
    to: Optional[AwareDatetime] = None,
    status: Optional[Literal["draft", "confirmed", "dismissed"]] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10_000),
    ctx: ProfileContext = Depends(get_profile_context),
):
    if from_ and to and from_ >= to:
        raise HTTPException(status_code=422, detail="'from' must be before 'to'")

    def query():
        q = ctx.client.table("events").select(EVENT_FIELDS).eq("user_id", ctx.user_id)
        if from_:
            q = q.gte("starts_at", from_.isoformat())
        if to:
            q = q.lt("starts_at", to.isoformat())
        if status:
            q = q.eq("status", status)
        return q.order("starts_at").order("id").range(offset, offset + limit - 1).execute().data

    return {"events": run_query(query)}


@router.post("", status_code=201)
def create_event(
    body: EventCreate, ctx: ProfileContext = Depends(get_profile_context)
):
    payload = {**_row_payload(body, exclude_unset=False), "user_id": ctx.user_id}
    rows = run_query(lambda: ctx.client.table("events").insert(payload).execute().data)
    if not rows:
        raise HTTPException(status_code=502, detail="Database error")
    return rows[0]


@router.patch("/{event_id}")
def update_event(
    event_id: UUID,
    body: EventUpdate,
    ctx: ProfileContext = Depends(get_profile_context),
):
    payload = _row_payload(body, exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=422, detail="No fields to update")
    rows = run_query(
        lambda: ctx.client.table("events").update(payload)
        .eq("user_id", ctx.user_id).eq("id", str(event_id)).execute().data
    )
    if not rows:
        raise not_found("Event")
    return rows[0]


@router.post("/{event_id}/confirm")
def confirm_event(event_id: UUID, ctx: ProfileContext = Depends(get_profile_context)):
    event = _get_event(ctx, event_id)
    if event["status"] == "dismissed":
        raise HTTPException(status_code=409, detail="Dismissed events cannot be confirmed")
    if event["status"] != "confirmed":
        rows = run_query(
            lambda: ctx.client.table("events").update({"status": "confirmed"})
            .eq("user_id", ctx.user_id).eq("id", str(event_id))
            .neq("status", "dismissed").execute().data
        )
        if not rows:
            raise HTTPException(status_code=409, detail="Event changed; reload and retry")
        event = rows[0]
    return {"event": event, "reminders_scheduled": False}


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: UUID, ctx: ProfileContext = Depends(get_profile_context)):
    rows = run_query(
        lambda: ctx.client.table("events").delete()
        .eq("user_id", ctx.user_id).eq("id", str(event_id)).execute().data
    )
    if not rows:
        raise not_found("Event")
    return Response(status_code=204)
