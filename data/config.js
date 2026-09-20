/* 小南瓜數位筆記 — 後端設定
   ────────────────────────────────────────────────────────────
   anonKey（publishable key）是「公開金鑰」，本來就設計成寫在前端，
   安全靠 Supabase 的 RLS 政策擋。service_role key 絕對不能放這裡。

   ⚠️ 2026-09-17：這支檔案被我（執行的 AI）誤覆蓋，原本填好的
      sb_publishable_… 金鑰不見了。請南瓜到
      Supabase → Project Settings → API Keys 複製 publishable key 貼回 anonKey。

   沒填 key（或維持 sb_publishable_mYFIBMzzwhkzn-ZKybxjng_ITw0cFN0）時，整個站會自動退回「示範模式」：
   用 data/reports.js 的離線資料 ＋ 這台瀏覽器的 localStorage，file:// 雙擊也能看。
*/
window.PN_CONFIG = {
  url: 'https://xoyalmkdaiehsldbokud.supabase.co',
  anonKey: 'sb_publishable_mYFIBMzzwhkzn-ZKybxjng_ITw0cFN0',
  /* 登入完要導回哪裡（本機開發會自動用 localhost，這個只給正式站用）。
     Supabase → Authentication → URL Configuration 的 Redirect URLs
     要同時填這個網址和 http://localhost:8000/ */
  siteUrl: 'https://terry12260201.github.io/pumpkin-notes/',
  googleEnabled: true    /* 南瓜在 Supabase 開通 Google 登入後改 true */
};
