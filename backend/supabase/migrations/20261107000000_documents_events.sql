begin;

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  filename text not null check (length(btrim(filename)) between 1 and 255),
  mime_type text not null check (mime_type in (
    'application/pdf', 'image/jpeg', 'image/png', 'image/bmp',
    'image/x-ms-bmp', 'image/tiff'
  )),
  status text not null default 'processing'
    check (status in ('processing', 'review', 'confirmed', 'failed')),
  raw_text text not null check (length(btrim(raw_text)) between 1 and 60000),
  timezone text not null check (length(timezone) between 1 and 100),
  error_code text check (error_code in (
    'extraction_failed', 'invalid_dates', 'worker_timeout'
  )),
  lease_token uuid,
  lease_expires_at timestamptz,
  attempts integer not null default 0 check (attempts between 0 and 3),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, user_id)
);

create table public.events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  document_id uuid,
  title text not null check (length(btrim(title)) between 1 and 300),
  category text not null check (category in ('meeting', 'study', 'deadline', 'other')),
  starts_at timestamptz not null check (isfinite(starts_at)),
  all_day boolean not null default false,
  source text not null default 'manual' check (source in ('extracted', 'manual')),
  status text not null default 'draft' check (status in ('draft', 'confirmed', 'dismissed')),
  reminder_offset_minutes integer not null default 15
    check (reminder_offset_minutes between 0 and 10080),
  job_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (document_id, user_id)
    references public.documents(id, user_id) on delete cascade
);

create table public.device_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  token text not null unique check (
    length(token) <= 255 and token ~ '^Expo(nent)?PushToken\[[A-Za-z0-9_-]+\]$'
  ),
  platform text not null check (platform in ('ios', 'android')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index documents_user_created_idx on public.documents(user_id, created_at, id);
create index documents_pending_idx on public.documents(created_at, id)
  where status = 'processing';
create index events_user_starts_idx on public.events(user_id, starts_at, id);
create index events_document_idx on public.events(document_id, user_id);
create index device_tokens_user_idx on public.device_tokens(user_id);

alter table public.documents enable row level security;
alter table public.events enable row level security;
alter table public.device_tokens enable row level security;

revoke all on public.documents, public.events, public.device_tokens
  from public, anon, authenticated;
grant all on public.documents, public.events, public.device_tokens to service_role;
grant select on public.documents to authenticated;
grant insert (user_id, filename, mime_type, raw_text, timezone)
  on public.documents to authenticated;
grant select, delete on public.events to authenticated;
grant insert (user_id, title, category, starts_at, all_day, reminder_offset_minutes)
  on public.events to authenticated;
grant update (title, category, starts_at, all_day, reminder_offset_minutes, status)
  on public.events to authenticated;
grant select, delete on public.device_tokens to authenticated;
grant insert (user_id, token, platform) on public.device_tokens to authenticated;
grant update (user_id, token, platform) on public.device_tokens to authenticated;

create policy documents_owner_read on public.documents for select to authenticated
  using ((select auth.uid()) = user_id);
create policy documents_owner_insert on public.documents for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy events_owner on public.events for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy device_tokens_owner on public.device_tokens for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create function public.phase3_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end;
$$;
revoke all on function public.phase3_updated_at() from public, anon, authenticated;

create trigger documents_updated_at before update on public.documents
  for each row execute function public.phase3_updated_at();
create trigger events_updated_at before update on public.events
  for each row execute function public.phase3_updated_at();
create trigger device_tokens_updated_at before update on public.device_tokens
  for each row execute function public.phase3_updated_at();

-- Editing a confirmed event always requires a fresh review.
create function public.phase3_event_review()
returns trigger language plpgsql set search_path = '' as $$
begin
  if old.status = 'confirmed' and (
    new.title, new.category, new.starts_at, new.all_day, new.reminder_offset_minutes
  ) is distinct from (
    old.title, old.category, old.starts_at, old.all_day, old.reminder_offset_minutes
  ) then
    new.status := 'draft';
  end if;
  return new;
end;
$$;
revoke all on function public.phase3_event_review() from public, anon, authenticated;
create trigger events_require_review before update on public.events
  for each row execute function public.phase3_event_review();

-- Trigger-only privilege: users cannot directly set document workflow/lease fields.
create function public.phase3_document_review()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  document_uuid uuid;
begin
  if tg_op = 'DELETE' then
    document_uuid := old.document_id;
  else
    document_uuid := new.document_id;
  end if;
  -- Serialize the aggregate status, then read children with a fresh snapshot.
  perform 1 from public.documents where id = document_uuid for update;
  update public.documents d
  set status = case when exists (
    select 1 from public.events e
    where e.document_id = d.id and e.status = 'draft'
  ) then 'review' else 'confirmed' end
  where d.id = document_uuid and d.status in ('review', 'confirmed');
  return null;
end;
$$;
revoke all on function public.phase3_document_review() from public, anon, authenticated;
create trigger events_sync_document after insert or update or delete on public.events
  for each row execute function public.phase3_document_review();

create function public.confirm_document(p_document_id uuid)
returns setof public.documents
language plpgsql security definer set search_path = '' as $$
declare
  document_row public.documents;
begin
  select * into document_row from public.documents
  where id = p_document_id and user_id = (select auth.uid()) for update;
  if not found then
    return;
  end if;
  if document_row.status not in ('review', 'confirmed') then
    raise exception using errcode = 'P0001', message = 'document_not_ready';
  end if;
  update public.events set status = 'confirmed'
  where document_id = document_row.id and user_id = document_row.user_id
    and status = 'draft';
  return query update public.documents set status = 'confirmed'
    where id = document_row.id returning *;
end;
$$;
revoke all on function public.confirm_document(uuid) from public, anon, authenticated;
grant execute on function public.confirm_document(uuid) to authenticated;

commit;
