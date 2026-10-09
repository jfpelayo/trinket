begin;

alter table public.profiles
  rename column time_zones to timezone;

-- Fill any missing timestamps before making the column required.
update public.profiles
set updated_at = coalesce(created_at, now())
where updated_at is null;

alter table public.profiles
  alter column updated_at set default now(),
  alter column updated_at set not null;

-- Add optional chatbot preferences.
alter table public.profiles
  add column communication_style text
    check (communication_style in ('concise', 'detailed', 'balanced')),
  add column motivation_style text
    check (motivation_style in (
      'encouragement', 'accountability', 'small_challenges'
    )),
  add column focus_session_minutes integer
    check (focus_session_minutes between 5 and 180),
  add column onboarding_completed_at timestamptz;

-- Automatically update the timestamp when a profile changes.
create function public.set_profile_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger profiles_set_updated_at
before update on public.profiles
for each row
execute function public.set_profile_updated_at();

commit;