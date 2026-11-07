import { useMemo } from "react";

import { type Api, getApiBase } from "@/lib/api";
import { useSession } from "@/lib/supabase";

export type ApiState =
  | { kind: "loading" }
  | { kind: "signedOut" }
  | { kind: "misconfigured"; message: string }
  | { kind: "ready"; api: Api };

/** Backend client for the signed-in user, or why one is unavailable. */
export function useApi(): ApiState {
  const session = useSession();
  const token = session?.access_token;
  return useMemo(() => {
    if (session === undefined) return { kind: "loading" };
    if (!token) return { kind: "signedOut" };
    const base = getApiBase();
    if (!base) {
      return {
        kind: "misconfigured",
        message:
          "EXPO_PUBLIC_API_URL is missing or invalid. Set an absolute http(s) URL in frontend/.env and restart Expo.",
      };
    }
    return { kind: "ready", api: { base, token } };
  }, [session, token]);
}
