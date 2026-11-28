create table public.chat_turns (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    student_message text not null,
    assistant_reply text not null,
    created_at timestamptz not null default now()
);

alter table public.chat_turns enable row level security;

create policy "Students can read their own chat turns"
on public.chat_turns for select
to authenticated
using (auth.uid() = user_id);

create policy "Students can save their own chat turns"
on public.chat_turns for insert
to authenticated
with check (auth.uid() = user_id);

create index chat_turns_user_recent_idx
on public.chat_turns (user_id, created_at desc, id desc);