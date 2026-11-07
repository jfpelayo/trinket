"""HTTP bridge for Supabase user profiles.

GET  /api/v1/profiles/me - read the caller's profile row.
PUT  /api/v1/profiles/me - upsert the caller's profile row.

Every request builds its own Supabase client with the publishable/anon
key (SUPABASE_KEY), verifies the bearer JWT via auth.get_user(), and
scopes PostgREST to that same bearer token so RLS applies. The service
key is never used here.
"""

import os
from datetime import time
from typing import Literal, Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from postgrest.exceptions import APIError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from supabase import ClientOptions, SupabaseException, create_client
from supabase_auth.errors import AuthError, AuthRetryableError

from .. import config  # noqa: F401  (loads root + backend .env)
from .. import profiles as profile_helpers

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


class ProfileContext:
    """Per-request verified auth context: request-scoped client + user id."""

    def __init__(self, client, user_id: str):
        self.client = client
        self.user_id = user_id


def get_profile_context(
    authorization: Optional[str] = Header(None),
):
    """Verify the bearer token and yield a request-scoped client."""
    parts = (authorization or "").split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise _unauthorized("Missing or malformed bearer token")
    token = parts[1]

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Supabase is not configured")

    options = ClientOptions(
        auto_refresh_token=False,
        persist_session=False,
    )
    try:
        client = create_client(url, key, options)
    except (SupabaseException, ValueError) as exc:
        raise HTTPException(
            status_code=503, detail="Supabase is not configured"
        ) from exc
    try:
        try:
            response = client.auth.get_user(token)
        except AuthRetryableError as exc:
            raise HTTPException(
                status_code=503, detail="Auth service unavailable"
            ) from exc
        except AuthError as exc:
            raise _unauthorized("Invalid or expired token") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Auth service unavailable"
            ) from exc

        if not response or not response.user:
            raise _unauthorized("Invalid or expired token")

        # Scope PostgREST to the verified user token so RLS applies.
        client.postgrest.auth(token)
        yield ProfileContext(client=client, user_id=str(response.user.id))
    finally:
        try:
            client.postgrest.aclose()
        except Exception:
            pass
        try:
            client.auth.close()
        except Exception:
            pass


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str
    timezone: Optional[str] = None
    avatar_url: Optional[str] = None
    pronouns: Optional[str] = Field(None, min_length=1, max_length=100)
    communication_style: Optional[
        Literal["concise", "detailed", "balanced"]
    ] = None
    motivation_style: Optional[
        Literal["encouragement", "accountability", "small_challenges"]
    ] = None
    preferred_study_time: Optional[time] = None
    focus_session_minutes: Optional[int] = Field(None, ge=5, le=180)
    reminders_enabled: Optional[bool] = None

    @field_validator("display_name")
    @classmethod
    def _name_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name cannot be empty")
        return value

    @field_validator("timezone")
    @classmethod
    def _timezone_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            try:
                ZoneInfo(value)
            except Exception:
                raise ValueError("timezone must be a valid IANA name")
        return value

    @field_validator("preferred_study_time")
    @classmethod
    def _time_naive(cls, value: Optional[time]) -> Optional[time]:
        # Column is `time without time zone`; reject tz-aware input.
        if value is not None and value.tzinfo is not None:
            raise ValueError("preferred_study_time must not include a timezone")
        return value

    @field_validator("reminders_enabled", mode="before")
    @classmethod
    def _reminders_not_null(cls, value):
        if value is None:
            raise ValueError("reminders_enabled cannot be null")
        return value


@router.get("/me")
def read_profile(ctx: ProfileContext = Depends(get_profile_context)):
    try:
        row = profile_helpers.get_profile(ctx.client, user_id=ctx.user_id)
    except (APIError, httpx.HTTPError) as exc:
        raise HTTPException(
            status_code=502, detail="Profile database error"
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return row


@router.put("/me")
def update_profile(
    body: ProfileUpdate,
    ctx: ProfileContext = Depends(get_profile_context),
):
    preferences = body.model_dump(exclude_unset=True)
    name = preferences.pop("display_name")
    if preferences.get("preferred_study_time") is not None:
        preferences["preferred_study_time"] = preferences[
            "preferred_study_time"
        ].isoformat()
    try:
        rows = profile_helpers.save_profile(
            ctx.client, name, user_id=ctx.user_id, **preferences
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (APIError, httpx.HTTPError) as exc:
        raise HTTPException(
            status_code=502, detail="Profile database error"
        ) from exc
    if not rows:
        raise HTTPException(status_code=502, detail="Profile database error")
    return rows[0] if isinstance(rows, list) else rows
