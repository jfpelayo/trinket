"""Offline tests for the Phase 3 document, event, and device routes.

Requests go through the pinned supabase SDK; only the HTTP transport is
replaced. The fake PostgREST below does NOT apply RLS, so cross-user
isolation in these tests proves the routes scope every query themselves.
Database triggers, grants, and RPC atomicity are covered separately by
phase3_regression.sql against a disposable PostgreSQL instance.
"""

import json
import os
import unittest
import uuid
from datetime import datetime
from unittest import mock

import httpx
import supabase as supabase_pkg
from fastapi.testclient import TestClient

import backend.main as main
import backend.routers.profiles as profiles_router

TOKENS = {"token-a": "aaaaaaaa-0000-4000-8000-000000000001",
          "token-b": "bbbbbbbb-0000-4000-8000-000000000002"}
USER_A, USER_B = TOKENS["token-a"], TOKENS["token-b"]
SERVICE_KEY = "service-role-secret"
DEFAULTS = {
    "documents": {"status": "processing", "error_code": None, "lease_token": None},
    "events": {"status": "draft", "source": "manual", "document_id": None,
               "all_day": False, "reminder_offset_minutes": 15, "job_id": None},
    "device_tokens": {},
}


def pg_error(status, code, message):
    return httpx.Response(status, json={"code": code, "message": message,
                                        "details": None, "hint": None})


def _compare(value, op, target):
    if op == "eq":
        return str(value).lower() == target.lower() if isinstance(value, bool) else str(value) == target
    if op == "neq":
        return str(value) != target
    left, right = datetime.fromisoformat(value), datetime.fromisoformat(target)
    return left >= right if op == "gte" else left < right


class FakePostgrest:
    """Minimal PostgREST/GoTrue emulator over in-memory tables (no RLS)."""

    def __init__(self):
        self.tables = {name: [] for name in DEFAULTS}
        self.profiles = {}
        self.requests = []
        self.fail = None

    def uid(self, request):
        parts = (request.headers.get("authorization") or "").split()
        return TOKENS.get(parts[1]) if len(parts) == 2 else None

    def rows_matching(self, table, params):
        rows = self.tables[table]
        for key, raw in params.multi_items():
            if key in ("select", "order", "limit", "offset", "on_conflict"):
                continue
            op, target = raw.split(".", 1)
            rows = [r for r in rows if _compare(r.get(key), op, target)]
        return rows

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/auth/v1/user"):
            uid = self.uid(request)
            if uid is None:
                return httpx.Response(403, json={"code": 403, "msg": "invalid JWT"})
            return httpx.Response(200, json={
                "id": uid, "aud": "authenticated", "role": "authenticated",
                "app_metadata": {}, "user_metadata": {},
                "created_at": "2026-01-01T00:00:00Z",
            })
        if self.fail == "transport":
            raise httpx.ConnectError("db down", request=request)
        if self.fail == "error":
            return pg_error(500, "XX000", "secret detail")
        name = path.rsplit("/", 1)[-1]
        params = request.url.params
        if name == "profiles":
            uid = params.get("id", "eq.").split(".", 1)[1]
            tz = self.profiles.get(uid)
            return httpx.Response(200, json=[{"timezone": tz}] if uid in self.profiles else [])
        if "/rpc/" in path:
            return self.confirm(request)
        body = json.loads(request.content) if request.content else None
        if request.method == "GET":
            rows = sorted(self.rows_matching(name, params),
                          key=lambda r: (r.get("starts_at") or r["created_at"], r["id"]))
            offset = int(params.get("offset", 0))
            limit = int(params.get("limit", 1000))
            return httpx.Response(200, json=rows[offset:offset + limit])
        if request.method == "POST":
            return self.insert(name, body, request)
        matched = self.rows_matching(name, params)
        if request.method == "PATCH":
            for row in matched:
                row.update(body)
            return httpx.Response(200, json=matched)
        if request.method == "DELETE":
            self.tables[name] = [r for r in self.tables[name] if r not in matched]
            return httpx.Response(200, json=matched)
        return httpx.Response(405)

    def insert(self, name, body, request):
        if name == "device_tokens":
            existing = [r for r in self.tables[name] if r["token"] == body["token"]]
            if existing:
                if existing[0]["user_id"] != self.uid(request):
                    return pg_error(403, "42501", "rls")
                existing[0].update(body)
                return httpx.Response(201, json=existing)
        row = {**DEFAULTS[name], **body, "id": str(uuid.uuid4()),
               "created_at": datetime.now().isoformat(),
               "updated_at": datetime.now().isoformat()}
        self.tables[name].append(row)
        return httpx.Response(201, json=[row])

    def confirm(self, request):
        doc_id = json.loads(request.content)["p_document_id"]
        docs = [d for d in self.tables["documents"]
                if d["id"] == doc_id and d["user_id"] == self.uid(request)]
        if not docs:
            return httpx.Response(200, json=[])
        if docs[0]["status"] not in ("review", "confirmed"):
            return pg_error(400, "P0001", "document_not_ready")
        for event in self.tables["events"]:
            if event["document_id"] == doc_id and event["status"] == "draft":
                event["status"] = "confirmed"
        docs[0]["status"] = "confirmed"
        return httpx.Response(200, json=docs)


class PersistenceTestCase(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "anon-public-key",
            "SUPABASE_SERVICE_KEY": SERVICE_KEY,
        })
        env.start()
        self.addCleanup(env.stop)
        sched = mock.patch.object(main, "scheduler", mock.MagicMock())
        self.scheduler = sched.start()
        self.addCleanup(sched.stop)
        self.db = FakePostgrest()
        self.keys = []

        def factory(url, key, options=None):
            self.keys.append(key)
            options.httpx_client = httpx.Client(transport=httpx.MockTransport(self.db))
            return supabase_pkg.create_client(url, key, options)

        patcher = mock.patch.object(profiles_router, "create_client", side_effect=factory)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(main.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def auth(self, token="token-a"):
        return {"Authorization": f"Bearer {token}"}

    def rest_requests(self, table):
        return [r for r in self.db.requests if f"/rest/v1/{table}" in r.url.path]

    def seed(self, table, **row):
        self.db.insert(table, row, None)
        return self.db.tables[table][-1]

    def upload(self, text="Midterm on March 2", token="token-a", headers=None, **kw):
        with mock.patch("backend.extraction.extract_raw_text", return_value=text) as ocr, \
                mock.patch("backend.extraction.parse_events_with_ollama") as model:
            r = self.client.post(
                "/api/v1/documents",
                headers={**self.auth(token), **(headers or {})},
                files={"file": kw.get("file", ("syllabus.pdf", b"%PDF", "application/pdf"))},
            )
        model.assert_not_called()
        self.ocr = ocr
        return r


class TestAuthAndValidation(PersistenceTestCase):
    ROUTES = [
        ("post", "/api/v1/documents"), ("get", "/api/v1/documents"),
        ("get", f"/api/v1/documents/{uuid.uuid4()}"),
        ("post", f"/api/v1/documents/{uuid.uuid4()}/confirm"),
        ("get", "/api/v1/events"), ("post", "/api/v1/events"),
        ("patch", f"/api/v1/events/{uuid.uuid4()}"),
        ("post", f"/api/v1/events/{uuid.uuid4()}/confirm"),
        ("delete", f"/api/v1/events/{uuid.uuid4()}"),
        ("post", "/api/v1/devices"), ("delete", f"/api/v1/devices/{uuid.uuid4()}"),
    ]

    def test_every_route_requires_a_valid_bearer_token(self):
        for method, path in self.ROUTES:
            for headers in ({}, {"Authorization": "Bearer bad"}, {"Authorization": "token-a"}):
                r = getattr(self.client, method)(path, headers=headers)
                self.assertEqual(r.status_code, 401, (method, path, headers))
        self.assertEqual(self.rest_requests(""), [])

    def test_http_routes_never_use_the_service_key(self):
        self.upload()
        self.client.get("/api/v1/events", headers=self.auth())
        self.assertTrue(self.keys)
        self.assertNotIn(SERVICE_KEY, self.keys)

    def test_bodies_reject_ownership_and_workflow_fields(self):
        base = {"title": "Quiz", "category": "study", "starts_at": "2026-12-01T10:00:00Z"}
        for extra in ({"user_id": USER_B}, {"document_id": str(uuid.uuid4())},
                      {"source": "extracted"}, {"job_id": "x"}, {"status": "confirmed"}):
            r = self.client.post("/api/v1/events", headers=self.auth(), json={**base, **extra})
            self.assertEqual(r.status_code, 422, extra)
        self.assertEqual(self.db.tables["events"], [])

    def test_event_dates_must_include_a_timezone(self):
        r = self.client.post("/api/v1/events", headers=self.auth(), json={
            "title": "Quiz", "category": "study", "starts_at": "2026-12-01T10:00:00"})
        self.assertEqual(r.status_code, 422)

    def test_database_errors_are_sanitized(self):
        for failure in ("transport", "error"):
            self.db.fail = failure
            r = self.client.get("/api/v1/events", headers=self.auth())
            self.assertEqual(r.status_code, 502)
            self.assertNotIn("secret detail", r.text)


class TestDocuments(PersistenceTestCase):
    def test_upload_persists_processing_document_without_running_model(self):
        r = self.upload()
        self.assertEqual(r.status_code, 202)
        body = r.json()
        doc = self.db.tables["documents"][0]
        self.assertEqual(r.headers["location"], f"/api/v1/documents/{doc['id']}")
        self.assertEqual(body["events"], [])
        self.assertEqual(body["document"]["status"], "processing")
        self.assertEqual(doc["user_id"], USER_A)
        self.assertEqual(doc["raw_text"], "Midterm on March 2")
        self.assertNotIn("raw_text", body["document"])
        self.assertNotIn("lease_token", body["document"])
        sent = json.loads(self.rest_requests("documents")[0].content)
        self.assertEqual(set(sent), {"user_id", "filename", "mime_type", "raw_text", "timezone"})
        self.scheduler.add_job.assert_not_called()

    def test_profile_timezone_wins_over_header(self):
        self.db.profiles[USER_A] = "America/Los_Angeles"
        self.upload(headers={"X-Timezone": "Europe/Paris"})
        self.assertEqual(self.db.tables["documents"][0]["timezone"], "America/Los_Angeles")

    def test_header_then_utc_fallback(self):
        self.db.profiles[USER_A] = None
        self.upload(headers={"X-Timezone": "Europe/Paris"})
        self.upload(token="token-b")
        zones = [d["timezone"] for d in self.db.tables["documents"]]
        self.assertEqual(zones, ["Europe/Paris", "UTC"])

    def test_unknown_timezone_422(self):
        self.assertEqual(self.upload(headers={"X-Timezone": "Mars/Base"}).status_code, 422)
        self.assertEqual(self.db.tables["documents"], [])

    def test_upload_validation(self):
        r = self.upload(file=("notes.txt", b"x", "text/plain"))
        self.assertEqual(r.status_code, 415)
        self.assertEqual(self.upload(text="   ").status_code, 422)
        with mock.patch("backend.extraction.MAX_UPLOAD_BYTES", 3):
            self.assertEqual(self.upload(file=("a.pdf", b"four", "application/pdf")).status_code, 413)
        r = self.client.post("/api/v1/documents", headers=self.auth(),
                             files={"file": ("a.pdf", b"not a pdf", "application/pdf")})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.db.tables["documents"], [])

    def test_get_document_is_owner_scoped_and_hides_raw_text(self):
        doc = self.seed("documents", user_id=USER_A, filename="a.pdf", raw_text="secret",
                        mime_type="application/pdf", timezone="UTC", lease_token="lease")
        self.seed("events", user_id=USER_A, document_id=doc["id"], title="B",
                  category="deadline", starts_at="2026-12-02T00:00:00+00:00")
        self.seed("events", user_id=USER_A, document_id=doc["id"], title="A",
                  category="deadline", starts_at="2026-12-01T00:00:00+00:00")
        r = self.client.get(f"/api/v1/documents/{doc['id']}", headers=self.auth())
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("secret", r.text)
        self.assertNotIn("lease", r.json()["document"])
        self.assertEqual([e["title"] for e in r.json()["events"]], ["A", "B"])
        other = self.client.get(f"/api/v1/documents/{doc['id']}", headers=self.auth("token-b"))
        self.assertEqual(other.status_code, 404)

    def test_confirm_document(self):
        doc = self.seed("documents", user_id=USER_A, filename="a.pdf", raw_text="t",
                        mime_type="application/pdf", timezone="UTC", status="processing")
        url = f"/api/v1/documents/{doc['id']}/confirm"
        self.assertEqual(self.client.post(url, headers=self.auth()).status_code, 409)
        doc["status"] = "review"
        self.assertEqual(self.client.post(url, headers=self.auth("token-b")).status_code, 404)
        for _ in range(2):
            r = self.client.post(url, headers=self.auth())
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["document"]["status"], "confirmed")
            self.assertFalse(r.json()["reminders_scheduled"])
        self.scheduler.add_job.assert_not_called()


class TestEvents(PersistenceTestCase):
    def make(self, token="token-a", **overrides):
        body = {"title": "  Quiz  ", "category": "study",
                "starts_at": "2026-12-01T10:00:00-08:00", **overrides}
        return self.client.post("/api/v1/events", headers=self.auth(token), json=body)

    def test_create_manual_event(self):
        r = self.make()
        self.assertEqual(r.status_code, 201)
        row = self.db.tables["events"][0]
        self.assertEqual((row["title"], row["user_id"], row["source"], row["status"]),
                         ("Quiz", USER_A, "manual", "draft"))
        self.assertEqual(self.make(title="   ").status_code, 422)

    def test_list_is_scoped_filtered_and_paginated(self):
        for day in (1, 2, 3):
            self.make(starts_at=f"2026-12-0{day}T00:00:00Z")
        self.make(token="token-b", starts_at="2026-12-02T00:00:00Z")
        r = self.client.get("/api/v1/events", headers=self.auth(), params={
            "from": "2026-12-01T00:00:00Z", "to": "2026-12-03T00:00:00Z"})
        self.assertEqual([e["starts_at"] for e in r.json()["events"]],
                         ["2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z"])
        page = self.client.get("/api/v1/events", headers=self.auth(),
                               params={"limit": 1, "offset": 2}).json()["events"]
        self.assertEqual(len(page), 1)
        self.assertEqual(page[0]["user_id"], USER_A)
        bad = self.client.get("/api/v1/events", headers=self.auth(), params={
            "from": "2026-12-03T00:00:00Z", "to": "2026-12-01T00:00:00Z"})
        self.assertEqual(bad.status_code, 422)
        naive = self.client.get("/api/v1/events", headers=self.auth(),
                                params={"from": "2026-12-01T00:00:00"})
        self.assertEqual(naive.status_code, 422)

    def test_patch_rules(self):
        event_id = self.make().json()["id"]
        url = f"/api/v1/events/{event_id}"
        for body in ({}, {"title": None}, {"status": "confirmed"}, {"user_id": USER_B}):
            self.assertEqual(self.client.patch(url, headers=self.auth(), json=body).status_code,
                             422, body)
        r = self.client.patch(url, headers=self.auth(), json={"title": "Final"})
        self.assertEqual((r.status_code, r.json()["title"], r.json()["category"]),
                         (200, "Final", "study"))
        self.assertEqual(self.client.patch(url, headers=self.auth("token-b"),
                                           json={"title": "x"}).status_code, 404)
        self.assertEqual(self.db.tables["events"][0]["title"], "Final")

    def test_confirm_dismiss_and_delete(self):
        event_id = self.make().json()["id"]
        url = f"/api/v1/events/{event_id}"
        self.assertEqual(self.client.post(f"{url}/confirm", headers=self.auth("token-b")).status_code, 404)
        for _ in range(2):
            r = self.client.post(f"{url}/confirm", headers=self.auth())
            self.assertEqual((r.status_code, r.json()["event"]["status"]), (200, "confirmed"))
            self.assertFalse(r.json()["reminders_scheduled"])
        self.client.patch(url, headers=self.auth(), json={"status": "dismissed"})
        self.assertEqual(self.client.post(f"{url}/confirm", headers=self.auth()).status_code, 409)
        self.assertEqual(self.client.delete(url, headers=self.auth("token-b")).status_code, 404)
        self.assertEqual(self.client.delete(url, headers=self.auth()).status_code, 204)
        self.assertEqual(self.client.delete(url, headers=self.auth()).status_code, 404)
        self.scheduler.add_job.assert_not_called()


class TestDevices(PersistenceTestCase):
    TOKEN = "ExponentPushToken[abc_123-XYZ]"

    def test_register_and_reregister(self):
        for platform in ("ios", "android"):
            r = self.client.post("/api/v1/devices", headers=self.auth(),
                                 json={"token": self.TOKEN, "platform": platform})
            self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.db.tables["device_tokens"]), 1)
        self.assertEqual(self.db.tables["device_tokens"][0]["platform"], "android")

    def test_validation_and_cross_owner_conflict(self):
        for body in ({"token": "abc", "platform": "ios"},
                     {"token": self.TOKEN, "platform": "web"},
                     {"token": self.TOKEN, "platform": "ios", "user_id": USER_B}):
            self.assertEqual(self.client.post("/api/v1/devices", headers=self.auth(),
                                              json=body).status_code, 422, body)
        self.client.post("/api/v1/devices", headers=self.auth(),
                         json={"token": self.TOKEN, "platform": "ios"})
        r = self.client.post("/api/v1/devices", headers=self.auth("token-b"),
                             json={"token": self.TOKEN, "platform": "ios"})
        self.assertEqual(r.status_code, 409)
        self.assertNotIn(USER_A, r.text)

    def test_delete_is_owner_scoped(self):
        device = self.client.post("/api/v1/devices", headers=self.auth(),
                                  json={"token": self.TOKEN, "platform": "ios"}).json()
        url = f"/api/v1/devices/{device['id']}"
        self.assertEqual(self.client.delete(url, headers=self.auth("token-b")).status_code, 404)
        self.assertEqual(self.client.delete(url, headers=self.auth()).status_code, 204)


if __name__ == "__main__":
    unittest.main()
