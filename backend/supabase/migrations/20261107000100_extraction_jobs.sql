begin;

-- A document is the durable job. A worker never stores a caller's access token.
create function public.claim_document_job()
returns setof public.documents
language plpgsql security definer set search_path = '' as $$
declare
  document_uuid uuid;
begin
  update public.documents
  set status = 'failed', error_code = 'worker_timeout',
      lease_token = null, lease_expires_at = null
  where status = 'processing' and attempts >= 3 and lease_expires_at <= now();

  select id into document_uuid from public.documents
  where status = 'processing' and attempts < 3
    and (lease_expires_at is null or lease_expires_at <= now())
  order by created_at, id
  for update skip locked limit 1;
  if not found then
    return;
  end if;
  return query update public.documents
  set lease_token = gen_random_uuid(),
      lease_expires_at = now() + interval '15 minutes',
      attempts = attempts + 1, error_code = null
  where id = document_uuid returning *;
end;
$$;
revoke all on function public.claim_document_job() from public, anon, authenticated;
grant execute on function public.claim_document_job() to service_role;

create function public.complete_document_job(
  p_document_id uuid, p_lease_token uuid, p_events jsonb
)
returns boolean
language plpgsql security definer set search_path = '' as $$
declare
  document_row public.documents;
begin
  select * into document_row from public.documents
  where id = p_document_id and status = 'processing'
    and lease_token = p_lease_token and lease_expires_at > now()
  for update;
  if not found then
    return false;
  end if;
  if p_events is null or jsonb_typeof(p_events) <> 'array' then
    raise exception using errcode = '22023', message = 'events_must_be_array';
  end if;
  if jsonb_array_length(p_events) > 500 then
    raise exception using errcode = '22023', message = 'too_many_events';
  end if;
  insert into public.events (
    user_id, document_id, title, category, starts_at, all_day, source
  )
  select document_row.user_id, document_row.id,
    e->>'title', e->>'category', (e->>'starts_at')::timestamptz,
    (e->>'all_day')::boolean, 'extracted'
  from jsonb_array_elements(p_events) as e;
  update public.documents
  set status = 'review', error_code = null,
      lease_token = null, lease_expires_at = null
  where id = document_row.id;
  return true;
end;
$$;
revoke all on function public.complete_document_job(uuid, uuid, jsonb)
  from public, anon, authenticated;
grant execute on function public.complete_document_job(uuid, uuid, jsonb)
  to service_role;

create function public.fail_document_job(
  p_document_id uuid, p_lease_token uuid, p_error_code text
)
returns boolean
language plpgsql security definer set search_path = '' as $$
declare
  changed_rows integer;
begin
  update public.documents
  set status = 'failed',
      error_code = case when p_error_code = 'invalid_dates'
        then 'invalid_dates' else 'extraction_failed' end,
      lease_token = null, lease_expires_at = null
  where id = p_document_id and status = 'processing'
    and lease_token = p_lease_token and lease_expires_at > now();
  get diagnostics changed_rows = row_count;
  return changed_rows = 1;
end;
$$;
revoke all on function public.fail_document_job(uuid, uuid, text)
  from public, anon, authenticated;
grant execute on function public.fail_document_job(uuid, uuid, text)
  to service_role;

commit;
