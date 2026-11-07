"""Expo push-token registration. Delivery itself is Phase 4."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from ._db import not_found, run_query
from .profiles import ProfileContext, get_profile_context

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

TOKEN_CONFLICT = "Push token is already registered"


class DeviceRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(
        max_length=255, pattern=r"^Expo(nent)?PushToken\[[A-Za-z0-9_-]+\]$"
    )
    platform: Literal["ios", "android"]


@router.post("", status_code=201)
def register_device(
    body: DeviceRegistration, ctx: ProfileContext = Depends(get_profile_context)
):
    rows = run_query(
        lambda: ctx.client.table("device_tokens").upsert(
            {"user_id": ctx.user_id, "token": body.token, "platform": body.platform},
            on_conflict="token",
        ).execute().data,
        conflicts={"23505": TOKEN_CONFLICT, "42501": TOKEN_CONFLICT},
    )
    if not rows:
        raise HTTPException(status_code=502, detail="Database error")
    return rows[0]


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: UUID, ctx: ProfileContext = Depends(get_profile_context)):
    rows = run_query(
        lambda: ctx.client.table("device_tokens").delete()
        .eq("user_id", ctx.user_id).eq("id", str(device_id)).execute().data
    )
    if not rows:
        raise not_found("Device")
    return Response(status_code=204)
