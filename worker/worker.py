#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""南瓜數位筆記（Pumpkin Notes）整理主機（worker）
把網站 https://notes.pumpkinvrarai.com/ 收件匣排隊的影片，跑完「下載→抽幀→Claude 寫報告→驗收→上架」全流程。

用法：
  python3 worker.py --once     # 處理完目前排隊的就結束
  python3 worker.py            # 常駐：訂閱 Supabase Realtime，有人送單「立刻」開跑；
                               #       另外每 POLL_FALLBACK 秒補看一次（Realtime 斷線時的保險）

需要 ~/.config/pumpkin-notes/config.json 有：
  "supabase_url": "https://xxxx.supabase.co",
  "supabase_service_key": "sb_secret_...",   # Supabase → Settings → API Keys → Secret keys
  "anthropic_api_key": "sk-ant-...",         # 或用環境變數 ANTHROPIC_API_KEY
  "telegram_bot_token": "...",  "telegram_chat_id": "..."   # 選填：壞了會發 Telegram 告訴南瓜（只 sendMessage，不 poll）
  "worker_name": "PC-01"                                    # 選填：顯示在網站「claimed_by」與通知
第一次請跑 worker_setup.command 貼金鑰。
"""
import base64, io, json, os, re, subprocess, sys, time, socket, urllib.request, urllib.parse, urllib.error
import ssl
try:                                   # Mac 的 python.org 版沒帶根憑證：用 certifi 的
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL = ssl.create_default_context()
_opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL))
urllib.request.install_opener(_opener)
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))   # 讓 worker 找得到 drive_store

CONF = Path(os.path.expanduser(os.environ.get("PN_CONFIG") or "~/.config/pumpkin-notes/config.json"))
RAW = json.loads(CONF.read_text(encoding="utf-8")) if CONF.exists() else {}
SKILL = Path(os.path.expanduser(os.environ.get("PN_SKILL_DIR") or RAW.get("skill_dir") or "~/.claude/skills/pumpkin-digital-notes/scripts"))
if not (SKILL / "prep_youtube.py").exists(): sys.exit(f"找不到 skill 腳本：{SKILL}（config.json 加 skill_dir 或設環境變數 PN_SKILL_DIR）")
sys.path.insert(0, str(SKILL))
from pn_config import cfg            # noqa: E402
from report_lib import Report        # noqa: E402
from PIL import Image                # noqa: E402

SB_URL = RAW.get("supabase_url") or "https://xoyalmkdaiehsldbokud.supabase.co"
SB_KEY = RAW.get("supabase_service_key") or os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_KEY = RAW.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = RAW.get("model") or "claude-opus-5"
WORKER = RAW.get("worker_name") or socket.gethostname()
STEP = 10
APP = "南瓜數位筆記"
TG_TOKEN = RAW.get("telegram_bot_token") or os.environ.get("PN_TG_TOKEN", "")
TG_CHAT = RAW.get("telegram_chat_id") or os.environ.get("PN_TG_CHAT", "")
POLL_FALLBACK = int(RAW.get("poll_fallback_sec") or 120)   # Realtime 正常時只是保險；Realtime 掛了自動改 30 秒
SITE = "https://notes.pumpkinvrarai.com/"

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

def notify(text, silent=False):
    """壞了就告訴南瓜：Telegram Bot API sendMessage（只發不收，可與其他機器人共用 token）。沒設定就只寫 log。"""
    line = f"🎃 {APP}整理主機（{WORKER}）\n{text}"
    if not (TG_TOKEN and TG_CHAT):
        log("（未設 Telegram，僅記錄）", text.replace("\n", " ")); return
    try:
        body = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": line, "disable_notification": "true" if silent else "false"}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=body, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r: r.read()
    except Exception as e:
        log("⚠️ Telegram 通知失敗：", e)

# ─────────────────────────── Supabase REST ───────────────────────────
def sb(method, path, body=None, headers=None, raw=False):
    h = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY}
    if body is not None and not raw:
        body = json.dumps(body, ensure_ascii=False).encode("utf-8"); h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(SB_URL + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            t = r.read()
            return json.loads(t) if t and r.headers.get("Content-Type", "").startswith("application/json") else t
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Supabase {method} {path} → {e.code}: {e.read().decode('utf-8','ignore')[:300]}")

def queued_jobs():
    return sb("GET", "/rest/v1/jobs?status=eq.queued&order=created_at.asc&limit=5")

def patch_job(jid, **fields):
    sb("PATCH", f"/rest/v1/jobs?id=eq.{jid}", fields, {"Prefer": "return=minimal"})

def profile_email(uid):
    rows = sb("GET", f"/rest/v1/profiles?id=eq.{uid}&select=email,display_name")
    return rows[0] if rows else {}

def upload(bucket, path, data, ctype):
    sb("POST", f"/storage/v1/object/{bucket}/{urllib.parse.quote(path)}", data,
       {"Content-Type": ctype, "x-upsert": "true"}, raw=True)

def download(bucket, path):
    return sb("GET", f"/storage/v1/object/{bucket}/{urllib.parse.quote(path)}", raw=True)

# ─────────────────────────── 備料 ───────────────────────────
def prep(job):
    src = job["source_url"] or ""
    if job.get("upload_path"):                       # 夥伴上傳的錄影檔：先抓下來
        local = cfg.work_dir / "uploads" / Path(job["upload_path"]).name
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(download("uploads", job["upload_path"]))
        src = str(local)
    if not src:
        raise RuntimeError("這張單沒有影片網址也沒有上傳檔")
    r = subprocess.run([sys.executable, str(SKILL / "prep_youtube.py"), src, str(STEP), "--scene"],
                       capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        raise RuntimeError("備料失敗：" + (r.stderr or r.stdout)[-400:])
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", src)
    key = re.sub(r"[^\w-]", "_", m.group(1) if src.startswith("http") and m else Path(src).stem)[:40]
    work = cfg.work_dir / key
    meta = json.loads((work / "job.json").read_text(encoding="utf-8"))
    meta["_work"] = str(work); meta["_src"] = src
    return meta

# ─────────────────────────── Claude 寫報告 ───────────────────────────
SPEC = """你是「Pumpkin Notes」的筆記編輯。把一支影片整理成國小生也讀得懂的白話圖文筆記，給台灣的團隊看（繁體中文、台灣用語）。
規則：
- 短句、多比喻、少術語；英文專有名詞第一次出現要進小辭典（glossary），內文用 [[id]] 標記那個詞，例如「這就是 [[agent]] 在做的事」。
- 章節 4～7 段，每段 1～2 張截圖；截圖用影片的秒數指定（figures.sec），挑「畫面本身就是重點」的時刻（投影片、示範、結論）；整篇 10～16 張，不要重複的畫面。
- 逐字稿只是參考，畫面總表（contact sheet，每格左上有秒數）才是挑圖依據；秒數必須是總表上看得到的。
- takeaways 三句：最重要的觀念／最能照著做的步驟／最容易踩的坑。verdict.pill 只能是「看報告就夠」「值得看原片」「挑段看」三選一。
- tags：topic 從這些選 1～3 個：AI代理人、Harness工程、VibeCoding、脈絡工程、團隊導入、自動化、資料分析、AI寫作、MCP、成本控管、產品上線、資安邊界（都不合再自創 2～6 字、不能有空格）；use 從 實作教學、觀念建立、案例分享、工具評測 選 1 個。
- level：入門（不需背景）／進階（要先懂基本名詞）／深入（給已在做的人）。
- 內文段落用 HTML：<p>、<ul><li>、<div class="note">💡 小提醒</div>、<table>；不要 <h2>（標題由 heading 給）。
輸出格式（只輸出這個 JSON，鍵名一字不差）：
{"h1":"一句人話標題","one_liner":"全場最重要的一句話","level":"入門|進階|深入","tags":{"topic":["…"],"use":"…"},"keywords":["…"],"glossary":[{"id":"agent","term":"AI Agent（AI 代理人）","plain":"白話解釋"}],"sections":[{"id":"s1","heading":"段落標題","range":"0:00–3:47","html":"<p>…</p>","figures":[{"sec":30,"caption":"這張在講什麼"}]}],"takeaways":["句1","句2","句3"],"verdict":{"pill":"看報告就夠|值得看原片|挑段看","why":"…"},"action":"看完可以做的一件事","for_team":["對團隊的用處"]}
"""

SCHEMA = {
  "type": "object", "additionalProperties": False,
  "required": ["h1", "one_liner", "level", "tags", "keywords", "glossary", "sections", "takeaways", "verdict", "action", "for_team"],
  "properties": {
    "h1": {"type": "string", "description": "一句人話當標題，不是影片原標題，20 字內"},
    "one_liner": {"type": "string", "description": "全場最重要的一句話，可含 <b> 與 <mark>"},
    "level": {"type": "string", "enum": ["入門", "進階", "深入"]},
    "tags": {"type": "object", "additionalProperties": False, "required": ["topic", "use"],
             "properties": {"topic": {"type": "array", "items": {"type": "string"}}, "use": {"type": "string"}}},
    "keywords": {"type": "array", "items": {"type": "string"}},
    "glossary": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["id", "term", "plain"],
                 "properties": {"id": {"type": "string"}, "term": {"type": "string"}, "plain": {"type": "string"}}}},
    "sections": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                 "required": ["id", "heading", "range", "html", "figures"],
                 "properties": {"id": {"type": "string"}, "heading": {"type": "string"},
                                "range": {"type": "string", "description": "影片時間範圍，如 0:00–3:47"},
                                "html": {"type": "string"},
                                "figures": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                            "required": ["sec", "caption"], "properties": {"sec": {"type": "integer"}, "caption": {"type": "string"}}}}}}},
    "takeaways": {"type": "array", "items": {"type": "string"}, "description": "恰好三句"},
    "verdict": {"type": "object", "additionalProperties": False, "required": ["pill", "why"],
                "properties": {"pill": {"type": "string"}, "why": {"type": "string"}}},
    "action": {"type": "string", "description": "看完可以做的一件事"},
    "for_team": {"type": "array", "items": {"type": "string"}, "description": "對團隊的用處 2～4 條"}
  }
}

def img_block(p, maxw=1600):
    im = Image.open(p).convert("RGB")
    if im.width > maxw: im = im.resize((maxw, round(im.height * maxw / im.width)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=78)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}

def write_with_claude(meta):
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else anthropic.Anthropic()
    work = Path(meta["_work"])
    sheets = sorted(work.glob("contact_*.jpg"))[:6]
    subs = (work / "subs.txt").read_text(encoding="utf-8", errors="ignore")[:70000] if (work / "subs.txt").exists() else "(無字幕)"
    content = [img_block(p) for p in sheets]
    content.append({"type": "text", "text": (
        f"影片標題：{meta.get('title','')}\n頻道／講者：{meta.get('uploader','')}\n總長：{meta.get('duration','')}（{meta.get('duration_sec',0)} 秒）\n"
        f"畫面總表：上面 {len(sheets)} 張，每格左上角的數字是秒數，每 {meta.get('step',STEP)} 秒一格。\n\n逐字稿（[分:秒] 文字）：\n{subs}\n\n請依規格輸出報告 JSON。")})
    kwargs = dict(model=MODEL, max_tokens=30000,
                  system=[{"type": "text", "text": SPEC, "cache_control": {"type": "ephemeral"}}],
                  messages=[{"role": "user", "content": content}],
                  extra_body={"output_config": {"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}}})
    try:
        with client.messages.stream(**kwargs) as s:
            msg = s.get_final_message()
    except anthropic.BadRequestError as e:          # 舊 SDK／API 不吃 format 就退回純文字 JSON
        log("結構化輸出不支援，改用純文字 JSON：", str(e)[:120])
        kwargs["extra_body"] = {"output_config": {"effort": "high"}}
        with client.messages.stream(**kwargs) as s:
            msg = s.get_final_message()
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    (work / "claude_raw.txt").write_text(text, encoding="utf-8")          # 留底，出錯好查
    log(f"Claude 回覆 {len(text)} 字，stop_reason={msg.stop_reason}")
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0) if m else text)
    for a, b in (("title", "h1"), ("one_liner", "one_liner"), ("summary", "one_liner"), ("oneLiner", "one_liner"), ("glossary_list", "glossary")):
        if a in data and b not in data: data[b] = data[a]                  # 常見的別名
    if "h1" not in data:                                                   # 有時會多包一層
        for k, v in data.items():
            if isinstance(v, dict) and "h1" in v: data = v; break
    if "h1" not in data:
        raise RuntimeError("Claude 回的 JSON 缺 h1 等欄位，原文存在 " + str(work / "claude_raw.txt"))
    u = msg.usage
    log(f"Claude 用量：in {u.input_tokens} / out {u.output_tokens} / cache read {getattr(u,'cache_read_input_tokens',0)}")
    return data

# ─────────────────────────── 組 HTML ───────────────────────────
def slugify(s):
    s = re.sub(r"[^\w一-鿿-]+", "_", s).strip("_")
    return s[:40] or "note"

def render(meta, data, shelf, level_override=""):
    work = Path(meta["_work"]); out = work / "out"; out.mkdir(exist_ok=True)
    today = date.today().isoformat()
    slug = f"{today}_{slugify(data['h1'])}"
    gl = {g["id"]: (g["term"], g["plain"]) for g in data.get("glossary", [])}
    src = meta.get("url") or meta["_src"]
    is_yt = src.startswith("http")
    r = Report(slug=slug, shelf=shelf, source_url=src if is_yt else "", cover=meta.get("cover", ""),
               glossary=gl, img_dir=work / "frames", img_mode="f", frame_step=meta.get("step", STEP),
               read_date=today, duration_sec=meta.get("duration_sec"), keywords=data.get("keywords", []),
               level=level_override or data.get("level", ""), out_dir=out, hub_url="../index.html",
               source_kind="youtube" if is_yt else "local")
    T, fig, grid = r.T, r.fig, r.grid
    def tl(html_text):
        return re.sub(r"\[\[([\w-]+)\]\]", lambda m: T(m.group(1)) if m.group(1) in gl else m.group(1), html_text)
    max_sec = int(meta.get("duration_sec") or 0)
    def safe_fig(f):
        sec = max(0, min(int(f["sec"]), max(0, max_sec - 1)))
        try: return fig(sec, f["caption"])
        except FileNotFoundError: return ""
    secs = data["sections"]
    outline = "".join(f"<tr><td><b>{i+1}</b></td><td>{tl(s['heading'])}</td><td>{s.get('range','')}</td></tr>" for i, s in enumerate(secs))
    body = ('<section id="outline"><h2>📋 大綱總結（1 分鐘看完全場）</h2><div class="tbl-wrap"><table>'
            '<tr><th style="width:60px">段</th><th>講了什麼</th><th style="width:110px">影片時間</th></tr>' + outline + '</table></div></section>')
    toc = [("outline", "📋 大綱總結")]
    for i, s in enumerate(secs):
        figs = [safe_fig(f) for f in s.get("figures", [])[:2]]
        figs = [f for f in figs if f]
        fh = grid(*figs) if len(figs) == 2 else "".join(figs)
        sid = re.sub(r"[^\w-]", "", s["id"]) or f"s{i+1}"
        body += f'<section id="{sid}"><h2>{i+1}️⃣ {tl(s["heading"])}</h2>{tl(s["html"])}{fh}</section>'
        toc.append((sid, s["heading"][:14]))
    if data.get("for_team"):
        body += '<section id="pumpkin"><h2>🎃 對團隊的用處</h2><ul>' + "".join(f"<li>{tl(x)}</li>" for x in data["for_team"]) + "</ul></section>"
        toc.append(("pumpkin", "🎃 對團隊的用處"))
    facts = [f"🎤 <b>講者</b>：{meta.get('uploader','')}", f"🎬 <b>原標題</b>：{meta.get('title','')}",
             f"📺 <b>來源</b>：{'YouTube' if is_yt else '錄影檔'}"]
    if is_yt: facts.append(f'🔗 <b>出處</b>：<a href="{src}" target="_blank" rel="noopener">youtube.com</a>')
    facts += [f"⏱️ <b>影片總長</b>：{meta.get('duration','')}", f"👀 <b>閱讀日期</b>：{today}"]
    path = r.write(title=f"白話圖文報告．{data['h1']}", h1=data["h1"], facts=facts, one=tl(data["one_liner"]),
                   toc=toc, body=body, takeaways=data["takeaways"],
                   verdict=(data["verdict"]["pill"], data["verdict"]["why"]), action=data["action"],
                   footer_how=f"整理主機自動產出：yt-dlp 抓影片與字幕 → 每 {meta.get('step',STEP)} 秒抽一張畫面 → {MODEL} 挑重點寫白話 → 驗收 → 上架。")
    return slug, Path(path), r

def check(html_path):
    r = subprocess.run([sys.executable, str(SKILL / "check_report.py"), str(html_path)], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-600:]

def cover_bytes(meta, work):
    try:
        from report_lib import load_image
        im = load_image(meta.get("cover", "")).convert("RGB")
    except Exception:
        first = sorted((work / "frames").glob("f_*.jpg"))
        if not first: return None
        im = Image.open(first[min(3, len(first) - 1)]).convert("RGB")
    im = im.resize((640, round(im.height * 640 / im.width)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=82); return b.getvalue()


SITE = RAW.get("site_url") or "https://notes.pumpkinvrarai.com/"
def reskin_v03(html, slug_db, data, meta, shelf):
    """套上 V03 墨金樣式（工具列、點格、回書架），連結一律指向正式網址；失敗就退回原樣。"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import build_v03 as B
        rp = {"file": f"cloud/{slug_db}.html", "title": data["h1"], "speaker": meta.get("uploader", ""),
              "source": "YouTube" if (meta.get("url") or "").startswith("http") else "錄影",
              "duration": meta.get("duration", ""), "date": date.today().isoformat(),
              "summary": re.sub(r"<[^>]+>", "", data["one_liner"])[:140], "cover": "",
              "tags": [f"主題/{t}" for t in data["tags"].get("topic", [])[:3]] + [f"用途/{data['tags'].get('use','')}"],
              "shelf": shelf, "section": ""}
        m = B.scan_report(html)
        out = B.reskin_report(html, rp, [rp], m, {shelf: shelf}, {}, depth_prefix=SITE)
        if not out: raise RuntimeError("reskin 回空")
        out = re.sub(r'name="pn:slug" content="[^"]*"', f'name="pn:slug" content="{slug_db}"', out)
        out = re.sub(r"var slug\s*=\s*['\"][^'\"]*['\"]", f"var slug='{slug_db}'", out)
        return out
    except Exception as e:
        log("⚠️ 套 V03 樣式失敗，先用原樣上架：", e)
        return html.replace('href="../index.html', 'href="' + SITE + 'index.html')


# ─────────────────────────── 圖片存放（不留在本機） ───────────────────────────
IMG_MAX_W = 1280      # 截圖統一最寬 1280px：1080p 影片縮一點點，文字仍清楚，一張約 80～120 KB
IMG_QUALITY = 80
def shrink_jpeg(raw: bytes) -> bytes:
    """任何格式 → 最寬 1280 的 JPEG（品質 80）。"""
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(raw)); im = im.convert("RGB")
    if im.width > IMG_MAX_W:
        im = im.resize((IMG_MAX_W, round(im.height * IMG_MAX_W / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=IMG_QUALITY, optimize=True, progressive=True); return buf.getvalue()

def externalize_images(html: str, uid: str, slug_db: str):
    """把報告裡 base64 內嵌的截圖抽出來：縮圖 → 上傳公開桶 img/<uid>/<slug>/NN.jpg → 網頁改用網址。
    回傳 (新 html, [(檔名, bytes), …])，後者拿去 Google 雲端歸檔。"""
    import base64 as _b
    images = []
    def rep(m):
        data = shrink_jpeg(_b.b64decode(m.group(2)))
        name = f"{len(images)+1:02d}.jpg"; images.append((name, data))
        path = f"{uid}/{slug_db}/{name}"
        upload("img", path, data, "image/jpeg")
        return f'src="{SB_URL}/storage/v1/object/public/img/{path}" loading="lazy" decoding="async"'
    out = re.sub(r'src="data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)"', rep, html)
    return out.replace(' loading="lazy" loading="lazy"', ' loading="lazy"'), images

def cloud_archive(slug_db, title, html: str, cover: bytes, images, work_dir):
    """Google 雲端歸檔（有授權才做）＋ 清掉本機工作夾（不留圖在 Mac）。"""
    try:
        import drive_store
        if drive_store.enabled():
            drive_store.archive_note(date.today().isoformat(), title, html.encode("utf-8"), cover, images, log=log)
        else:
            log("ℹ️ Google 雲端還沒授權（python3 worker/drive_store.py auth），這次先只存 Supabase")
    except Exception as e:
        log("⚠️ Google 雲端歸檔失敗（不影響上架）：", e)
    try:
        import shutil; shutil.rmtree(work_dir, ignore_errors=True); log("🧹 本機工作夾已清掉")
    except Exception as e:
        log("清工作夾失敗：", e)

# ─────────────────────────── 主流程 ───────────────────────────
def process(job):
    jid, uid = job["id"], job["owner_id"]
    log(f"▶ 接單 {jid[:8]}  {job.get('source_url') or job.get('upload_path')}")
    patch_job(jid, status="prepping", claimed_by=WORKER, progress_msg="正在下載影片與字幕，並抽出畫面")
    meta = prep(job)
    patch_job(jid, status="writing", progress_msg=f"正在挑 12～16 張關鍵畫面、用 {MODEL} 寫白話筆記（約 3～6 分鐘）")
    data = write_with_claude(meta)
    shelf = job.get("shelf") or ("youtube" if (meta.get("url") or "").startswith("http") else "meeting")
    slug, html_path, rep = render(meta, data, shelf, job.get("level") or "")
    patch_job(jid, status="checking", progress_msg="正在檢查截圖、時間戳與小辭典")
    ok, report = check(html_path)
    log(("✅ 驗收通過" if ok else "⚠️ 驗收有黃燈，照樣上架：") + ("" if ok else report[-300:]))
    patch_job(jid, status="publishing", progress_msg="正在上架")
    slug_db = f"{date.today().isoformat()}_{jid[:8]}"          # Storage 的路徑只能 ASCII，中文標題放 notes.title
    html = reskin_v03(html_path.read_text(encoding="utf-8"), slug_db, data, meta, shelf)
    html, images = externalize_images(html, uid, slug_db)           # 截圖抽出去：網頁瘦身、圖存雲端
    html_p = f"{uid}/{slug_db}.html"; upload("notes", html_p, html.encode("utf-8"), "text/html; charset=utf-8")
    cover_p = ""
    cb = cover_bytes(meta, Path(meta["_work"]))
    if cb: cb = shrink_jpeg(cb); cover_p = f"{uid}/{slug_db}.jpg"; upload("covers", cover_p, cb, "image/jpeg")
    rm = re.search(r'name="pn:read-min" content="(\d+)"', html)
    tags = [f"主題/{t}" for t in data["tags"].get("topic", [])[:3]] + [f"用途/{data['tags'].get('use','')}"]
    row = {"slug": slug_db, "owner_id": uid, "title": data["h1"], "speaker": meta.get("uploader", ""),
           "source_kind": "youtube" if (meta.get("url") or "").startswith("http") else "local",
           "source_url": meta.get("url", ""), "duration_sec": meta.get("duration_sec", 0),
           "read_min": int(rm.group(1)) if rm else None, "level": rep.level or None,
           "one_liner": re.sub(r"<[^>]+>", "", data["one_liner"]), "summary": re.sub(r"<[^>]+>", "", data["one_liner"])[:140],
           "takeaways": data["takeaways"], "verdict": data["verdict"], "action": data["action"],
           "shelf": shelf, "tags": tags, "keywords": data.get("keywords", [])[:12],
           "cover_path": cover_p, "html_path": html_p,
           "visibility": "team" if job.get("auto_share") else "private",
           "shared_at": (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) if job.get("auto_share") else None)}
    ins = sb("POST", "/rest/v1/notes", row, {"Prefer": "return=representation"})
    note_id = ins[0]["id"]
    patch_job(jid, status="done", note_id=note_id, progress_msg="已上架，看筆記 →")
    log(f"✅ 上架完成 {slug_db}")
    cloud_archive(slug_db, data["h1"], html, cb, images, Path(meta["_work"]))

def recover_stale():
    """整理主機上次中途掛掉，留在 prepping/writing/... 的單：重排一次；已重排過還掛 → 標失敗並通知。"""
    st = "status=in.(prepping,writing,checking,publishing)"
    for j in sb("GET", f"/rest/v1/jobs?{st}&claimed_by=eq.{urllib.parse.quote(WORKER)}&select=id,source_url,upload_path,progress_msg"):
        src = j.get("source_url") or j.get("upload_path") or ""
        if (j.get("progress_msg") or "").startswith("整理主機重啟"):
            patch_job(j["id"], status="failed", progress_msg="失敗：整理主機兩次中途停止，請再送一次或找南瓜")
            notify(f"❌ 一張單重試後仍卡住，已標失敗\n{src}\n單號 {j['id'][:8]}")
        else:
            patch_job(j["id"], status="queued", claimed_by=None, progress_msg="整理主機重啟，重新排隊")
            log("♻️ 重排中途單", j["id"][:8])

def drain():
    """把目前排隊的單全部做完。回傳做了幾張。"""
    n = 0
    while True:
        try:
            jobs = queued_jobs()
        except Exception as e:
            log("讀排隊單失敗：", e); return n
        if not jobs: return n
        for job in jobs:
            n += 1
            try:
                process(job)
            except Exception as e:
                log("❌ 失敗：", e)
                src = job.get("source_url") or job.get("upload_path") or ""
                try: patch_job(job["id"], status="failed", progress_msg=("失敗：" + str(e))[:300])
                except Exception as e2: log("回寫失敗：", e2)
                notify(f"❌ 一張單做失敗\n{src}\n原因：{str(e)[:200]}\n單號 {job['id'][:8]}（夥伴可在收件匣重送）")

def realtime_thread(wake, state):
    """背景執行緒：訂閱 jobs 表變動，有動靜就叫醒主迴圈。斷線自動重連；連不上就把 state['ok'] 設 False（主迴圈改密集輪詢）。"""
    import asyncio, threading
    try:
        import certifi; os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        from realtime import AsyncRealtimeClient
    except ImportError:
        log("⚠️ 沒裝 realtime 套件（pip install realtime certifi），改用每 30 秒輪詢"); state["ok"] = False; return
    async def run():
        fails = 0
        while True:
            client = AsyncRealtimeClient(SB_URL.replace("https://", "wss://") + "/realtime/v1", SB_KEY, auto_reconnect=True, max_retries=10)
            try:
                await client.connect()
                ch = client.channel("pn-worker-" + WORKER)
                ch.on_postgres_changes("*", schema="public", table="jobs", callback=lambda p: wake.set())
                st = {}
                await ch.subscribe(lambda status, err=None: st.update(s=str(status), e=err))
                for _ in range(50):
                    if st.get("s", "").endswith("SUBSCRIBED"): break
                    await asyncio.sleep(0.2)
                if not st.get("s", "").endswith("SUBSCRIBED"): raise RuntimeError(f"訂閱失敗：{st}")
                if not state["ok"] and fails: notify("✅ Realtime 已重新連上，恢復即時接單", silent=True)
                state["ok"] = True; fails = 0; log("📡 Realtime 已訂閱 jobs 表（有人送單立刻開跑）")
                while client.is_connected: await asyncio.sleep(5)
                raise RuntimeError("連線中斷")
            except Exception as e:
                fails += 1
                if state["ok"] or fails == 3:
                    log("⚠️ Realtime 斷線：", e, "→ 先用 30 秒輪詢，背景持續重連")
                    if fails == 3: notify(f"⚠️ Realtime 連不上（{e}），已改每 30 秒輪詢，不會漏單但會慢一點", silent=True)
                state["ok"] = False
                try: await client.close()
                except Exception: pass
                await asyncio.sleep(min(60, 5 * fails))
    threading.Thread(target=lambda: asyncio.run(run()), daemon=True, name="realtime").start()

def main():
    import threading
    once = "--once" in sys.argv
    if not SB_KEY: sys.exit("缺 supabase_service_key：先跑 worker_setup.command")
    if not ANTHROPIC_KEY and not os.environ.get("ANTHROPIC_API_KEY"): log("⚠️ 沒設 anthropic_api_key，會用 SDK 的預設登入（ant auth）")
    log(f"{APP}整理主機上線：{WORKER}，模型 {MODEL}，{'只跑一輪' if once else 'Realtime 即時接單'}")
    if once:
        drain(); return
    try:
        recover_stale()
    except Exception as e:
        log("查中途單失敗：", e)
    wake = threading.Event(); state = {"ok": False}
    realtime_thread(wake, state)
    notify(f"🟢 上線，等單中。網站 {SITE}", silent=True)
    try:
        while True:
            wake.clear()
            n = drain()
            if n: log(f"這輪做了 {n} 張，回到等單")
            wake.wait(timeout=POLL_FALLBACK if state["ok"] else 30)
    except KeyboardInterrupt:
        log("手動停止"); notify("⏹ 手動停止", silent=True)
    except Exception as e:
        log("💥 整理主機當掉：", e); notify(f"💥 整理主機當掉：{str(e)[:300]}\n（啟動腳本會自動重開；連續失敗請看 PC-01 的 worker.log）")
        raise

if __name__ == "__main__":
    main()
