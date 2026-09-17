-- 小南瓜數位筆記 V03 資料層（Supabase / Postgres）
-- 在 Supabase Dashboard → SQL Editor 整段貼上執行；可重複執行。

create extension if not exists "pgcrypto";

-- ── 誰可以進來：公司網域自動放行 ＋ 白名單 ──────────────────────────
create table if not exists public.allowlist (
  email      text primary key,
  added_by   uuid references auth.users(id),
  note       text,
  created_at timestamptz default now()
);

create or replace function public.is_allowed() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(
    (auth.email() ilike '%@pumpkinvrar.com')
    or exists (select 1 from public.allowlist a where lower(a.email) = lower(auth.email())),
    false);
$$;

-- ── 夥伴檔案 ───────────────────────────────────────────────────────
create table if not exists public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  email        text unique not null,
  display_name text not null default '',
  department   text default '',
  title        text default '',
  avatar_url   text,
  role         text not null default 'member' check (role in ('owner','member')),
  created_at   timestamptz default now()
);

-- 登入第一次自動建 profile
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, display_name, avatar_url)
  values (new.id, new.email,
          coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email,'@',1)),
          new.raw_user_meta_data->>'avatar_url')
  on conflict (id) do nothing;
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

create or replace function public.is_owner() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'owner');
$$;

-- ── 書架與標籤詞彙 ─────────────────────────────────────────────────
create table if not exists public.shelves (
  id          text primary key,
  name        text not null,
  emoji       text default '',
  description text default '',
  sort        int default 100
);

create table if not exists public.tag_vocab (
  family   text not null check (family in ('主題','用途','關聯')),
  value    text not null,
  approved boolean default false,
  primary key (family, value)
);

-- ── 筆記 ───────────────────────────────────────────────────────────
create table if not exists public.notes (
  id           uuid primary key default gen_random_uuid(),
  slug         text unique not null,
  owner_id     uuid not null references public.profiles(id) on delete cascade,
  title        text not null,
  speaker      text default '',
  source_kind  text not null default 'youtube' check (source_kind in ('youtube','local','platform')),
  source_url   text,
  duration_sec int default 0,
  read_min     int,
  level        text check (level in ('入門','進階','深入')),
  one_liner    text default '',
  summary      text default '',
  takeaways    jsonb default '[]'::jsonb,   -- ["句1","句2","句3"]
  verdict      jsonb,                        -- {"pill":"值得看原片","why":"…"}
  action       text,
  shelf        text references public.shelves(id),
  section      text,
  tags         text[] default '{}',          -- '主題/AI代理人' 形式
  keywords     text[] default '{}',
  cover_path   text,                         -- storage: covers/<slug>.jpg
  html_path    text,                         -- storage: notes/<owner_id>/<slug>.html
  md_path      text,
  pdf_path     text,
  visibility   text not null default 'private' check (visibility in ('private','team')),
  shared_at    timestamptz,
  shared_note  text,
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);
create index if not exists notes_owner_idx on public.notes(owner_id);
create index if not exists notes_vis_idx   on public.notes(visibility, shared_at desc);
create index if not exists notes_tags_idx  on public.notes using gin(tags);

-- ── 收件匣排隊單 ───────────────────────────────────────────────────
create table if not exists public.jobs (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid not null references public.profiles(id) on delete cascade,
  source_url   text,
  source_kind  text not null default 'youtube' check (source_kind in ('youtube','local','platform')),
  upload_path  text,
  shelf        text,
  level        text,
  auto_share   boolean default false,
  status       text not null default 'queued'
               check (status in ('queued','prepping','writing','checking','publishing','done','failed')),
  progress_msg text default '排隊中',
  note_id      uuid references public.notes(id),
  claimed_by   text,
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);
create index if not exists jobs_status_idx on public.jobs(status, created_at);

-- ── 最愛與閱讀紀錄 ─────────────────────────────────────────────────
create table if not exists public.favorites (
  user_id uuid references public.profiles(id) on delete cascade,
  note_id uuid references public.notes(id) on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, note_id)
);
create table if not exists public.reads (
  user_id     uuid references public.profiles(id) on delete cascade,
  note_id     uuid references public.notes(id) on delete cascade,
  my_takeaway text default '',
  read_at     timestamptz default now(),
  primary key (user_id, note_id)
);

-- updated_at 自動更新
create or replace function public.touch_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists notes_touch on public.notes;
create trigger notes_touch before update on public.notes for each row execute function public.touch_updated_at();
drop trigger if exists jobs_touch on public.jobs;
create trigger jobs_touch before update on public.jobs for each row execute function public.touch_updated_at();

-- ── RLS ────────────────────────────────────────────────────────────
alter table public.allowlist enable row level security;
alter table public.profiles  enable row level security;
alter table public.shelves   enable row level security;
alter table public.tag_vocab enable row level security;
alter table public.notes     enable row level security;
alter table public.jobs      enable row level security;
alter table public.favorites enable row level security;
alter table public.reads     enable row level security;

drop policy if exists allowlist_owner on public.allowlist;
create policy allowlist_owner on public.allowlist for all using (public.is_owner()) with check (public.is_owner());

drop policy if exists profiles_read on public.profiles;
create policy profiles_read on public.profiles for select using (public.is_allowed());
drop policy if exists profiles_self on public.profiles;
create policy profiles_self on public.profiles for update using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists shelves_read on public.shelves;
create policy shelves_read on public.shelves for select using (public.is_allowed());
drop policy if exists shelves_owner on public.shelves;
create policy shelves_owner on public.shelves for all using (public.is_owner()) with check (public.is_owner());

drop policy if exists vocab_read on public.tag_vocab;
create policy vocab_read on public.tag_vocab for select using (public.is_allowed());
drop policy if exists vocab_propose on public.tag_vocab;
create policy vocab_propose on public.tag_vocab for insert with check (public.is_allowed() and approved = false);
drop policy if exists vocab_owner on public.tag_vocab;
create policy vocab_owner on public.tag_vocab for update using (public.is_owner()) with check (public.is_owner());

drop policy if exists notes_read on public.notes;
create policy notes_read on public.notes for select
  using (public.is_allowed() and (owner_id = auth.uid() or visibility = 'team'));
drop policy if exists notes_write on public.notes;
create policy notes_write on public.notes for all
  using (public.is_allowed() and owner_id = auth.uid())
  with check (public.is_allowed() and owner_id = auth.uid());

drop policy if exists jobs_own on public.jobs;
create policy jobs_own on public.jobs for all
  using (public.is_allowed() and owner_id = auth.uid())
  with check (public.is_allowed() and owner_id = auth.uid());
-- worker 用 service_role key 更新狀態，不受 RLS 限制

drop policy if exists fav_own on public.favorites;
create policy fav_own on public.favorites for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists fav_count on public.favorites;
create policy fav_count on public.favorites for select using (public.is_allowed());

drop policy if exists reads_own on public.reads;
create policy reads_own on public.reads for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- ── Realtime（收件匣進度） ─────────────────────────────────────────
do $$ begin
  alter publication supabase_realtime add table public.jobs;
exception when duplicate_object then null; end $$;

-- ── 種子：兩個書架＋現有標籤詞 ─────────────────────────────────────
insert into public.shelves (id,name,emoji,description,sort) values
 ('gaiconf-2026','2026 Generative AI 年會','🎤','年會三場次的演講筆記',10),
 ('youtube','YouTube 精選','📺','值得留下的 YouTube 影片',20),
 ('course','課程平台','🎓','需要登入的線上課程',30),
 ('meeting','會議錄影','🗂️','內部會議與客戶簡報錄影',40)
on conflict (id) do nothing;

insert into public.tag_vocab (family,value,approved) values
 ('主題','AI代理人',true),('主題','Harness工程',true),('主題','VibeCoding',true),('主題','脈絡工程',true),
 ('主題','團隊導入',true),('主題','自動化',true),('主題','資料分析',true),('主題','AI寫作',true),
 ('主題','MCP',true),('主題','成本控管',true),('主題','產品上線',true),('主題','資安邊界',true),
 ('用途','照著做',true),('用途','建立觀念',true),('用途','案例故事',true),('用途','工具評測',true),
 ('關聯','南瓜虛擬',true),('關聯','HEKA',true),('關聯','自動化流程',true),('關聯','家庭',true)
on conflict do nothing;

-- Storage buckets（也可在 Dashboard 建）：covers 公開；notes / pdf / uploads 私有
insert into storage.buckets (id,name,public) values ('covers','covers',true) on conflict (id) do nothing;
insert into storage.buckets (id,name,public) values ('notes','notes',false) on conflict (id) do nothing;
insert into storage.buckets (id,name,public) values ('pdf','pdf',false) on conflict (id) do nothing;
insert into storage.buckets (id,name,public) values ('uploads','uploads',false) on conflict (id) do nothing;

drop policy if exists covers_public_read on storage.objects;
create policy covers_public_read on storage.objects for select using (bucket_id = 'covers');
drop policy if exists private_read on storage.objects;
create policy private_read on storage.objects for select
  using (bucket_id in ('notes','pdf','uploads') and public.is_allowed()
         and (split_part(name,'/',1) = auth.uid()::text
              or exists (select 1 from public.notes n where n.visibility='team'
                         and (n.html_path = name or n.pdf_path = name or n.md_path = name))));
drop policy if exists own_write on storage.objects;
create policy own_write on storage.objects for insert
  with check (public.is_allowed() and split_part(name,'/',1) = auth.uid()::text);
drop policy if exists own_update on storage.objects;
create policy own_update on storage.objects for update
  using (public.is_allowed() and split_part(name,'/',1) = auth.uid()::text);
