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

## 6. 2026-09-19 收尾狀態（新視窗接手先讀這段）
**已可用**：Google 登入（公司帳號）、信箱連結登入、私人／團隊筆記、收藏、已讀、垃圾桶、換封面（裁切）、書架／標籤改名、收件匣排隊 → 本機整理主機（`worker/`）→ Claude（claude-opus-5）寫報告 → 驗收 → 上架；第一支影片已實測全程通過（接單到上架 1 分 40 秒、約 0.15 美金）。
**設定檔**：`~/.config/pumpkin-notes/config.json` 有 `supabase_service_key`（sb_secret_ 開頭）與 `anthropic_api_key`；不進 repo。
**還沒做／已知問題（照順序）**
1. 雲端筆記的報告頁是舊版樣式（沒有工具列與點格）：`worker.reskin_v03()` 呼叫 `build_v03.reskin_report` 會回空，要查 reskin 對 report_lib 產出的結構假設（可能是 `<article>`／章節標記）。修好後 Storage 上的報告會有收藏／分享／刪除工具列。
2. 截圖與報告存放：目前報告 HTML（含 base64 截圖）與封面存 Supabase Storage（`notes/`、`covers/`），原始幀在本機 `~/PumpkinNotes/work/`。南瓜要求改存公司 Google 雲端：worker 上架後多一步用 Drive API 把 HTML／封面／幀存進指定資料夾（需 service account 或 OAuth 憑證，只有南瓜能給）。
3. 網址不要露出個人 GitHub 帳號：最快是幫 Pages 綁公司網域子網域（例如 notes.pumpkinvr.com，DNS 加 CNAME 指到 terry12260201.github.io，repo Settings → Pages → Custom domain），Supabase 的 Site URL／Redirect URLs 與 `data/config.js` 的 siteUrl 要一起改；或把 repo 轉到公司 GitHub 組織。Cursor Agents 不是網站託管，不適用。
4. 整理主機要 24 小時服務：把 `worker/` 搬到 PC-01 用排程或 launchd 常駐。
5. Obsidian 回寫：南瓜自己的筆記上架後同時 `note_lib.save()` 進 vault（還沒接）。

## 7. 2026-09-20 進度（接手先讀這段，§6 的 1 已完成）
**這輪修好**（commit a2c289d，已上線）
- 雲端筆記點開變原始碼＋亂碼：根因是 Supabase Storage 對 `.html` 一律回 `content-type: text/plain` 且不帶 charset（安全政策，改不了）。解法：`store.noteUrl()` 先 `fetch` 簽名網址，再包成 `text/html;charset=utf-8` 的 Blob 網址交給瀏覽器。CORS 已確認 `access-control-allow-origin: *`。
- `build_v03.reskin_report` 抓不到 `<nav class="toc" id="toc">`（report_lib 產的 nav 帶 id）→ 改 `[^>]*`。第一篇雲端筆記已重新換皮上傳（有工具列＋點格）。
- 快取版本 `?v=20260920a`（index、build_v03、24 篇靜態頁）。

**待辦（照順序）**
1. **公司網域（2026-09-20 進行中，已回退）**：⚠️ 綁上自訂網域後 GitHub 會把 github.io 全部轉向新網域，DNS 沒生效＝整站死。已拆掉綁定、程式退回 github.io。**正確順序：先等 `dig pn.pumpkinvr.com` 查得到 CNAME，再綁。** 南瓜已把 Supabase Site URL 改成 pn（要先改回 github.io，等網域通再改）。原記錄：：定案 `pn.pumpkinvr.com`。已做：GitHub Pages 綁定（repo 有 CNAME 檔）、`data/config.js siteUrl`、`worker.py SITE`、README 全改新網址。**卡在 Wix 的 CNAME 還查不到**（ns0.wixdns.net 直接問也沒有），等南瓜確認記錄；生效後 GitHub 會自動發 HTTPS 憑證（最多 1 小時），再開 `https_enforced`，並請南瓜到 Supabase → Authentication → URL Configuration 把 Site URL 改 `https://pn.pumpkinvr.com/`、Redirect URLs 加同一條。原文：DNS 在 Wix（`ns0/ns1.wixdns.net`）。`notes.pumpkinvr.com` **已有一筆 CNAME 指到 `cname.vercel-dns-0.com`**（目前打不開，疑似舊設定），要南瓜決定：改這筆指到 `terry12260201.github.io`，或另用 `pn.pumpkinvr.com`（目前空著）。DNS 好了之後：`gh api -X PUT repos/terry12260201/pumpkin-notes/pages -f cname=<網域>` → 等 HTTPS 憑證 → 改 `data/config.js siteUrl`、`worker.py SITE`、Supabase Authentication → URL Configuration 的 Site URL 與 Redirect URLs、Google OAuth 同意畫面的授權網域。
2. **Google 雲端存放（規劃定案，待南瓜給憑證）**：在公司 Google Drive 建共用資料夾 `Pumpkin Notes 素材庫/`，底下 `報告HTML/`、`封面/`、`截圖幀/<slug>/`、`夥伴上傳/`；worker 上架後多一步用 Drive API 上傳（HTML、封面 jpg、幀 jpg）。憑證走 **服務帳戶**：GCP 專案 `pumpkin-meeting-platform` → IAM → 服務帳戶 → 建立 → 金鑰 JSON 存 `~/.config/pumpkin-notes/drive_sa.json`；把資料夾分享給服務帳戶信箱（編輯者）即可，不用 domain-wide delegation。夥伴自己拍的照片直接丟 `夥伴上傳/`，worker 之後可掃該夾當錄影檔來源。
3. **24 小時整理主機**：現況 jobs 是排隊制，電腦沒開只是延後不會掉單。路線：短期 Mac → 中期搬 PC-01（launchd／工作排程器常駐）→ 長期租小主機（Hetzner／Oracle 免費層）。GitHub Actions 排程可行但 YouTube 常擋雲端 IP，需 cookies，不建議當主力。
4. Obsidian 回寫（§6 第 5 點）。
5. ✅ 2026-09-20 已合併：墨金 1.2 合併版（公開庫 7ac2da4）；點格預設＝Pumpkin Notes 發亮版、磁吸改選用；四處已同步。原記錄：墨金 skill 有兩份 v1.2 要合併：GPT/Codex 在 `~/GitHub/pumpkin-ink-gold` 工作區寫的（未 commit，`references/ink-gold-ui.js` 磁吸點陣＋Phosphor 圖示＋Logo）與 Fable 在 `~/.claude/skills/pumpkin-ink-gold/references/互動點格與品牌.md` 寫的（Pumpkin Notes 定案參數）。合併後再同步 OB／私有 pumpkin-skills／公開庫。
