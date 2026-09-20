你接手的是「Pumpkin Notes」（南瓜虛擬科技的團隊影片筆記工具）。先讀完這段，再照文件動手，不要憑印象改。

**在哪**
- 程式：`~/pumpkin-digital-notes-v02/` ＝ GitHub `terry12260201/pumpkin-notes`（main 直發 GitHub Pages）
- 正式網址：https://notes.pumpkinvrarai.com/（自訂網域，DNS 在 Cloudflare，舊網址 github.io 自動轉過來）
- 接手文件：`HANDOFF_PROMPT.md`，先讀 §6、§7（現況與待辦）
- 鑰匙全在 `~/.config/pumpkin-notes/config.json`（Supabase service key、Claude API key、Cloudflare DNS token、Google OAuth），不進 repo、不寫進前端

**架構（三層）**
1. 前端：純 HTML／JS 單檔 `index.html`＋`data/store.js`，無框架、無 build；雲端筆記用 fetch 後 `document.write` 原地顯示（不要改回 blob）
2. 後端：Supabase 專案 `pumpkin-notes`（Tokyo）。表：profiles／roster／notes／jobs／favorites／reads／shelves／tag_vocab／allowlist；RLS 全開；登入＝Google（公司網域）＋magic link。Storage：notes（私）、covers（公）、img（公，截圖）、pdf、uploads
3. 整理主機：`worker/worker.py`（南瓜 Mac 上，之後搬 PC-01）。輪詢 jobs → yt-dlp 抓片抽幀 → claude-opus-5 寫報告 → check_report 驗收 → 套 V03 樣式 → 截圖抽出縮成 1280 寬 JPEG q80 上傳 img 桶 → 上架 notes → `drive_store.archive_note` 歸檔到 Google 雲端「Pumpkin Notes 素材庫」→ 刪本機工作夾。規則見 `worker/STORAGE_RULES.md`

**鐵則**
- 視覺一律照墨金 skill `~/.claude/skills/pumpkin-ink-gold/`；互動點格＝磁吸版（ink-gold-ui.js 預設），金色一畫面一顆
- 說「跟 X 一樣」前要實際截圖量過，不能只比程式碼
- 自訂網域順序：DNS 查得到 → 綁 GitHub → 等憑證 → 改 config.js／worker／Supabase URL；順序錯整站會斷
- 對外動作（push 以外：建雲端資源、寄信、邀人）先問南瓜；回報要附連結、講白話、待辦列步驟

**待辦（照序）**：整理主機搬 PC-01 常駐 → 正式 PDF → Obsidian 回寫 → 問整個書架（NotebookLM）→ 分享通知 Telegram → 標籤治理。
