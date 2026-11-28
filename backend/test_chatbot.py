from fastapi.testclient import TestClient

from backend.chatbot import app


def test_chat_echoes_hello():
    client = TestClient(app)
    response = client.post("/chat", json={"message": "Hello"})

    assert response.status_code == 200
    assert response.json() == {"reply": "Trinket received your message: Hello"}

def test_chat_rejects_blank_message():
    client = TestClient(app)
    response = client.post("/chat", json={"message": "   "})

    assert response.status_code == 422
    assert response.json() == {"detail": "Please enter a message."}

def test_chat_requires_message_field():
    client = TestClient(app)
    response = client.post("/chat", json={})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "message"]