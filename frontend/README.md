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

## App flow

`/` (log in or sign up with Supabase email/password) → `/board` (your
upcoming saved events) → `/upload` (upload a document → wait while dates are
extracted → dismiss wrong ones → confirm). Signed-out users are sent back to
`/`.

The app signs in directly with Supabase Auth and sends the session's access
token to the backend on every request; it never sees the service key.
Uploads stay "processing" until someone runs the backend extraction worker
(`venv/bin/python -m backend.document_worker`). Confirming saves the dates;
reminders and push notifications come in Phase 4.

## Environment

Copy `.env.example` to `.env` (ignored by git) and set:

- `EXPO_PUBLIC_API_URL` — backend base URL. Web: `http://localhost:8000`.
  Physical device: `http://<LAN IP>:8000`. Android emulator:
  `http://10.0.2.2:8000`.
- `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_KEY` — the same Supabase
  project as the backend, publishable (anon) key only.

## Commands (run from `frontend/`)

```bash
npm ci                 # install deps
npx expo start         # dev server (src/app routes; no extra config)
npx expo lint          # lint
npx tsc --noEmit       # typecheck (strict, @/ -> ./src/*, @/assets/* -> ./assets/*)
npx tsx --test src/lib/api.test.ts      # offline API client tests
npx expo export --platform web          # static web bundle sanity check
```

From the repo root, `./start.sh` starts Redis/Ollama/the FastAPI
backend and then runs `npm run start` here.

## Verification coverage

API client tests cover URL validation, strict response parsing, bearer
headers, multipart upload without a manual Content-Type, error and
expired-session messages, network failures, and the confirm, dismiss, and
list routes. They do not hit a live Supabase project. Native multipart
upload still needs a device or emulator check.
