"""Chat router: Trinket's companion chatbot.

Contract: POST {"message": str} -> {"reply": str}, with a Supabase
bearer token in the Authorization header (same check as /profiles/me).
Missing or invalid tokens get 401, so only signed-in users can spend the
shared Groq quota.

Replies come from Groq's hosted Qwen model (OpenAI-compatible chat API)
when GROQ_API_KEY is set. If the key is missing or Groq fails (timeout,
rate limit, bad response), the endpoint falls back to the original echo
reply so the demo never breaks.
"""

import logging
import os

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from . import config  # noqa: F401  (loads root + backend .env)
from .routers.profiles import ProfileContext, get_profile_context

logger = logging.getLogger(__name__)
router = APIRouter()

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"
GROQ_TIMEOUT_SECONDS = 20.0
MAX_REPLY_TOKENS = 300

PERSONA_PROMPT = (
    "You are Trinket, a warm, upbeat study companion inside a gamified "
    "productivity app for high school and college students (ages 15-22). "
    "Act like a friendly coach: help students break assignments into small "
    "steps, encourage them to start, and celebrate progress. Keep replies "
    "short (2-4 sentences), casual, and a little playful. Stay appropriate "
    "for teens. Don't do their homework for them; guide them instead. If a "
    "student seems seriously upset or unsafe, respond kindly and encourage "
    "them to talk to a trusted adult or a crisis line such as 988 (US)."
)


class ChatMessage(BaseModel):
    message: str = Field(max_length=2000)


def echo_reply(message: str) -> str:
    return f"Trinket received your message: {message}"


def _make_client() -> httpx.AsyncClient:
    # Separate function so tests can swap in a fake transport.
    return httpx.AsyncClient(timeout=GROQ_TIMEOUT_SECONDS)


async def ask_groq(message: str, api_key: str) -> str:
    payload = {
        "model": os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL,
        "messages": [
            {"role": "system", "content": PERSONA_PROMPT},
            {"role": "user", "content": message},
        ],
        "max_tokens": MAX_REPLY_TOKENS,
        "temperature": 0.8,
    }
    async with _make_client() as client:
        response = await client.post(
            GROQ_CHAT_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
    response.raise_for_status()
    reply = response.json()["choices"][0]["message"]["content"].strip()
    if not reply:
        raise ValueError("Groq returned an empty reply")
    return reply


@router.post("/api/v1/chat")
async def chat(
    request: ChatMessage,
    ctx: ProfileContext = Depends(get_profile_context),
):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return {"reply": echo_reply(request.message)}
    try:
        return {"reply": await ask_groq(request.message, api_key)}
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        logger.warning(
            "Groq chat failed for user %s; using echo fallback",
            ctx.user_id,
            exc_info=True,
        )
        return {"reply": echo_reply(request.message)}


# Legacy alias kept for the incoming caller; hidden from the schema.
@router.post("/chat", include_in_schema=False)
async def chat_legacy(
    request: ChatMessage,
    ctx: ProfileContext = Depends(get_profile_context),
):
    return await chat(request, ctx)
