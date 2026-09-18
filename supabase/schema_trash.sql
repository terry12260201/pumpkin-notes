-- 垃圾桶：軟刪除、保留 14 天、記錄誰刪的；團隊共筆夥伴都可復原
alter table public.notes add column if not exists deleted_at timestamptz;
alter table public.notes add column if not exists deleted_by uuid references public.profiles(id);
alter table public.notes add column if not exists deleted_by_name text;
create index if not exists notes_deleted_idx on public.notes(deleted_at);

drop policy if exists notes_restore on public.notes;
create policy notes_restore on public.notes for update
  using (public.is_allowed() and visibility = 'team' and deleted_at is not null)
  with check (public.is_allowed() and visibility = 'team' and deleted_at is null);

-- owner 還沒登入認領（owner_id 空、owner_email 是自己）時也能操作自己的筆記
drop policy if exists notes_write_email on public.notes;
create policy notes_write_email on public.notes for update
  using (public.is_allowed() and owner_id is null and lower(owner_email) = lower(auth.email()))
  with check (public.is_allowed() and owner_id is null and lower(owner_email) = lower(auth.email()));

-- 每天 03:30 清掉超過 14 天的
create extension if not exists pg_cron;
select cron.schedule('purge-trashed-notes', '30 3 * * *',
  $$delete from public.notes where deleted_at is not null and deleted_at < now() - interval '14 days'$$);
