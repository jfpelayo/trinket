-- ONLY for a fresh, disposable PostgreSQL instance, never a Supabase project.
-- Minimal Supabase role/auth fixtures; real auth verification is tested in Python.
\set ON_ERROR_STOP on
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
create schema auth;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;
grant usage on schema public, auth to anon, authenticated, service_role;
grant execute on function auth.uid() to authenticated, service_role;
\ir ../supabase/migrations/20261004000100_create_profiles.sql
\ir ../supabase/migrations/20261008000000_add_profile_details.sql
\ir ../supabase/migrations/20261008000100_extend_profiles.sql
\ir ../supabase/migrations/20261107000000_documents_events.sql
\ir ../supabase/migrations/20261107000100_extraction_jobs.sql
