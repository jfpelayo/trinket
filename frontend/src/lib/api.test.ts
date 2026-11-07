// Run: npx tsx --test src/lib/api.test.ts  (from frontend/)
// The native {uri,name,type} FormData path needs a device/emulator check;
// Node's FormData cannot verify native byte transport.
/// <reference types="node" />
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { DocumentPickerAsset } from "expo-document-picker";

import {
  type Api,
  confirmDocument,
  getApiBase,
  getDocument,
  listEvents,
  parseDocumentBody,
  setEventStatus,
  uploadDocument,
} from "./api";

const document = {
  id: "doc-1", user_id: "u", filename: "syllabus.pdf", mime_type: "application/pdf",
  status: "processing", timezone: "America/Los_Angeles", error_code: null,
  created_at: "2026-11-07T00:00:00Z", updated_at: "2026-11-07T00:00:00Z",
};
const event = {
  id: "evt-1", user_id: "u", document_id: "doc-1", title: "Midterm", category: "deadline",
  starts_at: "2026-12-01T18:00:00+00:00", all_day: false, source: "extracted",
  status: "draft", reminder_offset_minutes: 15,
};
const asset: DocumentPickerAsset = {
  name: "syllabus.pdf", uri: "file:///tmp/syllabus.pdf", mimeType: "application/pdf",
  size: 3, lastModified: 0,
};

type Call = { url: string; init: RequestInit };

function fakeApi(status: number, body: unknown, calls: Call[] = []): Api {
  const fetchImpl = (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), { status });
  }) as typeof fetch;
  return { base: "http://api.test", token: "user-token", deps: { fetchImpl, web: true } };
}

describe("getApiBase", () => {
  it("accepts absolute http(s) URLs and trims slashes", () => {
    assert.equal(getApiBase(" http://localhost:8000// "), "http://localhost:8000");
    assert.equal(getApiBase("https://api.example.com"), "https://api.example.com");
  });
  it("rejects blank, relative, other schemes, query, and hash", () => {
    for (const bad of [undefined, "", "localhost:8000", "ftp://x", "http://x?a=1", "http://x#f"]) {
      assert.equal(getApiBase(bad), null, String(bad));
    }
  });
});

describe("parseDocumentBody", () => {
  it("accepts a document with events", () => {
    const r = parseDocumentBody({ document: { ...document, status: "review" }, events: [event] });
    assert.ok(r.ok);
    assert.equal(r.value.document.status, "review");
    assert.equal(r.value.events[0].title, "Midterm");
  });
  it("rejects malformed documents and any malformed event", () => {
    for (const body of [
      null, {}, { document: { ...document, status: "weird" }, events: [] },
      { document, events: "nope" },
      { document, events: [event, { ...event, starts_at: "not a date" }] },
      { document, events: [{ ...event, status: "unknown" }] },
    ]) {
      assert.equal(parseDocumentBody(body).ok, false, JSON.stringify(body));
    }
  });
});

describe("authenticated requests", () => {
  it("uploads to /api/v1/documents with the bearer token and no manual Content-Type", async () => {
    const calls: Call[] = [];
    const webFile = new File(["abc"], "syllabus.pdf", { type: "application/pdf" });
    const r = await uploadDocument(
      fakeApi(202, { document, events: [] }, calls), { ...asset, file: webFile },
    );
    assert.ok(r.ok);
    assert.equal(r.value.document.status, "processing");
    const { url, init } = calls[0];
    assert.equal(url, "http://api.test/api/v1/documents");
    const headers = new Headers(init.headers);
    assert.equal(headers.get("authorization"), "Bearer user-token");
    assert.ok(headers.get("x-timezone"));
    assert.equal(headers.get("content-type"), null);
    const sent = (init.body as FormData).get("file") as File;
    assert.equal(await sent.text(), "abc");
    assert.deepEqual([...(init.body as FormData).keys()], ["file"]);
  });

  it("maps backend errors and expired sessions to readable messages", async () => {
    const tooBig = await uploadDocument(fakeApi(413, { detail: "Upload exceeds the 10 MB limit" }),
      { ...asset, file: new File(["x"], "a.pdf") });
    assert.deepEqual(tooBig, { ok: false, message: "Upload exceeds the 10 MB limit" });
    const expired = await getDocument(fakeApi(401, { detail: "Invalid or expired token" }), "doc-1");
    assert.equal(expired.ok, false);
    assert.match(expired.ok ? "" : expired.message, /sign in again/);
    const opaque = await getDocument(fakeApi(502, null), "doc-1");
    assert.deepEqual(opaque, { ok: false, message: "Request failed (HTTP 502)." });
  });

  it("network failures reject so screens can report them", async () => {
    const api: Api = {
      base: "http://api.test", token: "t",
      deps: { fetchImpl: (async () => { throw new TypeError("fetch failed"); }) as typeof fetch },
    };
    await assert.rejects(getDocument(api, "doc-1"), TypeError);
  });

  it("confirms, dismisses, and lists events on the right routes", async () => {
    const calls: Call[] = [];
    const confirmed = await confirmDocument(
      fakeApi(200, { document: { ...document, status: "confirmed" }, reminders_scheduled: false }, calls),
      "doc/1",
    );
    assert.ok(confirmed.ok);
    assert.equal(calls[0].url, "http://api.test/api/v1/documents/doc%2F1/confirm");
    assert.equal(calls[0].init.method, "POST");

    const dismissed = await setEventStatus(fakeApi(200, { ...event, status: "dismissed" }, calls), "evt-1", "dismissed");
    assert.ok(dismissed.ok);
    assert.equal(calls[1].init.method, "PATCH");
    assert.deepEqual(JSON.parse(calls[1].init.body as string), { status: "dismissed" });

    const listed = await listEvents(fakeApi(200, { events: [event] }, calls), new Date("2026-11-07T08:00:00Z"));
    assert.ok(listed.ok);
    assert.equal(calls[2].url,
      "http://api.test/api/v1/events?from=2026-11-07T08%3A00%3A00.000Z&limit=100");
  });
});
