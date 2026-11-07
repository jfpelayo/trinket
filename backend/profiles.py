"""Supabase profile helpers shared by the HTTP router and manual scripts.

Works both as an importable module (backend/ on sys.path) and when the
manual scripts are run directly from the backend/ directory.
"""

import os
from zoneinfo import ZoneInfo

from supabase import create_client

if __package__:
    from . import config  # noqa: F401  (loads root + backend .env)
else:  # manual scripts run from backend/ import this flat
    import config  # noqa: F401


def connect():
    """Client for the interactive scripts: session-based auth."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Set SUPABASE_URL and SUPABASE_KEY in .env or backend/.env")

    return create_client(url, key)


def current_user_id(client):
    response = client.auth.get_user()

    if not response or not response.user:
        raise ValueError("Sign in before accessing a profile.")

    return str(response.user.id)


def save_profile(client, display_name, *, user_id=None, **preferences):
    """Upsert a profile row.

    user_id: verified user id supplied by the HTTP layer. When omitted,
    falls back to the client's signed-in session (manual scripts).
    """
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
        ZoneInfo(preferences["timezone"])

    verified_user_id = user_id if user_id is not None else current_user_id(client)

    response = (
        client.table("profiles")
        .upsert(
            {
                "id": verified_user_id,
                "display_name": name,
                **preferences,
            },
            on_conflict="id",
        )
        .execute()
    )

    return response.data


def get_profile(client, *, user_id=None):
    """Select a profile row.

    user_id: verified user id supplied by the HTTP layer. When omitted,
    falls back to the client's signed-in session (manual scripts).
    """
    verified_user_id = user_id if user_id is not None else current_user_id(client)

    response = (
        client.table("profiles")
        .select("*")
        .eq("id", verified_user_id)
        .execute()
    )

    return response.data[0] if response.data else None
