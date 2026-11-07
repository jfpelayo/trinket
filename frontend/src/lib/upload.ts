// Keep this module free of react-native runtime imports so the helpers
// can be exercised under the plain Node test runner.
import type { DocumentPickerAsset } from "expo-document-picker";

function isWeb(): boolean {
  return typeof window !== "undefined" && typeof window.document === "object";
}

export interface EventItem {
  title: string;
  category: string;
  event_date: string;
}

export interface UploadSuccess {
  ok: true;
  filename: string;
  userTimezone: string;
  reviewRequired: boolean;
  events: EventItem[];
}

export interface UploadFailure {
  ok: false;
  message: string;
}

export type UploadResult = UploadSuccess | UploadFailure;

/**
 * Base URL for the backend, e.g. "http://localhost:8000".
 * Returns null when unset or invalid — callers must surface a
 * configuration error rather than build a broken URL. Only absolute
 * http(s) URLs without query/hash are accepted; trailing slashes and
 * surrounding whitespace are normalized away.
 */
export function getApiBase(
  env: string | undefined = process.env.EXPO_PUBLIC_API_URL,
): string | null {
  const trimmed = (env ?? "").trim();
  if (!trimmed) return null;
  const withoutSlashes = trimmed.replace(/\/+$/, "");
  let parsed: URL;
  try {
    parsed = new URL(withoutSlashes);
  } catch {
    return null;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return null;
  }
  if (parsed.search || parsed.hash || !parsed.hostname) {
    return null;
  }
  return withoutSlashes;
}

export function uploadUrl(base: string): string {
  const normalized = getApiBase(base);
  if (!normalized) {
    throw new Error(
      "EXPO_PUBLIC_API_URL must be an absolute http(s) URL without query or hash",
    );
  }
  return `${normalized}/api/v1/upload`;
}

/** Extract a human-readable message from FastAPI error bodies. */
export function backendErrorDetail(body: unknown): string | null {
  if (body == null || typeof body !== "object") return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "string") return first;
    if (first && typeof first === "object") {
      const msg = (first as { msg?: unknown }).msg;
      if (typeof msg === "string" && msg.trim()) return msg;
    }
    return JSON.stringify(detail);
  }
  if (detail && typeof detail === "object") {
    const msg = (detail as { msg?: unknown }).msg;
    if (typeof msg === "string" && msg.trim()) return msg;
    return JSON.stringify(detail);
  }
  const status = (body as { status?: unknown }).status;
  if (typeof status === "string" && status !== "success") {
    return `Upload failed (${status}).`;
  }
  return null;
}

// Categories emitted by the backend EventItem model.
const EVENT_CATEGORIES = new Set([
  "meeting",
  "study",
  "deadline",
  "other",
]);

function isEventItem(value: unknown): value is EventItem {
  if (value == null || typeof value !== "object") return false;
  const e = value as Record<string, unknown>;
  return (
    typeof e.title === "string" &&
    e.title.trim() !== "" &&
    typeof e.event_date === "string" &&
    e.event_date.trim() !== "" &&
    typeof e.category === "string" &&
    EVENT_CATEGORIES.has(e.category)
  );
}

const SHAPE_ERROR =
  "Backend returned an unexpected response shape.";

/**
 * Validate the response before rendering. A successful payload must
 * carry filename/user_timezone strings, review_required === true, and
 * an extracted_events array whose every entry is a well-formed event —
 * partial or malformed payloads fail loudly instead of rendering as
 * "no events found". An actually empty events array is valid.
 */
export function parseUploadBody(
  status: number,
  body: unknown,
): UploadResult {
  if (status < 200 || status >= 300) {
    const detail = backendErrorDetail(body);
    return {
      ok: false,
      message: detail ?? `Upload failed (HTTP ${status}).`,
    };
  }
  if (body == null || typeof body !== "object") {
    return { ok: false, message: "Backend returned an unreadable response." };
  }
  const b = body as Record<string, unknown>;
  if (b.status !== "success") {
    return {
      ok: false,
      message:
        backendErrorDetail(body) ?? "Backend did not process the document.",
    };
  }
  if (
    typeof b.filename !== "string" ||
    typeof b.user_timezone !== "string" ||
    b.review_required !== true ||
    !Array.isArray(b.extracted_events)
  ) {
    return { ok: false, message: SHAPE_ERROR };
  }
  if (!b.extracted_events.every(isEventItem)) {
    return { ok: false, message: SHAPE_ERROR };
  }
  return {
    ok: true,
    filename: b.filename,
    userTimezone: b.user_timezone,
    reviewRequired: true,
    events: b.extracted_events,
  };
}

export interface UploadDeps {
  fetchImpl?: typeof fetch;
  /** Override web/native detection (tests). */
  web?: boolean;
}

/**
 * Append the picked asset to FormData.
 * Web: prefer DocumentPickerAsset.file, else fetch(uri) -> Blob -> File.
 * Native: React Native's { uri, name, type } file shape.
 */
export async function appendAssetToForm(
  form: FormData,
  asset: DocumentPickerAsset,
  deps: UploadDeps = {},
): Promise<void> {
  const web = deps.web ?? isWeb();
  if (web) {
    const webFile = (asset as { file?: File }).file;
    if (webFile) {
      form.append("file", webFile);
      return;
    }
    const res = await (deps.fetchImpl ?? fetch)(asset.uri);
    const blob = await res.blob();
    form.append(
      "file",
      new File([blob], asset.name, {
        type: asset.mimeType || "application/octet-stream",
      }),
    );
    return;
  }
  // React Native FormData accepts this file-like object; its typing
  // doesn't cover it, hence the single cast here.
  form.append("file", {
    uri: asset.uri,
    name: asset.name,
    type: asset.mimeType || "application/octet-stream",
  } as unknown as Blob);
}

/**
 * POST the document to the backend. Never sets a multipart
 * Content-Type header manually — fetch/RN compute the boundary.
 * Throws only on network-level failure; HTTP errors come back parsed.
 */
export async function uploadDocument(
  asset: DocumentPickerAsset,
  apiBase: string,
  deps: UploadDeps = {},
): Promise<UploadResult> {
  const form = new FormData();
  await appendAssetToForm(form, asset, deps);

  const timezone =
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

  const response = await (deps.fetchImpl ?? fetch)(uploadUrl(apiBase), {
    method: "POST",
    body: form,
    headers: { "X-Timezone": timezone },
  });

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON body; handled below via status code.
  }
  return parseUploadBody(response.status, body);
}
