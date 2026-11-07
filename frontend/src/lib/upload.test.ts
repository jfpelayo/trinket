// Run: npx tsx --test src/lib/upload.test.ts  (from frontend/)
// NOTE: the native {uri,name,type} FormData append path is only
// exercised at the call level — Node's FormData stringifies that
// object, so native byte-for-byte upload transport is NOT verified
// here and needs a real device/emulator check later.
/// <reference types="node" />
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { DocumentPickerAsset } from "expo-document-picker";

import {
  appendAssetToForm,
  backendErrorDetail,
  getApiBase,
  parseUploadBody,
  uploadDocument,
  uploadUrl,
} from "./upload";

const successBody = {
  status: "success",
  filename: "syllabus.pdf",
  user_timezone: "America/Los_Angeles",
  review_required: true,
  extracted_events: [
    {
      title: "Midterm",
      category: "deadline",
      event_date: "2026-03-02T09:00:00",
    },
  ],
};

const asset: DocumentPickerAsset = {
  name: "a.pdf",
  uri: "file:///tmp/a.pdf",
  mimeType: "application/pdf",
  size: 3,
  lastModified: 0,
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function fakeFetch(status: number, body: unknown): typeof fetch {
  return (async () => jsonResponse(status, body)) as typeof fetch;
}

describe("getApiBase / uploadUrl", () => {
  it("trims a single trailing slash", () => {
    assert.equal(getApiBase("http://localhost:8000/"), "http://localhost:8000");
    assert.equal(
      uploadUrl("http://localhost:8000/"),
      "http://localhost:8000/api/v1/upload",
    );
  });

  it("trims multiple trailing slashes and whitespace", () => {
    assert.equal(uploadUrl("  http://x:1/// "), "http://x:1/api/v1/upload");
  });

  it("accepts https", () => {
    assert.equal(
      uploadUrl("https://api.example.com"),
      "https://api.example.com/api/v1/upload",
    );
  });

  it("returns null for unset/blank env (native missing value)", () => {
    assert.equal(getApiBase(undefined), null);
    assert.equal(getApiBase(""), null);
    assert.equal(getApiBase("   "), null);
  });

  it("rejects non-http(s), malformed, and query/hash bases", () => {
    for (const bad of [
      "null",
      "notaurl",
      "ftp://x",
      "localhost:8000",
      "http://x:8000?key=1",
      "http://x:8000#frag",
    ]) {
      assert.equal(getApiBase(bad), null, bad);
    }
  });

  it("uploadUrl throws a configuration error for bad bases", () => {
    assert.throws(() => uploadUrl("null"), /EXPO_PUBLIC_API_URL/);
    assert.throws(() => uploadUrl(""), /EXPO_PUBLIC_API_URL/);
  });
});

describe("parseUploadBody", () => {
  it("parses a success response into events", () => {
    const r = parseUploadBody(200, successBody);
    assert.equal(r.ok, true);
    if (!r.ok) return;
    assert.equal(r.filename, "syllabus.pdf");
    assert.equal(r.userTimezone, "America/Los_Angeles");
    assert.equal(r.reviewRequired, true);
    assert.deepEqual(r.events, successBody.extracted_events);
  });

  it("accepts success with an actually-empty events array", () => {
    const r = parseUploadBody(200, { ...successBody, extracted_events: [] });
    assert.equal(r.ok, true);
    if (r.ok) assert.deepEqual(r.events, []);
  });

  it("rejects partial-invalid events (no silent filtering)", () => {
    const r = parseUploadBody(200, {
      ...successBody,
      extracted_events: [
        ...successBody.extracted_events,
        { title: 1, category: "study", event_date: "x" },
      ],
    });
    assert.equal(r.ok, false);
  });

  it("rejects all-invalid events", () => {
    const r = parseUploadBody(200, {
      ...successBody,
      extracted_events: [{ nope: true }],
    });
    assert.equal(r.ok, false);
  });

  it("rejects missing or non-array extracted_events", () => {
    assert.equal(
      parseUploadBody(200, {
        status: "success",
        filename: "f",
        user_timezone: "UTC",
        review_required: true,
      }).ok,
      false,
    );
    assert.equal(
      parseUploadBody(200, {
        ...successBody,
        extracted_events: "nope",
      }).ok,
      false,
    );
  });

  it("rejects missing filename/user_timezone/review_required", () => {
    assert.equal(
      parseUploadBody(200, { ...successBody, filename: 5 }).ok,
      false,
    );
    assert.equal(
      parseUploadBody(200, { ...successBody, user_timezone: null }).ok,
      false,
    );
    assert.equal(
      parseUploadBody(200, { ...successBody, review_required: false }).ok,
      false,
    );
  });

  it("rejects events outside the backend category set or empty fields", () => {
    for (const ev of [
      { title: "x", category: "wild", event_date: "d" },
      { title: "", category: "study", event_date: "d" },
      { title: "x", category: "study", event_date: "" },
    ]) {
      const r = parseUploadBody(200, {
        ...successBody,
        extracted_events: [ev],
      });
      assert.equal(r.ok, false, JSON.stringify(ev));
    }
  });

  it("handles malformed success bodies", () => {
    assert.equal(parseUploadBody(200, null).ok, false);
    assert.equal(parseUploadBody(200, "junk").ok, false);
    assert.equal(parseUploadBody(200, { status: "weird" }).ok, false);
  });

  it("maps FastAPI string detail on 4xx", () => {
    const r = parseUploadBody(413, {
      detail: "Upload exceeds the 10 MB limit",
    });
    assert.equal(r.ok, false);
    if (!r.ok) assert.equal(r.message, "Upload exceeds the 10 MB limit");
  });

  it("maps validation-style detail arrays", () => {
    const r = parseUploadBody(422, {
      detail: [{ loc: ["body"], msg: "field required" }],
    });
    assert.equal(r.ok, false);
    if (!r.ok) assert.equal(r.message, "field required");
  });

  it("maps status-only error bodies (no_text_found / extraction_failed)", () => {
    const a = parseUploadBody(422, { status: "no_text_found" });
    assert.equal(a.ok, false);
    const b = parseUploadBody(502, { status: "extraction_failed" });
    assert.equal(b.ok, false);
    if (!b.ok) assert.match(b.message, /extraction_failed/);
  });

  it("falls back to a generic message on opaque errors", () => {
    const r = parseUploadBody(500, null);
    assert.equal(r.ok, false);
    if (!r.ok) assert.match(r.message, /HTTP 500/);
  });
});

describe("backendErrorDetail", () => {
  it("handles objects and arrays", () => {
    assert.equal(backendErrorDetail({ detail: "x" }), "x");
    assert.equal(backendErrorDetail({ detail: [{ msg: "m" }] }), "m");
    assert.equal(backendErrorDetail({ detail: { msg: "m2" } }), "m2");
    assert.equal(backendErrorDetail({}), null);
  });
});

describe("appendAssetToForm", () => {
  it("web: appends DocumentPickerAsset.file directly with name/bytes", async () => {
    const webFile = new File(["abc"], "doc.pdf", {
      type: "application/pdf",
    });
    const webAsset: DocumentPickerAsset = { ...asset, file: webFile };
    const form = new FormData();
    await appendAssetToForm(form, webAsset, { web: true });
    const entry = form.get("file");
    assert.ok(entry instanceof File);
    assert.equal((entry as File).name, "doc.pdf");
    assert.equal(await (entry as File).text(), "abc");
  });

  it("web: falls back to fetch(uri) -> Blob -> File via injected fetch", async () => {
    const fetchImpl = (async (url: string) => {
      assert.equal(url, "file:///tmp/a.pdf");
      return new Response(new Blob(["xyz"]), { status: 200 });
    }) as typeof fetch;
    const form = new FormData();
    await appendAssetToForm(form, asset, { web: true, fetchImpl });
    const entry = form.get("file");
    assert.ok(entry instanceof File);
    assert.equal((entry as File).name, "a.pdf");
    assert.equal(await (entry as File).text(), "xyz");
  });
});

describe("uploadDocument", () => {
  it("appends the file and parses success", async () => {
    let seenUrl = "";
    let seenHeaders: Headers | undefined;
    const fetchSpy = (async (url: string, init: RequestInit) => {
      seenUrl = url;
      seenHeaders = new Headers(init.headers);
      return jsonResponse(200, successBody);
    }) as typeof fetch;
    const r = await uploadDocument(asset, "http://b:8000/", {
      fetchImpl: fetchSpy,
    });
    assert.equal(seenUrl, "http://b:8000/api/v1/upload");
    assert.equal(r.ok, true);
    // Timezone header present; no manual multipart boundary set.
    assert.ok(seenHeaders!.get("x-timezone"));
    assert.equal(seenHeaders!.get("content-type"), null);
  });

  it("surfaces 4xx/502 backend detail instead of throwing", async () => {
    const r413 = await uploadDocument(asset, "http://b", {
      fetchImpl: fakeFetch(413, { detail: "too big" }),
    });
    assert.equal(r413.ok, false);
    if (!r413.ok) assert.equal(r413.message, "too big");

    const r502 = await uploadDocument(asset, "http://b", {
      fetchImpl: fakeFetch(502, { status: "extraction_failed" }),
    });
    assert.equal(r502.ok, false);
  });

  it("rejects (throws) on network-level failure", async () => {
    const fetchImpl = (async () => {
      throw new TypeError("fetch failed");
    }) as typeof fetch;
    await assert.rejects(
      uploadDocument(asset, "http://b", { fetchImpl }),
      TypeError,
    );
  });

  it("does not send any device token", async () => {
    let body!: FormData;
    const fetchSpy = (async (_url: string, init: RequestInit) => {
      body = init.body as FormData;
      return jsonResponse(200, successBody);
    }) as typeof fetch;
    await uploadDocument(asset, "http://b", { fetchImpl: fetchSpy });
    for (const key of body.keys()) {
      assert.notEqual(key, "device_token");
    }
  });
});
