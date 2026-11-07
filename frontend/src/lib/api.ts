// Client for the authenticated Phase 3 backend routes.
// Keep this module free of react-native runtime imports so it can be
// exercised under the plain Node test runner.
import type { DocumentPickerAsset } from "expo-document-picker";

export type DocumentStatus = "processing" | "review" | "confirmed" | "failed";
export type EventStatus = "draft" | "confirmed" | "dismissed";

export interface TrinketDocument {
  id: string;
  filename: string;
  status: DocumentStatus;
  timezone: string;
  error_code: string | null;
}

export interface TrinketEvent {
  id: string;
  document_id: string | null;
  title: string;
  category: string;
  starts_at: string;
  all_day: boolean;
  status: EventStatus;
}

export type Result<T> = { ok: true; value: T } | { ok: false; message: string };

export interface ApiDeps {
  fetchImpl?: typeof fetch;
  /** Override web/native detection (tests). */
  web?: boolean;
}

const DOCUMENT_STATUSES = new Set(["processing", "review", "confirmed", "failed"]);
const EVENT_STATUSES = new Set(["draft", "confirmed", "dismissed"]);
const SHAPE_ERROR = "Backend returned an unexpected response shape.";

/**
 * Absolute http(s) backend base URL without query/hash, trailing slashes
 * removed; null when unset or invalid so callers can show a config error.
 */
export function getApiBase(
  env: string | undefined = process.env.EXPO_PUBLIC_API_URL,
): string | null {
  const trimmed = (env ?? "").trim().replace(/\/+$/, "");
  if (!trimmed) return null;
  try {
    const parsed = new URL(trimmed);
    const valid =
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      parsed.hostname && !parsed.search && !parsed.hash;
    return valid ? trimmed : null;
  } catch {
    return null;
  }
}

/** Extract a human-readable message from FastAPI error bodies. */
export function backendErrorDetail(body: unknown): string | null {
  if (body == null || typeof body !== "object") return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  const first = Array.isArray(detail) ? detail[0] : detail;
  if (typeof first === "string") return first;
  if (first && typeof first === "object") {
    const msg = (first as { msg?: unknown }).msg;
    return typeof msg === "string" && msg.trim() ? msg : JSON.stringify(detail);
  }
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value != null && typeof value === "object" && !Array.isArray(value);
}

export function parseDocument(value: unknown): TrinketDocument | null {
  if (!isRecord(value)) return null;
  const { id, filename, status, timezone, error_code } = value;
  if (typeof id !== "string" || typeof filename !== "string" ||
      typeof status !== "string" || !DOCUMENT_STATUSES.has(status) ||
      typeof timezone !== "string" ||
      (error_code !== null && typeof error_code !== "string")) {
    return null;
  }
  return { id, filename, status: status as DocumentStatus, timezone, error_code };
}

export function parseEvent(value: unknown): TrinketEvent | null {
  if (!isRecord(value)) return null;
  const { id, document_id, title, category, starts_at, all_day, status } = value;
  if (typeof id !== "string" || typeof title !== "string" ||
      typeof category !== "string" || typeof starts_at !== "string" ||
      Number.isNaN(Date.parse(starts_at)) || typeof all_day !== "boolean" ||
      typeof status !== "string" || !EVENT_STATUSES.has(status) ||
      (document_id !== null && typeof document_id !== "string")) {
    return null;
  }
  return { id, document_id, title, category, starts_at, all_day, status: status as EventStatus };
}

/** Parse a list strictly: one malformed entry fails the whole response. */
function parseList<T>(value: unknown, parse: (v: unknown) => T | null): T[] | null {
  if (!Array.isArray(value)) return null;
  const items = value.map(parse);
  return items.every((item) => item !== null) ? (items as T[]) : null;
}

export function parseDocumentBody(
  body: unknown,
): Result<{ document: TrinketDocument; events: TrinketEvent[] }> {
  const document = isRecord(body) ? parseDocument(body.document) : null;
  const events = isRecord(body) ? parseList(body.events, parseEvent) : null;
  return document && events
    ? { ok: true, value: { document, events } }
    : { ok: false, message: SHAPE_ERROR };
}

export function parseEventsBody(body: unknown): Result<TrinketEvent[]> {
  const events = isRecord(body) ? parseList(body.events, parseEvent) : null;
  return events ? { ok: true, value: events } : { ok: false, message: SHAPE_ERROR };
}

export interface Api {
  base: string;
  token: string;
  deps?: ApiDeps;
}

/** Send an authenticated request; HTTP errors resolve, network errors throw. */
export async function request(
  api: Api, path: string, init: RequestInit = {},
): Promise<Result<unknown>> {
  const response = await (api.deps?.fetchImpl ?? fetch)(`${api.base}${path}`, {
    ...init,
    headers: { ...(init.headers as Record<string, string>), Authorization: `Bearer ${api.token}` },
  });
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Empty (204) or non-JSON body; judged by status below.
  }
  if (response.status === 401) {
    return { ok: false, message: "Your session expired. Please sign in again." };
  }
  if (response.status < 200 || response.status >= 300) {
    return { ok: false, message: backendErrorDetail(body) ?? `Request failed (HTTP ${response.status}).` };
  }
  return { ok: true, value: body };
}

function isWeb(): boolean {
  return typeof window !== "undefined" && typeof window.document === "object";
}

/** Append the picked asset as the multipart `file` field. */
export async function appendAssetToForm(
  form: FormData, asset: DocumentPickerAsset, deps: ApiDeps = {},
): Promise<void> {
  if (deps.web ?? isWeb()) {
    const webFile = (asset as { file?: File }).file;
    if (webFile) {
      form.append("file", webFile);
      return;
    }
    const blob = await (await (deps.fetchImpl ?? fetch)(asset.uri)).blob();
    form.append("file", new File([blob], asset.name, {
      type: asset.mimeType || "application/octet-stream",
    }));
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

const andThen = <A, B>(result: Result<A>, next: (value: A) => Result<B>): Result<B> =>
  result.ok ? next(result.value) : result;

/** Upload a document; the server extracts dates later (202 + processing). */
export async function uploadDocument(api: Api, asset: DocumentPickerAsset) {
  const form = new FormData();
  await appendAssetToForm(form, asset, api.deps);
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  // No manual Content-Type: fetch sets the multipart boundary.
  const result = await request(api, "/api/v1/documents", {
    method: "POST", body: form, headers: { "X-Timezone": timezone },
  });
  return andThen(result, parseDocumentBody);
}

export async function getDocument(api: Api, id: string) {
  return andThen(await request(api, `/api/v1/documents/${encodeURIComponent(id)}`), parseDocumentBody);
}

export async function confirmDocument(api: Api, id: string) {
  const result = await request(api, `/api/v1/documents/${encodeURIComponent(id)}/confirm`, { method: "POST" });
  return andThen(result, (body) => {
    const document = isRecord(body) ? parseDocument(body.document) : null;
    return document ? { ok: true as const, value: document } : { ok: false as const, message: SHAPE_ERROR };
  });
}

export async function setEventStatus(api: Api, id: string, status: "draft" | "dismissed") {
  const result = await request(api, `/api/v1/events/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  return andThen(result, (body) => {
    const event = parseEvent(body);
    return event ? { ok: true as const, value: event } : { ok: false as const, message: SHAPE_ERROR };
  });
}

export async function listEvents(api: Api, from: Date) {
  const query = new URLSearchParams({ from: from.toISOString(), limit: "100" });
  return andThen(await request(api, `/api/v1/events?${query}`), parseEventsBody);
}
