# 帳號怎麼記錄、AI 怎麼接（V03 定案）

## 一、帳號與每個人的資料（已實作）

登入走 Supabase Auth。**每個人一個帳號，資料靠「使用者 id」分開**，不是靠瀏覽器、也不是靠信箱字串。

| 表 | 記什麼 | 誰看得到 |
|---|---|---|
| `auth.users` | Supabase 自己管的登入帳號（信箱、登入方式、最後登入） | 只有系統 |
| `roster` | 16 位夥伴花名冊：信箱 → 名字、部門、職稱（本機 `roster.local.sql`，不進 repo） | 登入者可讀 |
| `profiles` | 每位登入過的人一筆：顯示名、部門、職稱、頭像、角色（owner / member）。**第一次登入自動從花名冊帶入** | 全公司可讀，只能改自己 |
| `notes` | 每篇筆記：`owner_id`＝誰整理的、`visibility` private/team、封面、標籤、書架、刪除時間與刪除者 | 自己的全部 + 團隊分享的 |
| `favorites` | 誰收藏了哪篇 | 只有自己 |
| `reads` | 誰讀過哪篇、「我的一句話」 | 只有自己 |
| `jobs` | 誰貼了哪支影片排隊、進度到哪 | 只有自己 |
| `shelves` / `tag_vocab` | 書架名稱、標籤詞彙（owner 可改名，改了全站同步） | 全公司可讀 |

**規則**
- 誰能進來：信箱以 `@pumpkinvrar.com` 結尾自動放行；其他信箱要在 `allowlist` 表。
- 誰是 owner：`nanhong@pumpkinvrar.com` 第一次登入自動設 owner；owner 可改書架名、標籤名、白名單。
- 12 篇舊筆記目前 `owner_email` 是南瓜，南瓜登入那一刻會自動認領到他的 `owner_id` 名下。
- 資料分隔靠資料庫的 Row Level Security，不是前端判斷；就算改前端程式也看不到別人的私人筆記。

### 登入方式的現況（重要）
| 方式 | 狀態 | 誰能用 |
|---|---|---|
| 信箱登入連結（magic link） | 已開、已測試寄出成功 | **只有南瓜**。Supabase 內建寄信只寄給 Supabase 組織成員，且每小時 2 封 |
| Google 登入 | 待南瓜貼 Client ID／Secret | 全公司 16 人 |
| 自訂 SMTP（Resend 免費方案） | 待南瓜貼 API key | 全公司 16 人（信箱連結） |

所以「每位夥伴都能登入」有兩條路，**擇一**，都只有南瓜能做（需要憑證）：
1. **Google 登入（推薦，5 分鐘）**：Google Cloud Console → OAuth client（Web）→ redirect URI 填 `https://xoyalmkdaiehsldbokud.supabase.co/auth/v1/callback` → 回 Supabase Authentication → Sign In / Providers → Google 貼上。
2. **Resend SMTP**：resend.com 註冊 → 驗證網域 pumpkinvrar.com → 拿 API key → Supabase Project Settings → Authentication → SMTP Settings 填 `smtp.resend.com` / 465 / user `resend` / password＝API key。

## 二、AI 整理筆記怎麼接（Phase 3 設計，下一輪實作）

**選型**：Claude API，模型 `claude-opus-5`，`output_config.effort = "high"`，adaptive thinking（預設開）。串流輸出避免逾時。

**跑在哪**：本機 worker（先南瓜的 Mac，之後 PC-01 常駐），因為要下載影片、抽幀、需要登入的課程平台只有本機做得到。前端只負責「貼網址→寫 jobs 表」。

**流程**（`scripts/worker.py`，放進 `pumpkin-digital-notes` skill）
```
每 30 秒查 jobs.status='queued'
 → 標 prepping：prep_youtube.py（yt-dlp 下載、字幕、抽幀、縮圖總表）
 → 標 writing：把 subs.txt ＋ 12～18 張關鍵幀（base64 image）＋ 報告規格 送 Claude API
     system：報告規格（封面、截圖＝重點、時間戳、辭典、三句話帶走、一主題一用途標籤）
     output_config.format：JSON schema（title / one_liner / sections[] / glossary[] / takeaways / tags / level）
 → 標 checking：report_lib 組 HTML → check_report.py 驗收，紅燈就帶錯誤回頭再請 AI 修一次（最多 2 次）
 → 標 publishing：上傳 HTML／封面／MD 到 Storage → 寫 notes（owner_id＝jobs.owner_id）
 → 標 done；失敗標 failed 並把原因寫進 progress_msg（前端會顯示）
```
南瓜自己的單同時 `note_lib.save()` 回寫 Obsidian；夥伴的單只上雲端，他們用「下載 Obsidian 包」自己收。

**金鑰放哪**：`~/.config/pumpkin-notes/config.json` 加 `anthropic_api_key` 與 `supabase_service_role_key`；只在 worker 那台機器，不進 repo、不進前端。

**成本估算**（Opus 5：輸入 $5／百萬 token、輸出 $25／百萬 token）
- 一支 20 分鐘影片：字幕約 6k token ＋ 16 張圖約 25k token ＋ 規格 3k ＝ 輸入約 35k；輸出約 8k。
- 約 **$0.4 美金／篇**（含一次驗收重跑約 $0.7）。16 人每人每週 2 篇 ≈ 每月 $50～$90。
- 報告規格放 system 並開 prompt caching，重複部分打 1 折。

**Python 呼叫骨架**
```python
import anthropic, base64, json
client = anthropic.Anthropic()  # 讀 ANTHROPIC_API_KEY
with client.messages.stream(
    model="claude-opus-5",
    max_tokens=32000,
    output_config={"effort": "high", "format": {"type": "json_schema", "schema": REPORT_SCHEMA}},
    system=[{"type": "text", "text": REPORT_SPEC, "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content":
        [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}} for b64 in frames]
        + [{"type": "text", "text": f"影片標題：{title}\n逐字稿：\n{subs}\n請依規格產出報告 JSON。"}]}],
) as stream:
    report = json.loads(stream.get_final_message().content[-1].text)
```
