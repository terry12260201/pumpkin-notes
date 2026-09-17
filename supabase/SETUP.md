# Supabase 設定（南瓜親手做，約 15 分鐘）

> 做完把「專案網址」與「anon key」貼給執行 AI 即可；其他都不用給。**service_role key 只放本機 worker 的 `~/.config/pumpkin-notes/config.json`，不進 repo。**

## 1. 建專案
1. https://supabase.com/dashboard → New project
   - Name：`pumpkin-notes`
   - Region：`Northeast Asia (Tokyo)`
   - Database password：自己保管（之後用不到）
2. 等 2 分鐘建好 → 左側 **Project Settings → API**，記下：
   - `Project URL`（形如 `https://xxxx.supabase.co`）
   - `anon public` key

## 2. 建資料表
1. 左側 **SQL Editor → New query**
2. 把 `supabase/schema.sql` 整段貼上 → **Run**（跑完應顯示 Success，可重複跑）

## 3. 開 Google 登入
1. https://console.cloud.google.com → 選南瓜的 Workspace 專案 → **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type：Web application
   - Name：`pumpkin-notes`
   - Authorized redirect URIs：`https://<你的專案id>.supabase.co/auth/v1/callback`
   - 記下 Client ID / Client Secret
2. 回 Supabase → **Authentication → Providers → Google** → Enable，貼上 Client ID / Secret → Save
3. **Authentication → URL Configuration**
   - Site URL：正式網址（先填 `http://localhost:8000`，上線後改 GitHub Pages 網址）
   - Redirect URLs：加 `http://localhost:8000/**` 與之後的 Pages 網址 `/**`

## 4. 把自己設成 owner（登入一次之後）
SQL Editor 執行：
```sql
update public.profiles set role='owner', display_name='南瓜', department='管理層', title='美術總監／PM'
where email='nanhong@pumpkinvrar.com';
```

## 5. 加白名單（HEKA 或外部夥伴才需要）
```sql
insert into public.allowlist (email, note) values ('someone@example.com','HEKA 同事');
```
公司信箱 `@pumpkinvrar.com` 不用加，登入就放行。

## 6. 交給執行 AI 的兩個值
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
```
