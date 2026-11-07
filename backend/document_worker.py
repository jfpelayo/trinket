"""Standalone extraction worker for a team-controlled machine.

Run from the repository root:
    venv/bin/python -m backend.document_worker          # poll forever
    venv/bin/python -m backend.document_worker --once   # one claim attempt

Uploads are stored as `processing` documents. This worker claims one with a
15-minute database lease, runs the local model, and saves draft events and
the `review` status in one transaction. A crashed or stalled job is reclaimed
after its lease expires and fails explicitly after three attempts. Only this
process uses SUPABASE_SERVICE_KEY; it never stores user tokens or logs
document text.
"""

import argparse
import asyncio
import logging
import os
from datetime import date, datetime, time
from typing import Dict, List

import httpx
import pytz
from postgrest.exceptions import APIError
from supabase import ClientOptions, create_client

from . import extraction

logger = logging.getLogger("backend.document_worker")

MODEL_TIMEOUT_SECONDS = 840  # stays below the 900-second database lease
IDLE_SECONDS = 2.0
MAX_EVENTS = 500
MAX_TITLE_CHARS = 300


class InvalidEventDates(Exception):
    """An extracted date is ambiguous or does not exist in the user's timezone."""


def to_event_row(event: extraction.EventItem, timezone: str) -> Dict:
    """Convert a model event into a UTC row; never guess ambiguous local times."""
    title = event.title.strip()
    if not title or len(title) > MAX_TITLE_CHARS:
        raise InvalidEventDates("invalid title")
    zone = pytz.timezone(timezone)
    value = event.event_date.strip()
    all_day = len(value) == 10
    try:
        if all_day:
            local = datetime.combine(date.fromisoformat(value), time.min)
            starts_at = zone.localize(local, is_dst=None)
        else:
            parsed = datetime.fromisoformat(value)
            starts_at = (
                zone.localize(parsed, is_dst=None) if parsed.tzinfo is None else parsed
            )
    except (ValueError, pytz.exceptions.InvalidTimeError) as exc:
        raise InvalidEventDates(str(exc)) from exc
    return {
        "title": title,
        "category": event.category,
        "starts_at": starts_at.astimezone(pytz.utc).isoformat(),
        "all_day": all_day,
    }


def to_event_rows(events: List[extraction.EventItem], timezone: str) -> List[Dict]:
    if len(events) > MAX_EVENTS:
        raise InvalidEventDates("too many events")
    return [to_event_row(event, timezone) for event in events]


def service_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(
        url, key, ClientOptions(auto_refresh_token=False, persist_session=False)
    )


def _rpc(client, name: str, params: Dict = None):
    return client.rpc(name, params or {}).execute().data


async def process_one(client) -> bool:
    """Claim and process one document. Returns False when the queue is empty."""
    jobs = await asyncio.to_thread(_rpc, client, "claim_document_job")
    if not jobs:
        return False
    job = jobs[0]
    lease = {"p_document_id": job["id"], "p_lease_token": job["lease_token"]}
    try:
        extracted = await asyncio.wait_for(
            extraction.parse_events_with_ollama(job["raw_text"], job["timezone"]),
            MODEL_TIMEOUT_SECONDS,
        )
        rows = to_event_rows(extracted.events, job["timezone"])
    except InvalidEventDates:
        outcome = await asyncio.to_thread(
            _rpc, client, "fail_document_job", {**lease, "p_error_code": "invalid_dates"}
        )
        logger.warning("document %s failed: invalid dates (recorded=%s)", job["id"], outcome)
        return True
    except (extraction.EventExtractionError, extraction.DocumentInputError,
            asyncio.TimeoutError, pytz.UnknownTimeZoneError):
        outcome = await asyncio.to_thread(
            _rpc, client, "fail_document_job",
            {**lease, "p_error_code": "extraction_failed"},
        )
        logger.warning("document %s failed: extraction (recorded=%s)", job["id"], outcome)
        return True

    saved = await asyncio.to_thread(
        _rpc, client, "complete_document_job", {**lease, "p_events": rows}
    )
    if saved:
        logger.info("document %s ready for review (%d events)", job["id"], len(rows))
    else:
        logger.warning("document %s lease lost; result discarded", job["id"])
    return True


async def run(client, once: bool) -> None:
    while True:
        try:
            worked = await process_one(client)
        except (APIError, httpx.HTTPError):
            # Ambiguous outcomes are left to the lease: the database either
            # committed the result or will let another attempt reclaim it.
            logger.warning("database unavailable; retrying", exc_info=False)
            worked = False
        if once:
            return
        if not worked:
            await asyncio.sleep(IDLE_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--once", action="store_true", help="claim at most one job")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = service_client()
    try:
        asyncio.run(run(client, args.once))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            client.postgrest.session.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
