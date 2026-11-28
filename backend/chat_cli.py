import httpx

message = input("You: ")
try:
    response = httpx.post(
        "http://127.0.0.1:8000/chat",
        json={"message": message},
    )
except httpx.ConnectError:
    print("Could not connect to Trinket. Start the backend and try again.")
    raise SystemExit(1)
if response.status_code == 422:
    print(f"Trinket: {response.json()['detail']}")
    raise SystemExit(1)

response.raise_for_status()
print(f"Trinket: {response.json()['reply']}")