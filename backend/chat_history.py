from backend.profiles import current_user_id


def save_chat_turn(
    client,
    student_message: str,
    assistant_reply: str,
    *,
    access_token: str | None = None,
) -> None:
    if access_token is None:
        user_id = current_user_id(client)
    else:
        response = client.auth.get_user(access_token)
        if response is None or response.user is None:
            raise ValueError("Sign in before saving a chat turn.")
        user_id = str(response.user.id)
        client.postgrest.auth(access_token)

    client.table("chat_turns").insert({
        "user_id": user_id,
        "student_message": student_message,
        "assistant_reply": assistant_reply,
    }).execute()

def load_chat_turns(client):
    result = (
        client.table("chat_turns")
        .select("student_message, assistant_reply, created_at")
        .order("created_at", desc=True)
        .order("id", desc=True)
        .limit(10)
        .execute()
    )
    return list(reversed(result.data))