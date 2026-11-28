# Trinket chatbot backend

The FastAPI endpoint `POST /chat` accepts a student message and
returns a temporary echo reply. Blank messages and requests missing
the `message` field return HTTP 422.

## Run the chatbot

From the project root with the Python virtual environment active:

    python -m uvicorn backend.chatbot:app --reload

Open http://127.0.0.1:8000/docs to try the endpoint.

## Try a chat request

Open http://127.0.0.1:8000/docs. Expand **POST /chat**, click
**Try it out**, paste this request body, and click **Execute**.

```json
{"message": "Hello"}
```

Under **Server response**, expect HTTP 200 and this JSON:

```json
{"reply": "Trinket received your message: Hello"}
```

To check validation, send `{"message": " "}`. Expect HTTP 422
with `{"detail": "Please enter a message."}`.

## Run the tests

    python -m pytest backend/test_chatbot.py -q

## Set up on macOS

Open Terminal in the project root, the folder that contains `backend`.
Run these commands one at a time:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi uvicorn pytest httpx
```

If you open a new Terminal window later, return to the project root
and run `source .venv/bin/activate` again.
