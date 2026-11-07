"""Offline tests for the standalone extraction worker (no network, no model)."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

import httpx

from backend import document_worker as worker
from backend import extraction

JOB = {"id": "doc-1", "lease_token": "lease-1", "raw_text": "Midterm March 2",
       "timezone": "America/Los_Angeles", "user_id": "user-a"}


class FakeRpcClient:
    def __init__(self, jobs=None, complete=True, error=None):
        self.jobs = [JOB] if jobs is None else jobs
        self.complete = complete
        self.error = error
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))

        def execute():
            if self.error and name == self.error[0]:
                raise self.error[1]
            if name == "claim_document_job":
                return SimpleNamespace(data=self.jobs)
            return SimpleNamespace(data=self.complete)

        return SimpleNamespace(execute=execute)


def events(*dates):
    return extraction.ExtractedData(events=[
        extraction.EventItem(title="Midterm", category="deadline", event_date=d)
        for d in dates
    ])


class TestConversion(unittest.TestCase):
    def test_date_only_is_local_midnight_all_day(self):
        row = worker.to_event_row(events("2026-12-01").events[0], "America/Los_Angeles")
        self.assertEqual((row["starts_at"], row["all_day"]),
                         ("2026-12-01T08:00:00+00:00", True))

    def test_naive_datetime_uses_document_timezone(self):
        row = worker.to_event_row(events("2026-07-01T09:30:00").events[0], "America/Los_Angeles")
        self.assertEqual((row["starts_at"], row["all_day"]),
                         ("2026-07-01T16:30:00+00:00", False))

    def test_aware_datetime_is_not_reinterpreted(self):
        row = worker.to_event_row(events("2026-07-01T09:30:00+02:00").events[0], "America/Los_Angeles")
        self.assertEqual(row["starts_at"], "2026-07-01T07:30:00+00:00")

    def test_dst_gap_and_overlap_are_rejected(self):
        for value in ("2026-03-08T02:30:00", "2026-11-01T01:30:00"):
            with self.assertRaises(worker.InvalidEventDates, msg=value):
                worker.to_event_row(events(value).events[0], "America/Los_Angeles")

    def test_blank_title_and_too_many_events_rejected(self):
        blank = extraction.EventItem(title="  ", category="other", event_date="2026-12-01")
        with self.assertRaises(worker.InvalidEventDates):
            worker.to_event_row(blank, "UTC")
        with self.assertRaises(worker.InvalidEventDates):
            worker.to_event_rows(events(*["2026-12-01"] * 501).events, "UTC")


class TestProcessOne(unittest.TestCase):
    def run_one(self, client, model=None):
        model = model or mock.AsyncMock(return_value=events("2026-12-01T10:00:00"))
        with mock.patch.object(extraction, "parse_events_with_ollama", model):
            return asyncio.run(worker.process_one(client)), model

    def test_idle_queue_does_no_work(self):
        client = FakeRpcClient(jobs=[])
        worked, model = self.run_one(client)
        self.assertFalse(worked)
        model.assert_not_called()
        self.assertEqual([c[0] for c in client.calls], ["claim_document_job"])

    def test_success_completes_with_lease_and_utc_rows(self):
        client = FakeRpcClient()
        worked, model = self.run_one(client)
        self.assertTrue(worked)
        model.assert_awaited_once_with(JOB["raw_text"], JOB["timezone"])
        name, params = client.calls[-1]
        self.assertEqual(name, "complete_document_job")
        self.assertEqual(params["p_document_id"], "doc-1")
        self.assertEqual(params["p_lease_token"], "lease-1")
        self.assertEqual(params["p_events"], [{
            "title": "Midterm", "category": "deadline",
            "starts_at": "2026-12-01T18:00:00+00:00", "all_day": False}])

    def test_lost_lease_is_not_retried(self):
        client = FakeRpcClient(complete=False)
        self.run_one(client)
        self.assertEqual([c[0] for c in client.calls],
                         ["claim_document_job", "complete_document_job"])

    def test_model_failures_mark_extraction_failed(self):
        for error in (extraction.EventExtractionError("x"), asyncio.TimeoutError()):
            client = FakeRpcClient()
            self.run_one(client, mock.AsyncMock(side_effect=error))
            self.assertEqual(client.calls[-1],
                             ("fail_document_job", {"p_document_id": "doc-1",
                                                    "p_lease_token": "lease-1",
                                                    "p_error_code": "extraction_failed"}))

    def test_ambiguous_dates_mark_invalid_dates(self):
        client = FakeRpcClient()
        self.run_one(client, mock.AsyncMock(return_value=events("2026-03-08T02:30:00")))
        self.assertEqual(client.calls[-1][1]["p_error_code"], "invalid_dates")

    def test_model_timeout_is_below_database_lease(self):
        self.assertLess(worker.MODEL_TIMEOUT_SECONDS, 15 * 60)


class TestRunLoop(unittest.TestCase):
    def test_database_failure_is_survived(self):
        client = FakeRpcClient(error=("claim_document_job", httpx.ConnectError("down")))
        with self.assertLogs("backend.document_worker", "WARNING") as logs:
            asyncio.run(worker.run(client, once=True))
        self.assertNotIn(JOB["raw_text"], "\n".join(logs.output))

    def test_ambiguous_completion_does_not_mark_failed(self):
        client = FakeRpcClient(error=("complete_document_job", httpx.ReadTimeout("?")))
        with mock.patch.object(extraction, "parse_events_with_ollama",
                               mock.AsyncMock(return_value=events("2026-12-01"))):
            asyncio.run(worker.run(client, once=True))
        self.assertNotIn("fail_document_job", [c[0] for c in client.calls])

    def test_missing_service_credentials_exit_without_echo(self):
        with mock.patch.dict("os.environ", {"SUPABASE_URL": "", "SUPABASE_SERVICE_KEY": ""}):
            with self.assertRaises(SystemExit) as exit_info:
                worker.service_client()
        self.assertIn("must be set", str(exit_info.exception))


if __name__ == "__main__":
    unittest.main()
