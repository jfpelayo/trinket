from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth.errors import AuthApiError

from backend.chat_history import load_chat_turns, save_chat_turn
from backend.profiles import connect
from pydantic import BaseModel
from datetime import datetime
from typing import Literal

app = FastAPI()
chat_auth = HTTPBearer(auto_error=False)


# Defines what the frontend sends us
class ChatMessage(BaseModel):
    message: str

class ChatReply(BaseModel):
    reply: str

class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime

# Frontend sends a POST request here
@app.post("/chat", response_model=ChatReply)
def chat(
    request: ChatMessage,
    credentials: HTTPAuthorizationCredentials | None = Depends(chat_auth),
):
    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=422, detail="Please enter a message.")

    ai_reply = f"Trinket received your message: {user_message}"

    if credentials is not None:
        try:
            save_chat_turn(
                connect(),
                user_message,
                ai_reply,
                access_token=credentials.credentials,
            )
        except AuthApiError as exc:
            if exc.status in (401, 403):
                raise HTTPException(
                    status_code=401, detail="Please sign in again."
                ) from exc
            raise

    return {"reply": ai_reply}

@app.get("/chat/history", response_model=list[ChatHistoryMessage])
def chat_history(
    credentials: HTTPAuthorizationCredentials | None = Depends(chat_auth),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Please sign in.")

    client = connect()
    token = credentials.credentials
    try:
        account = client.auth.get_user(token)
    except AuthApiError as exc:
        if exc.status in (401, 403):
            raise HTTPException(
                status_code=401, detail="Please sign in again."
            ) from exc
        raise

    if account is None or account.user is None:
        raise HTTPException(status_code=401, detail="Please sign in again.")

    client.postgrest.auth(token)

    messages = []
    for turn in load_chat_turns(client):
        messages.extend([
            {"role": "user", "text": turn["student_message"],
             "created_at": turn["created_at"]},
            {"role": "assistant", "text": turn["assistant_reply"],
             "created_at": turn["created_at"]},
        ])

    return messages
