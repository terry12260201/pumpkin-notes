-- 追加：花名冊 + 種子筆記可先無主人（南瓜第一次登入自動認領）
create table if not exists public.roster (
  email        text primary key,
  display_name text not null,
  department   text default '',
  title        text default ''
);
alter table public.roster enable row level security;
drop policy if exists roster_read on public.roster;
create policy roster_read on public.roster for select using (public.is_allowed());
drop policy if exists roster_owner on public.roster;
create policy roster_owner on public.roster for all using (public.is_owner()) with check (public.is_owner());

alter table public.notes alter column owner_id drop not null;
alter table public.notes add column if not exists owner_email text;
create index if not exists notes_owner_email_idx on public.notes(lower(owner_email));

-- 新使用者：從花名冊帶名字部門；認領 owner_email 等於自己的筆記；南瓜自動成為 owner
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare r record;
begin
  select * into r from public.roster where lower(email) = lower(new.email);
  insert into public.profiles (id, email, display_name, department, title, avatar_url, role)
  values (new.id, new.email,
          coalesce(r.display_name, new.raw_user_meta_data->>'full_name', split_part(new.email,'@',1)),
          coalesce(r.department,''), coalesce(r.title,''),
          new.raw_user_meta_data->>'avatar_url',
          case when lower(new.email) = 'nanhong@pumpkinvrar.com' then 'owner' else 'member' end)
  on conflict (id) do nothing;
  update public.notes set owner_id = new.id where owner_id is null and lower(owner_email) = lower(new.email);
  return new;
end $$;

-- 花名冊資料在 roster.local.sql（含同事信箱，不進 repo）
