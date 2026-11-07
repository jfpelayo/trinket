-- Run after phase3_bootstrap.sql on the same disposable PostgreSQL instance.
\set ON_ERROR_STOP on
begin;
create function public.phase3_assert(ok boolean, label text)
returns void language plpgsql as $$
begin
  if ok is distinct from true then
    raise exception 'Phase 3 regression: %', label;
  end if;
end;
$$;
grant execute on function public.phase3_assert(boolean, text)
  to authenticated, service_role;
insert into auth.users(id) values
  ('11111111-1111-4111-8111-111111111111'),
  ('22222222-2222-4222-8222-222222222222');

set local role authenticated;
select set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
insert into public.documents(filename, mime_type, raw_text, timezone)
values ('a.pdf', 'application/pdf', 'Sample deadline', 'America/Los_Angeles')
returning id as a_doc \gset
select public.phase3_assert(
  not has_column_privilege('authenticated', 'public.documents', 'status', 'UPDATE'),
  'document workflow cannot be forged'
);
select public.phase3_assert(
  not has_column_privilege('authenticated', 'public.events', 'document_id', 'INSERT'),
  'manual events cannot forge a document link'
);
select public.phase3_assert(
  not has_function_privilege('authenticated', 'public.claim_document_job()', 'EXECUTE')
  and not has_function_privilege('anon', 'public.claim_document_job()', 'EXECUTE'),
  'worker RPCs are not callable by users'
);
select public.phase3_assert(
  not has_function_privilege(
    'authenticated', 'public.complete_document_job(uuid,uuid,jsonb)', 'EXECUTE'
  ) and not has_function_privilege(
    'authenticated', 'public.fail_document_job(uuid,uuid,text)', 'EXECUTE'
  ), 'worker completion/failure are privileged'
);
select public.phase3_assert(
  not has_table_privilege('anon', 'public.documents', 'SELECT')
  and not has_table_privilege('anon', 'public.events', 'SELECT')
  and not has_table_privilege('anon', 'public.device_tokens', 'SELECT'),
  'anonymous roles have no table reads'
);

select set_config('request.jwt.claim.sub', '22222222-2222-4222-8222-222222222222', true);
select public.phase3_assert((select count(*) = 0 from public.documents), 'B cannot read A');
select public.phase3_assert(
  (select count(*) = 0 from public.confirm_document(:'a_doc')),
  'B cannot confirm A document'
);
insert into public.documents(filename, mime_type, raw_text, timezone)
values ('b.pdf', 'application/pdf', 'Another deadline', 'UTC')
returning id as b_doc \gset

reset role;
set local role service_role;
update public.documents set created_at = now() - interval '1 day' where id = :'a_doc';
select id as job_id, lease_token as first_lease from public.claim_document_job() \gset
select public.phase3_assert(:'job_id' = :'a_doc', 'oldest document claimed');
select public.phase3_assert(
  not public.complete_document_job(
    :'a_doc', '00000000-0000-4000-8000-000000000000', '[]'
  ), 'wrong lease cannot complete'
);
select public.phase3_assert(
  public.complete_document_job(:'a_doc', :'first_lease',
    '[{"title":"Deadline","category":"deadline","starts_at":"2026-12-01T18:00:00Z","all_day":false}]'),
  'worker saves drafts'
);
select public.phase3_assert(
  not public.complete_document_job(:'a_doc', :'first_lease', '[]'),
  'duplicate completion is harmless'
);
select public.phase3_assert(
  (select status = 'review' from public.documents where id = :'a_doc')
  and (select count(*) = 1 from public.events where document_id = :'a_doc'),
  'document and single event committed together'
);
select id as second_job from public.claim_document_job() \gset
select public.phase3_assert(:'second_job' = :'b_doc', 'next document claimed');

do $$
begin
  begin
    perform public.complete_document_job(
      (select id from public.documents where filename = 'b.pdf'),
      (select lease_token from public.documents where filename = 'b.pdf'),
      '[{"title":"Valid","category":"study","starts_at":"2026-12-01T00:00:00Z","all_day":true},
        {"title":"Invalid","category":"unsupported","starts_at":"2026-12-02T00:00:00Z","all_day":true}]'
    );
    raise exception 'Expected invalid batch to fail';
  exception when check_violation then null;
  end;
  begin
    insert into public.events(user_id, document_id, title, category, starts_at)
    values (
      '11111111-1111-4111-8111-111111111111',
      (select id from public.documents where filename = 'b.pdf'),
      'Cross-owner', 'other', '2026-12-01T00:00:00Z'
    );
    raise exception 'Expected ownership foreign key to fail';
  exception when foreign_key_violation then null;
  end;
end;
$$;
select public.phase3_assert(
  (select count(*) = 0 from public.events where document_id = :'b_doc')
  and (select status = 'processing' from public.documents where id = :'b_doc'),
  'invalid batch rolls back events and status'
);
select public.phase3_assert(
  public.complete_document_job(
    :'b_doc', (select lease_token from public.documents where id = :'b_doc'), '[]'
  ), 'genuinely empty extraction can enter review'
);

reset role;
set local role authenticated;
select set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
select public.phase3_assert((select count(*) = 1 from public.documents), 'A sees only A');
select public.phase3_assert((select count(*) = 1 from public.events), 'event RLS scopes A');
select public.phase3_assert(
  (select status = 'confirmed' from public.confirm_document(:'a_doc')),
  'document confirmation succeeds'
);
select public.phase3_assert(
  (select status = 'confirmed' from public.confirm_document(:'a_doc'))
  and (select bool_and(status = 'confirmed' and job_id is null) from public.events),
  'confirmation is idempotent and does not schedule'
);
update public.events set title = 'Corrected deadline' where document_id = :'a_doc';
select public.phase3_assert(
  (select status = 'draft' from public.events where document_id = :'a_doc')
  and (select status = 'review' from public.documents where id = :'a_doc'),
  'editing confirmed content invalidates review'
);
update public.events set status = 'dismissed' where document_id = :'a_doc';
select public.phase3_assert(
  (select status = 'confirmed' from public.confirm_document(:'a_doc'))
  and (select status = 'dismissed' from public.events where document_id = :'a_doc'),
  'confirmation never resurrects dismissed events'
);
insert into public.device_tokens(token, platform)
values ('ExponentPushToken[test-device]', 'ios');
select set_config('request.jwt.claim.sub', '22222222-2222-4222-8222-222222222222', true);
select public.phase3_assert(
  (select count(*) = 0 from public.device_tokens), 'device RLS hides A token'
);
do $$
begin
  begin
    insert into public.device_tokens(user_id, token, platform)
    values ('22222222-2222-4222-8222-222222222222', 'ExponentPushToken[test-device]', 'android')
    on conflict (token) do update
    set user_id = excluded.user_id, token = excluded.token, platform = excluded.platform;
    raise exception 'Expected cross-owner token takeover to fail';
  exception when insufficient_privilege then null;
  end;
end;
$$;

select set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
insert into public.documents(filename, mime_type, raw_text, timezone)
values ('stale.pdf', 'application/pdf', 'Lease recovery example', 'UTC')
returning id as stale_doc \gset
reset role;
set local role service_role;
select lease_token as stale_lease from public.claim_document_job() \gset
select public.phase3_assert(
  (select count(*) = 0 from public.claim_document_job()), 'active lease is exclusive'
);
update public.documents set lease_expires_at = now() - interval '1 second'
where id = :'stale_doc';
select lease_token as reclaimed_lease from public.claim_document_job() \gset
select public.phase3_assert(
  :'stale_lease' <> :'reclaimed_lease'
  and not public.complete_document_job(:'stale_doc', :'stale_lease', '[]')
  and not public.fail_document_job(:'stale_doc', :'stale_lease', 'invalid_dates'),
  'reclaimed lease fences stale completion and failure'
);
update public.documents set lease_expires_at = now() - interval '1 second'
where id = :'stale_doc';
select public.phase3_assert(
  (select attempts = 3 from public.claim_document_job()), 'third attempt permitted'
);
update public.documents set lease_expires_at = now() - interval '1 second'
where id = :'stale_doc';
select public.phase3_assert(
  (select count(*) = 0 from public.claim_document_job()), 'retry cap enforced'
);
select public.phase3_assert(
  (select status = 'failed' and error_code = 'worker_timeout' and lease_token is null
   from public.documents where id = :'stale_doc'), 'abandoned job fails explicitly'
);
reset role;
rollback;
\echo Phase 3 SQL regression checks passed.
