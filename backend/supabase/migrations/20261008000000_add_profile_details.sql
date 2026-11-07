begin;

alter table public.profiles
  add column time_zones text
    constraint profiles_time_zones_check
    check (length(time_zones) between 1 and 100),
  add column avatar_url text,
  add column pronouns text
    constraint profiles_pronouns_check
    check (length(pronouns) between 1 and 100),
  add column preferred_study_time time without time zone,
  add column reminders_enabled boolean not null default false,
  add column updated_at timestamptz default now();

commit;