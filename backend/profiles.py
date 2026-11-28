
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


def connect():
    # Read the .env file next to this Python file.
    load_dotenv(Path(__file__).parent / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Set SUPABASE_URL and SUPABASE_KEY in backend/.env")

    return create_client(url, key)


def current_user_id(client):
    response = client.auth.get_user()

    if not response or not response.user:
        raise ValueError("Sign in before accessing a profile.")

    return str(response.user.id)


def save_profile(client, display_name, **preferences):
    name = display_name.strip()

    if not name:
        raise ValueError("Display name cannot be empty.")

    allowed = {
        "timezone",
        "avatar_url",
        "pronouns",
        "communication_style",
        "motivation_style",
        "preferred_study_time",
        "focus_session_minutes",
        "reminders_enabled",
    }

    unknown = set(preferences) - allowed
    if unknown:
        raise ValueError(f"Unknown profile fields: {sorted(unknown)}")

    if preferences.get("timezone") is not None:
        from zoneinfo import ZoneInfo

        ZoneInfo(preferences["timezone"])

    response = (
        client.table("profiles")
        .upsert(
            {
                "id": current_user_id(client),
                "display_name": name,
                **preferences,
            },
            on_conflict="id",
        )
        .execute()
    )

    return response.data

def get_profile(client):
    response = (
        client.table("profiles")
        .select("*")
        .eq("id", current_user_id(client))
        .execute()
    )

    return response.data[0] if response.data else None