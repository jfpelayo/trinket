"""Chat router.

Stub echo endpoint preserved from the incoming chatbot branch; real
inference is deferred beyond launch scope. Contract: POST {"message": str} ->
{"reply": "Trinket received your message: <message>"}. No external
model calls are made.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ChatMessage(BaseModel):
    message: str


@router.post("/api/v1/chat")
def chat(request: ChatMessage):
    ai_reply = f"Trinket received your message: {request.message}"
    return {"reply": ai_reply}


# Legacy alias kept for the incoming caller; hidden from the schema.
@router.post("/chat", include_in_schema=False)
def chat_legacy(request: ChatMessage):
    return chat(request)
