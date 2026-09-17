# 🎃 小南瓜數位筆記 V03｜看一支影片的時間，換一疊帶得走的筆記。

這是南瓜虛擬科技的「影片 → 圖文筆記 → 第二大腦」工具。貼上 YouTube、課程連結或錄影檔，
小南瓜會把它整理成有截圖、有時間戳、有白話辭典的圖文筆記；整理完是你自己的，
覺得好再一鍵分享給夥伴。

## 怎麼用（夥伴版）
1. 打開 `index.html`（雙擊就能開，離線也行）。
2. **筆記書架**：上排選書架、下排選主題；工具列可依難度／用途／關聯篩選，也可以只看「團隊分享」「我的最愛」「未讀」。
3. **收件匣**：貼網址或拖進 .mp4／.mov → 按「開始整理」→ 看五段進度（排隊 → 備料 → AI 寫作 → 驗收 → 上架）。
4. 打開一篇筆記：先看「一句話大綱」，截圖旁的 ▶ 可跳回原片，點線底的詞有白話解釋，最後是「三句話帶走」。
5. 筆記頁右上：♥ 最愛、分享給團隊（附一句為什麼推薦）、匯出 PDF、複製 Markdown、下載 Obsidian 包。
6. 右上 ☀／☾ 切換日夜模式。

## 目前階段
| 階段 | 內容 | 狀態 |
|---|---|---|
| Phase 1 | 前端殼：書架／團隊／收件匣／我的、深淺色、分頁、匯出 | ✅ 本版 |
| Phase 2 | 公司信箱登入（Supabase）、私人／團隊筆記真資料、收件匣真排隊 | 🔧 設定步驟見 `supabase/SETUP.md` |
| Phase 3 | 貼網址後機器自動跑整理（本機 worker） | ⏳ 下一輪 |

Phase 1 的「夥伴」與「團隊分享」是示意資料，登入功能接上後會換成真的。

## 給維護者
- 資料來源：`~/pumpkin-digital-notes/reports.json`（V01 上線站，只讀）。
- 重新產出：`python3 build_v03.py` → 更新 `data/reports.js`、換皮所有報告頁（補 `pn:` meta 與「三句話帶走」）。
- 首頁 `index.html` 手寫，不由 build 產生；資料層在 `data/store.js`（Phase 2 換成 Supabase 版，介面不變）。
- 視覺規範：`~/.claude/skills/pumpkin-ink-gold/`；公司 Logo 在 `assets/brand/`。
- 驗收：`python3 ~/.claude/skills/pumpkin-digital-notes/scripts/check_report.py <報告.html>`；截圖在 `_qa/`。
- 完整架構計畫：`~/.claude/plans/https-terry12260201-github-io-pumpkin-d-giggly-wilkes.md`。


## 墨金目錄校準 1.1（2026-09-17）

首頁換成1200px內容、浮動深炭導覽、三欄橫式筆記卡；搜尋獨立放在區段標題旁，進階篩選可展開。
新增 `assets/directory-v1.1.css` 與 `assets/marks/` 原創主題圖示。原始資料、筆記內頁與封面均未改寫。
首頁正本仍是手寫 `index.html`；不要用舊備份重建覆蓋。舊版首頁備份在 `_qa/index-before-ink-gold-v1.1.html`。
本次localhost響應式與操作檢查完成；file://被自動瀏覽器規則封鎖，尚未完成雙擊驗證。正式登入與收件匣後端仍屬既有待實作範圍。
