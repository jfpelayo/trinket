"""Offline API tests: one FastAPI instance serves root/upload/chat/profiles.

All external systems are stubbed or run through httpx.MockTransport:
scheduler start/shutdown, EasyOCR, Ollama, and Supabase transport.
No real network calls are made.
"""

import asyncio
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

import backend.extraction as extraction  # noqa: E402
import backend.main as main  # noqa: E402
import backend.routers.profiles as profiles_router  # noqa: E402
from supabase_auth.errors import AuthApiError  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class FakeBuilder:
    """Records the query chain and returns canned data from execute()."""

    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.data = client.next_data
        self.calls = client.query_calls
        self._upsert_payload = None

    def select(self, *args, **kwargs):
        self.calls.append(("select", self.table_name, args, kwargs))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", self.table_name, args, kwargs))
        return self

    def upsert(self, payload, **kwargs):
        self.calls.append(("upsert", self.table_name, payload, kwargs))
        self._upsert_payload = payload
        return self

    def execute(self):
        if self.client.execute_error is not None:
            raise self.client.execute_error
        data = self.data
        if not data and self._upsert_payload is not None:
            data = [self._upsert_payload]
        return SimpleNamespace(data=data)


class FakeAuth:
    def __init__(self, client):
        self.client = client
        self.get_user_calls = []
        self.closed = False

    def get_user(self, jwt=None):
        self.get_user_calls.append(jwt)
        if self.client.auth_error is not None:
            raise self.client.auth_error
        if jwt == "token-nouser":
            return SimpleNamespace(user=None)
        user_id = self.client.tokens.get(jwt)
        if user_id is None:
            raise AuthApiError("invalid token", 403, None)
        return SimpleNamespace(user=SimpleNamespace(id=user_id))

    def close(self):
        self.closed = True


class FakePostgrest:
    def __init__(self, client):
        self.client = client
        self.auth_calls = []
        self.closed = False

    def auth(self, token):
        self.auth_calls.append(token)
        return self

    def aclose(self):
        self.closed = True


class FakeSupabaseClient:
    def __init__(self, tokens, factory):
        self.factory = factory
        self.tokens = tokens
        self.auth = FakeAuth(self)
        self.postgrest = FakePostgrest(self)
        self.query_calls = []
        self.next_data = []
        self.auth_error = None
        self.execute_error = None

    def table(self, name):
        return FakeBuilder(self, name)


class FakeClientFactory:
    """Stands in for supabase.create_client; records call args."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.calls = []
        self.clients = []

    def __call__(self, url, key, options=None):
        self.calls.append({"url": url, "key": key, "options": options})
        client = FakeSupabaseClient(self.tokens, self)
        self.clients.append(client)
        return client


class FakeOllamaClient:
    def __init__(self, response_body=None, status_code=200, raw_content=None):
        self.response_body = response_body
        self.status_code = status_code
        self.raw_content = raw_content
        self.prompts = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, url, json, timeout):
        self.prompts.append(json["prompt"])
        if self.raw_content is not None:
            return httpx.Response(
                self.status_code,
                request=httpx.Request("POST", url),
                content=self.raw_content,
            )
        return httpx.Response(
            self.status_code,
            request=httpx.Request("POST", url),
            json={"response": self.response_body},
        )


TOKENS = {"token-a": "user-a-id", "token-b": "user-b-id"}
ANON_KEY = "anon-public-key"
SERVICE_KEY = "service-role-key"
SUPABASE_URL = "https://example.supabase.co"


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(
            os.environ,
            {
                "SUPABASE_URL": SUPABASE_URL,
                "SUPABASE_KEY": ANON_KEY,
                "SUPABASE_SERVICE_KEY": SERVICE_KEY,
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

        self.scheduler_mock = mock.MagicMock()
        scheduler_patcher = mock.patch.object(
            main, "scheduler", self.scheduler_mock
        )
        scheduler_patcher.start()
        self.addCleanup(scheduler_patcher.stop)

        self.factory = FakeClientFactory(TOKENS)
        factory_patcher = mock.patch.object(
            profiles_router, "create_client", self.factory
        )
        factory_patcher.start()
        self.addCleanup(factory_patcher.stop)

        self.client = TestClient(main.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def auth(self, token, scheme="Bearer"):
        return {"Authorization": f"{scheme} {token}"}


class TestImportFromRepoRoot(unittest.TestCase):
    def test_backend_main_importable_as_package(self):
        code = (
            "import backend.main as m\n"
            "import json\n"
            "print(json.dumps(sorted(m.app.openapi()['paths'])))\n"
        )
        env = dict(os.environ)
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            str(REPO_ROOT) + os.pathsep + existing
            if existing
            else str(REPO_ROOT)
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = json.loads(result.stdout.strip().splitlines()[-1])
        for expected in (
            "/api/v1/upload",
            "/api/v1/chat",
            "/api/v1/profiles/me",
        ):
            self.assertIn(expected, paths)


class TestRootChatUpload(ApiTestCase):
    def test_root(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("status", r.json())

    def test_chat_echo(self):
        r = self.client.post("/api/v1/chat", json={"message": "hi there"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["reply"], "Trinket received your message: hi there"
        )

    def test_chat_legacy_alias(self):
        r = self.client.post("/chat", json={"message": "old"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["reply"], "Trinket received your message: old"
        )

    def test_chat_missing_message_422(self):
        r = self.client.post("/api/v1/chat", json={})
        self.assertEqual(r.status_code, 422)

    def test_upload_returns_events_contract(self):
        fake_events = main.ExtractedData(
            events=[
                main.EventItem(
                    title="Midterm",
                    category="deadline",
                    event_date="2026-01-10T09:00:00",
                )
            ]
        )
        with mock.patch.object(
            main, "extract_raw_text", return_value="some text"
        ) as ocr, mock.patch.object(
            main, "parse_events_with_ollama", return_value=fake_events
        ) as ollama:
            r = self.client.post(
                "/api/v1/upload",
                files={"file": ("notes.pdf", b"content", "application/pdf")},
                data={"device_token": "device-token"},
            )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["filename"], "notes.pdf")
        self.assertTrue(body["review_required"])
        self.assertEqual(
            body["extracted_events"],
            [
                {
                    "title": "Midterm",
                    "category": "deadline",
                    "event_date": "2026-01-10T09:00:00",
                }
            ],
        )
        ocr.assert_called_once()
        ollama.assert_called_once()
        self.scheduler_mock.add_job.assert_not_called()

    def test_upload_rejects_unsupported_file_type(self):
        r = self.client.post(
            "/api/v1/upload",
            files={"file": ("notes.txt", b"content", "text/plain")},
        )
        self.assertEqual(r.status_code, 415)

    def test_upload_rejects_file_over_size_limit(self):
        with mock.patch.object(main, "MAX_UPLOAD_BYTES", 3):
            r = self.client.post(
                "/api/v1/upload",
                files={"file": ("notes.pdf", b"four", "application/pdf")},
            )
        self.assertEqual(r.status_code, 413)

    def test_upload_returns_explicit_extraction_failure(self):
        with mock.patch.object(
            main, "extract_raw_text", return_value="some text"
        ), mock.patch.object(
            main,
            "parse_events_with_ollama",
            side_effect=main.EventExtractionError("offline"),
        ):
            r = self.client.post(
                "/api/v1/upload",
                files={"file": ("notes.pdf", b"content", "application/pdf")},
            )
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json(), {"status": "extraction_failed"})

    def test_upload_with_no_ocr_text_is_unprocessable(self):
        with mock.patch.object(main, "extract_raw_text", return_value="  "):
            r = self.client.post(
                "/api/v1/upload",
                files={"file": ("notes.pdf", b"content", "application/pdf")},
            )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"status": "no_text_found"})

    def test_upload_rejects_invalid_pdf(self):
        r = self.client.post(
            "/api/v1/upload",
            files={"file": ("notes.pdf", b"not a PDF", "application/pdf")},
        )
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["detail"], "Uploaded PDF is invalid")

    def test_pdf_page_limit_is_enforced_before_ocr(self):
        document = main.fitz.open()
        for _ in range(main.MAX_PDF_PAGES + 1):
            document.new_page()
        file_bytes = document.tobytes()
        document.close()
        with mock.patch.object(extraction, "get_ocr_reader") as ocr:
            with self.assertRaises(main.DocumentInputError):
                main.extract_raw_text(file_bytes, "notes.pdf")
        ocr.assert_not_called()

    def test_event_item_rejects_invalid_date(self):
        with self.assertRaises(ValueError):
            main.EventItem(
                title="Midterm",
                category="deadline",
                event_date="not-a-date",
            )

    def test_long_extraction_text_is_chunked_and_deduplicated(self):
        response_body = (
            '{"events":[{"title":"Midterm","category":"deadline",'
            '"event_date":"2026-07-12T10:00:00"}]}'
        )
        fake_ollama = FakeOllamaClient(response_body)
        with mock.patch.object(
            extraction.httpx, "AsyncClient", return_value=fake_ollama
        ):
            result = asyncio.run(
                main.parse_events_with_ollama(
                    "x" * (main.OLLAMA_CHUNK_CHARS + 1), "UTC"
                )
            )
        self.assertEqual(len(fake_ollama.prompts), 2)
        self.assertTrue(
            all("Today's date" in prompt for prompt in fake_ollama.prompts)
        )
        self.assertEqual(len(result.events), 1)

    def test_invalid_ollama_date_fails_extraction(self):
        fake_ollama = FakeOllamaClient(
            '{"events":[{"title":"Midterm","category":"deadline",'
            '"event_date":"not-a-date"}]}'
        )
        with mock.patch.object(
            extraction.httpx, "AsyncClient", return_value=fake_ollama
        ):
            with self.assertRaises(main.EventExtractionError):
                asyncio.run(main.parse_events_with_ollama("text", "UTC"))

    def test_ollama_http_failure_fails_extraction(self):
        fake_ollama = FakeOllamaClient("{}", status_code=503)
        with mock.patch.object(
            extraction.httpx, "AsyncClient", return_value=fake_ollama
        ):
            with self.assertRaises(main.EventExtractionError):
                asyncio.run(main.parse_events_with_ollama("text", "UTC"))

    def test_ollama_invalid_json_fails_extraction(self):
        fake_ollama = FakeOllamaClient(raw_content=b"{")
        with mock.patch.object(
            extraction.httpx, "AsyncClient", return_value=fake_ollama
        ):
            with self.assertRaises(main.EventExtractionError):
                asyncio.run(main.parse_events_with_ollama("text", "UTC"))

    def test_scheduler_started_and_stopped(self):
        self.scheduler_mock.start.assert_called_once()
        self.client.__exit__(None, None, None)
        self.scheduler_mock.shutdown.assert_called_once()


class TestProfileAuth(ApiTestCase):
    def test_missing_bearer_401(self):
        r = self.client.get("/api/v1/profiles/me")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.headers.get("WWW-Authenticate"), "Bearer")

    def test_malformed_bearer_401(self):
        for header in [
            "token-a",
            "Bearer",
            "Bearer ",
            "Basic abc",
            "Bearer token-a extra",
            "Bearer token-a token-b",
        ]:
            r = self.client.get(
                "/api/v1/profiles/me",
                headers={"Authorization": header},
            )
            self.assertEqual(r.status_code, 401, header)
            self.assertEqual(r.headers.get("WWW-Authenticate"), "Bearer")

    def test_bearer_scheme_case_insensitive(self):
        for scheme in ["bearer", "BEARER", "Bearer"]:
            r = self.client.get(
                "/api/v1/profiles/me",
                headers=self.auth("token-a", scheme=scheme),
            )
            self.assertEqual(r.status_code, 404, scheme)  # auth passed; no row

    def test_invalid_token_401(self):
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("bad-token")
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.headers.get("WWW-Authenticate"), "Bearer")
        self.assertNotIn("bad-token", r.text)
        self.assertNotIn(ANON_KEY, r.text)
        self.assertNotIn(SERVICE_KEY, r.text)

    def test_no_user_401(self):
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-nouser")
        )
        self.assertEqual(r.status_code, 401)

    def test_auth_transport_failure_503(self):
        def make_client(url, key, options=None):
            c = FakeSupabaseClient(TOKENS, self.factory)
            c.auth_error = httpx.ConnectError("down")
            return c

        with mock.patch.object(
            profiles_router, "create_client", side_effect=make_client
        ):
            r = self.client.get(
                "/api/v1/profiles/me", headers=self.auth("token-a")
            )
        self.assertEqual(r.status_code, 503)

    def test_missing_config_503(self):
        with mock.patch.dict(
            os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""}
        ):
            r = self.client.get(
                "/api/v1/profiles/me", headers=self.auth("token-a")
            )
        self.assertEqual(r.status_code, 503)

    def test_create_client_failure_503(self):
        with mock.patch.object(
            profiles_router,
            "create_client",
            side_effect=ValueError("bad config"),
        ):
            r = self.client.get(
                "/api/v1/profiles/me", headers=self.auth("token-a")
            )
        self.assertEqual(r.status_code, 503)
        self.assertNotIn("bad config", r.text)


class TestProfileEndpoints(ApiTestCase):
    def test_get_404(self):
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-a")
        )
        self.assertEqual(r.status_code, 404)

    def test_get_row(self):
        original_call = self.factory.__call__

        def seeded(url, key, options=None):
            c = original_call(url, key, options)
            c.next_data = [{"id": "user-a-id", "display_name": "A"}]
            return c

        with mock.patch.object(
            profiles_router, "create_client", side_effect=seeded
        ):
            r = self.client.get(
                "/api/v1/profiles/me", headers=self.auth("token-a")
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["id"], "user-a-id")
        self.assertEqual(r.json()["display_name"], "A")

    def test_put_trims_name_and_scopes_to_verified_user(self):
        r = self.client.put(
            "/api/v1/profiles/me",
            headers=self.auth("token-a"),
            json={
                "display_name": "  Ada  ",
                "timezone": "America/Los_Angeles",
                "communication_style": "concise",
                "focus_session_minutes": 25,
                "preferred_study_time": "14:30",
                "reminders_enabled": True,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        upserts = [
            c for c in self.factory.clients[0].query_calls if c[0] == "upsert"
        ]
        self.assertEqual(len(upserts), 1)
        payload = upserts[0][2]
        self.assertEqual(payload["id"], "user-a-id")
        self.assertEqual(payload["display_name"], "Ada")
        self.assertEqual(payload["timezone"], "America/Los_Angeles")
        self.assertEqual(payload["communication_style"], "concise")
        self.assertEqual(payload["focus_session_minutes"], 25)
        self.assertEqual(payload["preferred_study_time"], "14:30:00")
        self.assertEqual(payload["reminders_enabled"], True)
        self.assertEqual(upserts[0][3].get("on_conflict"), "id")

    def test_put_omitted_fields_not_sent(self):
        r = self.client.put(
            "/api/v1/profiles/me",
            headers=self.auth("token-a"),
            json={"display_name": "Ada"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        upserts = [
            c for c in self.factory.clients[0].query_calls if c[0] == "upsert"
        ]
        payload = upserts[0][2]
        self.assertEqual(set(payload), {"id", "display_name"})

    def test_put_rejects_invalid_bodies(self):
        cases = [
            {"id": "spoofed", "display_name": "X"},
            {"display_name": "X", "nope": 1},
            {"display_name": "   "},
            {"display_name": "X", "communication_style": "wild"},
            {"display_name": "X", "motivation_style": "n/a"},
            {"display_name": "X", "timezone": "Not/AZone"},
            {"display_name": "X", "focus_session_minutes": 4},
            {"display_name": "X", "focus_session_minutes": 181},
            {"display_name": "X", "reminders_enabled": None},
            {"display_name": "X", "pronouns": ""},
            {"display_name": "X", "pronouns": "p" * 101},
            {"display_name": "X", "preferred_study_time": "14:30:00+01:00"},
            {"timezone": "UTC"},
        ]
        for body in cases:
            r = self.client.put(
                "/api/v1/profiles/me",
                headers=self.auth("token-a"),
                json=body,
            )
            self.assertEqual(r.status_code, 422, body)

    def test_explicit_nullable_fields_allowed(self):
        r = self.client.put(
            "/api/v1/profiles/me",
            headers=self.auth("token-a"),
            json={
                "display_name": "Ada",
                "avatar_url": None,
                "pronouns": None,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        upserts = [
            c for c in self.factory.clients[0].query_calls if c[0] == "upsert"
        ]
        payload = upserts[0][2]
        self.assertIsNone(payload["avatar_url"])
        self.assertIsNone(payload["pronouns"])

    def test_two_users_scoped_separately(self):
        self.client.put(
            "/api/v1/profiles/me",
            headers=self.auth("token-a"),
            json={"display_name": "Ada"},
        )
        self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-b")
        )
        client_a, client_b = self.factory.clients[0], self.factory.clients[1]
        upsert = [c for c in client_a.query_calls if c[0] == "upsert"][0]
        eq = [c for c in client_b.query_calls if c[0] == "eq"][0]
        self.assertEqual(upsert[2]["id"], "user-a-id")
        self.assertEqual(eq[2], ("id", "user-b-id"))
        self.assertEqual(client_a.auth.get_user_calls, ["token-a"])
        self.assertEqual(client_b.auth.get_user_calls, ["token-b"])
        self.assertEqual(client_a.postgrest.auth_calls, ["token-a"])
        self.assertEqual(client_b.postgrest.auth_calls, ["token-b"])

    def test_auth_and_scoping_calls_and_no_service_key(self):
        self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-a")
        )
        call = self.factory.calls[0]
        self.assertEqual(call["url"], SUPABASE_URL)
        self.assertEqual(call["key"], ANON_KEY)
        self.assertNotEqual(call["key"], SERVICE_KEY)
        self.assertFalse(call["options"].persist_session)
        self.assertFalse(call["options"].auto_refresh_token)
        client = self.factory.clients[0]
        self.assertEqual(client.auth.get_user_calls, ["token-a"])
        self.assertEqual(client.postgrest.auth_calls, ["token-a"])
        self.assertTrue(client.postgrest.closed)
        self.assertTrue(client.auth.closed)


class SupabaseTransport:
    """httpx.MockTransport handler emulating GoTrue + PostgREST.

    Rows are stored per verified user id so cross-user leakage is
    observable. Failure flags inject auth/db errors at transport level.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.requests = []
        self.rows = {}  # user_id -> row dict
        self.fail_auth_transport = False
        self.fail_db_transport = False
        self.db_error = False
        self.empty_save = False

    def _bearer(self, request):
        parts = (request.headers.get("authorization") or "").split()
        return parts[1] if len(parts) == 2 else None

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path

        if path.endswith("/auth/v1/user"):
            if self.fail_auth_transport:
                raise httpx.ConnectError("auth down", request=request)
            uid = self.tokens.get(self._bearer(request))
            if uid is None:
                return httpx.Response(
                    403,
                    json={
                        "error_code": "bad_jwt",
                        "code": 403,
                        "msg": "invalid JWT",
                    },
                )
            return httpx.Response(
                200,
                json={
                    "id": uid,
                    "aud": "authenticated",
                    "role": "authenticated",
                    "email": f"{uid}@example.com",
                    "app_metadata": {"provider": "email"},
                    "user_metadata": {},
                    "created_at": "2026-01-01T00:00:00.000000Z",
                    "updated_at": "2026-01-01T00:00:00.000000Z",
                },
            )

        if "/rest/v1/profiles" in path:
            if self.fail_db_transport:
                raise httpx.ConnectError("db down", request=request)
            if self.db_error:
                return httpx.Response(
                    500,
                    json={
                        "code": "XX000",
                        "message": "internal error",
                        "details": None,
                        "hint": None,
                    },
                )
            uid = self.tokens.get(self._bearer(request))
            if request.method == "POST":
                row = json.loads(request.content)
                if self.empty_save:
                    return httpx.Response(201, json=[])
                self.rows[uid] = row
                return httpx.Response(201, json=[row])
            row = self.rows.get(uid)
            return httpx.Response(200, json=[row] if row else [])

        return httpx.Response(404, json={"message": f"no route {path}"})


class TestProfilesRealSdkTransport(unittest.TestCase):
    """Drive the router through the pinned supabase SDK with network
    faked only at the httpx transport layer (no real network)."""

    def setUp(self):
        self.env = mock.patch.dict(
            os.environ,
            {
                "SUPABASE_URL": SUPABASE_URL,
                "SUPABASE_KEY": ANON_KEY,
                "SUPABASE_SERVICE_KEY": SERVICE_KEY,
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

        self.scheduler_mock = mock.MagicMock()
        scheduler_patcher = mock.patch.object(
            main, "scheduler", self.scheduler_mock
        )
        scheduler_patcher.start()
        self.addCleanup(scheduler_patcher.stop)

        self.transport = SupabaseTransport(TOKENS)
        self.created = []
        self.factory_calls = []

        import supabase as supabase_pkg

        def real_factory(url, key, options=None):
            self.factory_calls.append((url, key))
            # Inject the mocked transport into the request-scoped client
            # options the router built (keeps persist/auto_refresh flags).
            options.httpx_client = httpx.Client(
                transport=httpx.MockTransport(self.transport)
            )
            client = supabase_pkg.create_client(url, key, options)
            self.created.append(client)
            return client

        factory_patcher = mock.patch.object(
            profiles_router, "create_client", side_effect=real_factory
        )
        factory_patcher.start()
        self.addCleanup(factory_patcher.stop)

        self.client = TestClient(main.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _rest_requests(self):
        return [
            r for r in self.transport.requests
            if "/rest/v1/profiles" in r.url.path
        ]

    def _auth_requests(self):
        return [
            r for r in self.transport.requests
            if r.url.path.endswith("/auth/v1/user")
        ]

    def test_get_put_via_real_sdk_transport(self):
        # PUT as user A
        r = self.client.put(
            "/api/v1/profiles/me",
            headers=self.auth("token-a"),
            json={
                "display_name": "Ada",
                "timezone": "UTC",
                "reminders_enabled": False,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["display_name"], "Ada")

        # GET as user A returns the stored row
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-a")
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["display_name"], "Ada")

        # Every request carried the USER bearer token, never service key
        for req in self.transport.requests:
            self.assertEqual(
                req.headers.get("authorization"), "Bearer token-a"
            )
            self.assertEqual(req.headers.get("apikey"), ANON_KEY)
            self.assertNotEqual(req.headers.get("apikey"), SERVICE_KEY)
            self.assertNotIn(SERVICE_KEY, req.headers.get("authorization"))

        # create_client used anon key
        for url, key in self.factory_calls:
            self.assertEqual(url, SUPABASE_URL)
            self.assertEqual(key, ANON_KEY)

        # GET query shape: select=* & id=eq.<user>
        get_req = [
            r for r in self._rest_requests() if r.method == "GET"
        ][-1]
        self.assertEqual(get_req.url.params["id"], "eq.user-a-id")
        self.assertEqual(get_req.url.params["select"], "*")

        # PUT JSON payload scoped to verified id
        post_req = [r for r in self._rest_requests() if r.method == "POST"][0]
        payload = json.loads(post_req.content)
        self.assertEqual(payload["id"], "user-a-id")
        self.assertEqual(payload["display_name"], "Ada")
        self.assertEqual(payload["timezone"], "UTC")
        self.assertEqual(payload["reminders_enabled"], False)

        # Request-scoped clients were closed
        for client in self.created:
            self.assertTrue(client.postgrest.session.is_closed)

    def test_two_users_isolated_over_transport(self):
        self.client.put(
            "/api/v1/profiles/me",
            headers=self.auth("token-a"),
            json={"display_name": "Ada"},
        )
        # User B sees their own (empty) profile, not A's row
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-b")
        )
        self.assertEqual(r.status_code, 404)
        b_reqs = [
            r
            for r in self._rest_requests()
            if r.headers.get("authorization") == "Bearer token-b"
        ]
        self.assertTrue(b_reqs)
        self.assertEqual(b_reqs[0].url.params["id"], "eq.user-b-id")

    def test_expired_token_401(self):
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("bad-token")
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.headers.get("WWW-Authenticate"), "Bearer")

    def test_auth_transport_failure_503(self):
        self.transport.fail_auth_transport = True
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-a")
        )
        self.assertEqual(r.status_code, 503)

    def test_db_api_error_502(self):
        self.transport.db_error = True
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-a")
        )
        self.assertEqual(r.status_code, 502)

    def test_db_transport_failure_502(self):
        self.transport.fail_db_transport = True
        r = self.client.get(
            "/api/v1/profiles/me", headers=self.auth("token-a")
        )
        self.assertEqual(r.status_code, 502)

    def test_empty_save_502(self):
        self.transport.empty_save = True
        r = self.client.put(
            "/api/v1/profiles/me",
            headers=self.auth("token-a"),
            json={"display_name": "Ada"},
        )
        self.assertEqual(r.status_code, 502)

    def test_invalid_supabase_url_503(self):
        # Real create_client rejects the URL -> sanitized 503.
        with mock.patch.dict(os.environ, {"SUPABASE_URL": "not-a-url"}):
            r = self.client.get(
                "/api/v1/profiles/me", headers=self.auth("token-a")
            )
        self.assertEqual(r.status_code, 503)
        self.assertNotIn("not-a-url", r.text)


if __name__ == "__main__":
    unittest.main()
