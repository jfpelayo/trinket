from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


# Defines what the frontend sends us
class ChatMessage(BaseModel):
    message: str


# Frontend sends a POST request here
@app.post("/chat")
def chat(request: ChatMessage):

    user_message = request.message

    # Temporary response until AI model is connected
    ai_reply = f"Trinket received your message: {user_message}"

    # Send AI response back to frontend
    return {
        "reply": ai_reply
    }
