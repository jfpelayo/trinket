# Frontend integration notes (unsent handoff)

This document is a local handoff note for the team — it is **not** a
sent message and has not been delivered to anyone.

## Where frontend work now lives

All future frontend work should be based on branch
`feat/frontend-consolidation` in this repo, inside `frontend/`. The
Expo project is canonical here — `app.json`, `package.json`, and the
strict `tsconfig.json` path aliases (`@/*` → `./src/*`,
`@/assets/*` → `./assets/*`) are already correct. Nothing needs to
move to the repo root, and no custom Expo app-directory config is
required: `src/app/` is the router root, so `cd frontend && npx expo
start` is sufficient.

## What was ported (selective, not a merge)

- From `origin/athena` (`589513c`): quest board screen and
  `components/board.tsx` / `components/task.tsx`, plus
  `assets/images/onboarding-bg.svg`.
- From `origin/Brian` (`a098739`): the login screen UI and parchment /
  wood texture assets, including his version of `mappaper.png`, plus
  `@expo-google-fonts/pirata-one`.
- Upload screen ported from the legacy `ClientApp/src/app/index.tsx`
  functionality into `frontend/src/app/upload.tsx` with helpers in
  `frontend/src/lib/upload.ts`.

The earlier `ClientApp/` tree is kept on disk locally but is no
longer tracked — treat `frontend/` as the only app going forward.

## Current boundaries

- Login uses real Supabase email/password auth (set the env values in
  `.env.example`). The board shows the signed-in user's saved events.
- Upload → review → confirm uses the Phase 3 backend routes. Extraction
  needs the backend worker running on a team-controlled machine.
- Reminders and push notifications are Phase 4.
- Production model host is unresolved; free-only controlled infra.
