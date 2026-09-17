# 接手 Prompt｜小南瓜數位筆記 V03（複製整段給任何 AI）

你接手的是「小南瓜數位筆記 V03」——南瓜虛擬科技的團隊第二大腦工具：把影片（YouTube／課程平台／錄影檔）變成有截圖、時間戳、白話辭典、三句話帶走的圖文筆記；每位夥伴用公司信箱登入，筆記預設私人，可一鍵分享到「團隊共筆」，能匯出 PDF／Markdown／Obsidian 包。你的任務是**在不破壞既有規範的前提下，把它做得更完善**。

## 1. 專案在哪、長什麼樣
- 程式碼：`~/pumpkin-digital-notes-v02/`＝GitHub `terry12260201/pumpkin-notes`（公開，main 根目錄直發 GitHub Pages）
- 線上：https://terry12260201.github.io/pumpkin-notes/
- 結構：`index.html`（單檔殼，hash 路由 `#library` 筆記書架／`#team` 團隊共筆／`#inbox` 收件匣／`#me` 我的）、`data/store.js`（資料層 `PN.store`，雙模式：有 Supabase 設定走雲端，否則 localStorage 示範）、`data/config.js`（Supabase URL＋publishable key，可公開）、`data/reports.js`（離線資料，由 `build_v03.py` 產）、`gaiconf-2026/`＋`youtube/`（12 篇報告 HTML，截圖 base64 內嵌）、`covers/`、`assets/brand/`（公司橫向 Logo 黑 SVG＋白 PNG）、`assets/art/`（墨線插畫）、`supabase/`（schema.sql、schema_patch.sql、seed_notes.sql、SETUP.md）、`_qa/`（驗收截圖）、`README.md`（人話說明）
- 完整架構與文案定案：`~/.claude/plans/https-terry12260201-github-io-pumpkin-d-giggly-wilkes.md`（先讀）
- 產線 skill（影片→報告）：`~/.claude/skills/pumpkin-digital-notes/`（`prep_youtube.py` 備料 → AI 寫 `report_lib.Report` → `check_report.py` 驗收 → `note_lib.py` 回寫 Obsidian → `publish.py`）。**不要改 V01 上線站 `~/pumpkin-digital-notes/`。**

## 2. 後端（Supabase，專案 `pumpkin-notes`，Tokyo）
- URL `https://xoyalmkdaiehsldbokud.supabase.co`；前端只用 publishable key；secret／service_role 一律不進 repo、不寫進前端。
- 表：`profiles`（登入者）、`roster`（16 位夥伴花名冊，第一次登入自動帶名字部門並認領筆記）、`notes`（`visibility` private|team、`html_path` 形如 `static:gaiconf-2026/x.html` 或 Storage 路徑）、`jobs`（收件匣排隊：queued→prepping→writing→checking→publishing→done|failed）、`favorites`、`reads`（含 `my_takeaway`）、`shelves`、`tag_vocab`、`allowlist`。
- 權限：`is_allowed()`＝信箱以 `@pumpkinvrar.com` 結尾或在 `allowlist`；RLS 全開；南瓜（nanhong@）登入即 owner。
- 登入：Email magic link 已開；**Google 登入待南瓜貼 OAuth Client**（Authentication → Sign In / Providers → Google）。
- Storage buckets：`covers`（公開）、`notes`／`pdf`／`uploads`（私有，簽名網址）。

## 3. 設計規範（必守，違反視為失敗）
- 視覺＝「南瓜墨金美學」：`~/.claude/skills/pumpkin-ink-gold/SKILL.md`。重點：紙底 `#F5F5F5`／墨 `#161415` 一色靠透明度分層／金 `#FDC302` **一個畫面只一顆**（通常是「＋ 新增筆記」或「開始整理」）／白卡 18px 圓角＋1px 8% 髮絲線、不用厚陰影／深炭舞台一頁 ≤2 塊／中文不斜體不負字距／UI 圖示用 SVG sprite、不用彩色 emoji／夜間版 `body[data-theme="night"]`。
- 交付前用墨金驗收清單自評 ≥90；日夜兩版、1440 與 375 寬都要截圖放 `_qa/`。
- 文案語氣：專業但好讀、台灣用語、一句一個意思；既有文案表在計畫檔 §4，改文案要對齊語氣。
- 純前端：不引入框架、不加 build 工具；外部只允許 Google Fonts 與 `cdn.jsdelivr.net` 的 supabase-js。`file://` 雙擊要能開（無 key 時退回示範模式）。
- 對外動作（push、建雲端資源、寄信、邀請使用者）先問南瓜。

## 4. 現況與待辦（照優先序）
1. **Phase 3 產線接通**：寫 `scripts/worker.py`（放進 skill）：輪詢 `jobs.status='queued'` → `prep_youtube.py` → 用 Claude Code／Codex 依 skill 寫報告 → `check_report.py` → 上傳 HTML／封面／MD 到 Storage → 更新 `notes` → 南瓜自己的單同時 `note_lib.save()` 回寫 Obsidian；用 service_role key（放 `~/.config/pumpkin-notes/config.json`）。先在南瓜 Mac 手動跑，之後搬 PC-01 常駐。
2. **正式 PDF**：worker 端 headless Chrome 產 PDF 存 `pdf/`，前端「匯出 PDF」優先開 Storage 檔，沒有才 `window.print()`。
3. **Obsidian 包**：把報告轉成 Markdown＋封面 zip；南瓜的走 vault 直寫，夥伴的下載。
4. **問整個書架**：接 NotebookLM（本機有 MCP）或向量搜尋，讓團隊書架可問答。
5. **通知**：有人分享到團隊 → Telegram 公告（既有機器人在 PC-01）；每週一寄「本週團隊新增 N 篇」。
6. **標籤治理**：`tag_vocab` 夥伴提案、南瓜核准；前端加「提議新標籤」。
7. 小修：卡片 hover 預覽三句話帶走；「兩篇一起讀」並排比較；年度小結真資料。

## 5. 交付格式
每輪結束回報：改了哪些檔、怎麼驗證（截圖路徑、console 無紅字、`check_report.py` 全綠）、還沒做到的項目。誠實，不美化。
