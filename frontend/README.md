# Trinket frontend

Canonical Expo (SDK 57) app for Trinket. Consolidated on branch
`feat/frontend-consolidation` from two source branches:

- `origin/athena` `589513c` — quest board UI (`src/app/index.tsx`,
  `src/components/board.tsx`, `src/components/task.tsx`) and
  `assets/images/onboarding-bg.svg`, `mappaper.png`.
- `origin/Brian` `a098739` — login UI (`frontend/src/app/index.tsx`),
  parchment/wood assets (`login-page.png`, `password.png`,
  `username.png`, `welcome.png`, `woodtexture1.png`,
  `woodtexture2.png`, `darkwoodtexture.png`, `mappaper.png`), and the
  `@expo-google-fonts/pirata-one` font package. (Both branches have a
  `mappaper.png`; they differ — Brian's was kept since the login
  fields depend on it.)

## Preview flow

`/` (login preview) → "Preview app (no sign-in)" → `/board` (sample
quests, local only) → `/upload` (document → draft events).

**Nothing here signs in or saves.** The login fields are a visual
preview only — Supabase auth is not wired up, Log In/Sign Up are
disabled, and credentials are never sent, logged, or passed between
routes. Board tasks are static samples. Uploaded documents produce
draft events for review only; they are not saved or scheduled and no
push notification is requested or sent.

## Environment

Copy `.env.example` to `.env` (ignored by git) and set:

- `EXPO_PUBLIC_API_URL` — public backend base URL (not a secret).
  Web: `http://localhost:8000`. Physical device: `http://<LAN IP>:8000`.
  Android emulator: `http://10.0.2.2:8000`. The upload screen appends
  `/api/v1/upload` and shows an inline hint when it is unset.

## Commands (run from `frontend/`)

```bash
npm ci                 # install deps
npx expo start         # dev server (src/app routes; no extra config)
npx expo lint          # lint
npx tsc --noEmit       # typecheck (strict, @/ -> ./src/*, @/assets/* -> ./assets/*)
npx tsx --test src/lib/upload.test.ts   # offline helper tests
npx expo export --platform web          # static web bundle sanity check
```

From the repo root, `./start.sh` starts Redis/Ollama/the FastAPI
backend and then runs `npm run start` here.

## Verification coverage

Helper tests cover the API base URL trimming/missing value, success
event parsing, malformed/4xx/502 backend error mapping, network
failure, and that no device token is sent. They do not exercise real
frontend sign-in, persistence, or push. The backend's authenticated
profiles API already exists; connecting it to this UI is separate work.
Native multipart byte transport still needs a device/emulator check.

The web export, typecheck, lint, and helper tests pass. Expo's
compatibility check still flags existing SDK 57 patch-version drift.
The dependency audit also reports vulnerabilities, including high and
critical findings. Neither dependency remediation nor production
readiness is established by this consolidation.
