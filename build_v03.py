#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小南瓜數位筆記 V03（墨金美學 × 第二大腦工具）產生器。

做三件事（可以重複跑，跑幾次結果都一樣）：
  1. 把 V01 分享庫（~/pumpkin-digital-notes）的封面照抄過來。
  2. 把每篇報告「換皮」成墨金版，並且補回 V01 沒有的東西：
       • <meta name="pn:*">（slug／keywords／level／read-min／source）
       • 缺「🎯 三句話帶走」的篇章補一個 id="takeaway" 區塊（內容從本篇的
         「對南瓜的用處／結語」自動摘錄，區塊裡會誠實標示是自動摘的）
       • 頂部工具列（回書架、收藏、分享給團隊、匯出 PDF、複製 Markdown…）
       • 日／夜主題切換（跟首頁共用 localStorage.pnTheme）
  3. 產出前端資料層：
       • data/reports.js  →  window.PN_DATA = {...}（file:// 也讀得到）
       • data/store.js    →  PN.store（Phase 1 用 localStorage 實作；
                              Phase 2 換 Supabase 時只換這一支，介面不變）

V01 完全不動，只讀不寫。V01 有新報告時重跑一次就同步：

    python3 build_v03.py
    python3 build_v03.py --src <V01 路徑>
"""
import argparse, html, json, re, shutil, sys
from datetime import date
from pathlib import Path

E = html.escape
HERE = Path(__file__).resolve().parent
KIT = Path.home() / ".claude/skills/pumpkin-ink-gold/references/ink-gold.css"
LOGO = HERE / "assets/brand/pumpkin-logo-black.svg"

# ───────────────────────── 共用：字體、圖示、Logo ─────────────────────────
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,300;0,400;0,500;0,600;0,700;0,900;1,900'
         '&family=Roboto+Mono:wght@400;500&family=Noto+Sans+TC:wght@300;400;500;700;900&display=swap" rel="stylesheet">')

_S = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
ICONS = {
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.8-3.8"/>',
    "arrow": '<path d="M7 17 17 7M8 7h9v9"/>',
    "right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "left": '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    "play": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
    "tag": '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.2"/>',
    "layers": '<path d="M12 2 2 7l10 5 10-5z"/><path d="m2 12 10 5 10-5"/><path d="m2 17 10 5 10-5"/>',
    "file": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    "filter": '<path d="M4 6h16M7 12h10M10 18h4"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "list": '<rect x="3" y="4" width="6" height="6" rx="1.5"/><rect x="3" y="14" width="6" height="6" rx="1.5"/><path d="M13 6h8M13 9h5M13 16h8M13 19h5"/>',
    "down": '<path d="m6 9 6 6 6-6"/>',
    "up": '<path d="m6 15 6-6 6 6"/>',
    "spark": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16v4M17 18h4"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    "list-tree": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "heart": '<path d="M12 20.3 4.6 13a4.6 4.6 0 0 1 6.5-6.5l.9.9.9-.9A4.6 4.6 0 1 1 19.4 13z"/>',
    "users": '<circle cx="9" cy="8" r="3.4"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16.5 5.2a3.4 3.4 0 0 1 0 6.6M17 20a6 6 0 0 0-2.3-4.7"/>',
    "inbox": '<path d="M3 13h5l1.6 2.6h4.8L16 13h5"/><path d="M5.5 5h13l2.5 8v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4z"/>',
    "print": '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 15h10v6H7z"/>',
    "download": '<path d="M12 3v12M7 11l5 5 5-5"/><path d="M4 20h16"/>',
    "sun": '<circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.4M12 19.6V22M2 12h2.4M19.6 12H22M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M19.1 4.9l-1.7 1.7M6.6 17.4l-1.7 1.7"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>',
    "check": '<path d="m5 13 4.5 4.5L19 7"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "user": '<circle cx="12" cy="8" r="3.6"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
}


def sprite(names):
    sym = "".join(f'<symbol id="i-{n}" {_S}>{ICONS[n]}</symbol>' for n in names)
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
            '<linearGradient id="pn-gold" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FDC302"/>'
            '<stop offset="1" stop-color="#FFD83A"/></linearGradient></defs>' + sym + '</svg>')


def ic(name, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f'<svg{c} aria-hidden="true"><use href="#i-{name}"/></svg>'


def logo_svg(cls="pn-logo"):
    """公司橫向字標。單色 → fill:currentColor，日／夜自動跟著翻。"""
    if not LOGO.exists():
        return '<b>南瓜虛擬科技</b>'
    s = LOGO.read_text(encoding="utf-8")
    s = re.sub(r"<title>.*?</title>", "", s, flags=re.S)
    s = re.sub(r"<svg[^>]*>",
               f'<svg class="{cls}" viewBox="0 0 1300 320" fill="currentColor" role="img" '
               'aria-label="南瓜虛擬科技">', s, count=1)
    return s.strip()


# 彩色 emoji（墨金規則：不當 UI 圖示）。只清「開頭」那顆，內文裡的不動
EMO = (r"(?:[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿〰〽㊗㊙]"
       r"(?:️|‍[\U0001F000-\U0001FAFF☀-➿]|[\U0001F3FB-\U0001F3FF])*️?)")
LEAD_EMO = re.compile(r"^(\s*(?:<[^>]+>\s*)*)(?:" + EMO + r"\s*)+")
KEYCAP = re.compile(r"([0-9])️?⃣")


def strip_lead_emoji(s):
    """去掉開頭的 emoji（可能藏在 <b> 後面），keycap 數字 1️⃣ 轉回 1。"""
    s = KEYCAP.sub(r"\1", s)
    return LEAD_EMO.sub(lambda m: m.group(1), s, count=1)


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def fam_of(tag):
    return tag.split("/", 1)[0] if "/" in tag else "主題"


def leaf(tag):
    return tag.split("/", 1)[1] if "/" in tag else tag


def dur_sec(d):
    try:
        p = [int(x) for x in str(d).split(":")]
        return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
    except Exception:
        return 0


def kit_css():
    if not KIT.exists():
        sys.exit(f"❌ 找不到墨金 CSS 套件：{KIT}")
    return KIT.read_text(encoding="utf-8")


# ───────────────────────── 從報告撈搜尋材料 ─────────────────────────
def scan_report(s):
    s2 = re.sub(r"data:image/[^\"']{50,}", "", s)
    out = {"keywords": [], "level": "", "read_min": "", "source_url": ""}
    for key, name in (("keywords", "pn:keywords"), ("level", "pn:level"),
                      ("read_min", "pn:read-min"), ("source_url", "pn:source")):
        m = re.search(rf'name="{name}" content="([^"]*)"', s2)
        if m:
            out[key] = [k for k in html.unescape(m.group(1)).split("|") if k] if key == "keywords" else m.group(1)
    out["glossary"] = [plain(t) for t in re.findall(r'<tr id="g-[^"]+"><td><b>(.*?)</b>', s2)]
    out["headings"] = [plain(strip_lead_emoji(t)) for t in re.findall(r"<h2[^>]*>(.*?)</h2>", s2, re.S)]
    out["figs"] = len(re.findall(r"<figure>", s2))
    # 出處網址：V01 舊報告沒有 pn:source，就從頁首「出處」那一行撈回來
    if not out["source_url"]:
        m = re.search(r"<b>出處</b>\s*[：:]\s*<a href=\"([^\"]+)\"", s2)
        if m:
            out["source_url"] = html.unescape(m.group(1))
    # 章節字數估讀秒（沒有 read-min 時用）：中文約 450 字／分
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s2, flags=re.S)
    n = len(re.sub(r"\s", "", plain(body)))
    out["est_min"] = max(3, round(n / 450))
    out["chars"] = n
    return out


def guess_level(meta):
    """難度：V01 舊報告沒標，用「小辭典收了幾個詞」粗估一個暫定值。

    規則就這麼簡單，寫死在這裡好讓大家知道它怎麼來的——不是 AI 現場判斷，
    也不是真人評的：辭典 ≤8 詞＝入門、≤16 詞＝進階、再多＝深入。
    之後只要在 reports.json 補 "level": "入門/進階/深入"，就會蓋掉這個暫定值。
    """
    terms = len(meta.get("glossary", []))
    if terms <= 8:
        return "入門"
    if terms <= 16:
        return "進階"
    return "深入"


def related_for(rp, reports, k=3):
    mine, scored = set(rp.get("tags", [])), []
    for o in reports:
        if o.get("file") == rp.get("file"):
            continue
        shared = mine & set(o.get("tags", []))
        score = len(shared) * 3 + (2 if o.get("shelf") == rp.get("shelf") else 0) \
            + (1 if o.get("section") and o.get("section") == rp.get("section") else 0)
        if score:
            scored.append((score, o, shared))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


# ═════════════════════════ 三句話帶走：缺的自動補 ═════════════════════════
def build_takeaway(body, rp):
    """從本篇的「對南瓜的用處／結語」段落，摘出三句話＋一件可以做的事。

    只做「搬運」不做「創作」：句子全部取自本篇既有文字，區塊裡也會標明是自動摘的。
    """
    src_ids = ("pumpkin", "adopt", "ending", "outline")
    chunk = ""
    for sid in src_ids:
        m = re.search(rf'<section id="{sid}">(.*?)</section>', body, re.S)
        if m:
            chunk = m.group(1)
            break

    lines = []
    # 1) 先用 reports.json 的 summary 拆句（那是人寫的一句話大綱）
    for sent in re.split(r"[。！]", rp.get("summary", "")):
        sent = sent.strip()
        if 8 <= len(sent) <= 70:
            lines.append(sent + "。")
    # 2) 不夠三句，就從段落裡撈粗體重點補
    if chunk:
        for b in re.findall(r"<b>(.*?)</b>", chunk, re.S):
            t = plain(strip_lead_emoji(b)).strip("：: ")
            if 6 <= len(t) <= 46 and not any(t in x or x.rstrip("。") in t for x in lines):
                lines.append(t + "。")
            if len(lines) >= 3:
                break
    lines = lines[:3]
    if not lines:
        return ""

    # 3) 一件可以做的事：取「怎麼用在南瓜的工作上」那一欄的第一格
    action = ""
    cells = re.findall(r"<td>(.*?)</td>", chunk, re.S)
    if len(cells) >= 2:
        action = plain(strip_lead_emoji(cells[1]))
    if not action:
        ps = [plain(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", chunk, re.S)]
        ps = [p for p in ps if len(p) >= 20]
        action = ps[0] if ps else ""
    if len(action) > 120:
        action = action[:118].rstrip("，、 ") + "…"

    lis = "".join(f'<li><span class="num">{i + 1}</span><span>{E(t)}</span></li>'
                  for i, t in enumerate(lines))
    out = f'<section id="takeaway"><h2>🎯 三句話帶走</h2><ul class="take">{lis}</ul>'
    if action:
        out += f'<div class="action"><b>看完可以做的一件事</b>：{E(action)}</div>'
    out += ('<p class="small">這一塊是 build_v03 從本篇「對南瓜的用處／結語」自動摘的，'
            '句子都取自原文。之後可以人工改寫成更好的三句。</p>')
    return out + "</section>"


def inject_takeaway(body, toc_html, rp):
    """把補出來的 takeaway 區塊塞進內文＋目錄（插在收尾段落之前）。"""
    if 'id="takeaway"' in body:
        return body, toc_html
    block = build_takeaway(body, rp)
    if not block:
        return body, toc_html
    anchor = None
    for sid in ("pumpkin", "adopt", "ending", "glossary"):
        if f'<section id="{sid}">' in body:
            anchor = sid
            break
    if anchor:
        body = body.replace(f'<section id="{anchor}">', block + f'<section id="{anchor}">', 1)
        toc_html = re.sub(rf'(<a href="#{anchor}">)',
                          r'<a href="#takeaway">🎯 三句話帶走</a>\1', toc_html, count=1)
    else:
        body += block
        toc_html += '<a href="#takeaway">🎯 三句話帶走</a>'
    return body, toc_html


# ═════════════════════════ 報告換皮 ═════════════════════════
TIME_RANGE = re.compile(r"\s*[（(]\s*(\d{1,2}:\d{2}(?::\d{2})?\s*[–—\-~～]\s*\d{1,2}:\d{2}(?::\d{2})?)\s*[）)]")


def split_title(t):
    """大標拆成「粗一行＋細一行」。在第一個不在「」裡的 ：，？ 切開。"""
    depth = 0
    for i, ch in enumerate(t):
        if ch in "「『（(":
            depth += 1
        elif ch in "」』）)":
            depth = max(0, depth - 1)
        elif ch in "：，？" and depth == 0 and 2 <= i < len(t) - 2:
            strong = t[: i + 1] if ch == "？" else t[:i]
            return strong.strip(), t[i + 1:].strip()
    return t, ""


def reskin_report(src_html, rp, reports, meta, shelf_name, sec_name, depth_prefix="../"):
    s = src_html
    # 1) 拆出 V01 的各區塊
    m_cover = re.search(r'<figure class="cover">(.*?)</figure>', s, re.S)
    m_hero = re.search(r'<header class="hero">(.*?)</header>', s, re.S)
    m_toc = re.search(r'<nav class="toc">(.*?)</nav>', s, re.S)
    m_body = re.search(r"</nav>(.*)<footer>(.*?)</footer>", s, re.S)
    if not (m_hero and m_toc and m_body):
        return None
    title_tag = re.search(r"<title>(.*?)</title>", s, re.S)
    page_title = plain(title_tag.group(1)) if title_tag else rp["title"]

    hero = m_hero.group(1)
    h1 = plain(strip_lead_emoji(re.search(r"<h1>(.*?)</h1>", hero, re.S).group(1)))
    strong, light = split_title(h1)

    facts_html = ""
    m_facts = re.search(r'<div class="facts">(.*?)</div>\s*<div class="one">', hero, re.S)
    if m_facts:
        for label, val in re.findall(r"<div>\s*(?:" + EMO + r"\s*)*<b>(.*?)</b>\s*[：:]\s*(.*?)</div>", m_facts.group(1), re.S):
            val = re.sub(r'\sstyle="[^"]*"', "", val)
            facts_html += (f'<div class="pn-fact"><span class="pn-fact__k">{label}</span>'
                           f'<span class="pn-fact__v">{val}</span></div>')
    one = ""
    m_one = re.search(r'<div class="one">(.*?)</div>\s*$', hero, re.S)
    if m_one:
        o = strip_lead_emoji(m_one.group(1).strip())
        o = re.sub(r"^\s*<b>[^<]*</b>\s*[：:]\s*", "", o)
        one = o

    # 2) 內文預處理 → 補三句話帶走 → 章節換皮
    body = m_body.group(1)
    body = re.sub(r"<!--PN:RELATED-->.*?<!--/PN:RELATED-->", "", body, flags=re.S)
    # Obsidian 內部連結 [[slug|顯示字]] 在網頁上只留顯示字（不外露內部筆記檔名）
    body = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", body)
    body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)
    toc_src = m_toc.group(1)
    body, toc_src = inject_takeaway(body, toc_src, rp)

    sec_ids, counter = [], [0]

    def fix_section(m):
        sid, inner = m.group(1), m.group(2)
        counter[0] += 1
        n = counter[0]
        hm = re.search(r"<h2>(.*?)</h2>", inner, re.S)
        eb = f"{n:02d}"
        if hm:
            h = strip_lead_emoji(hm.group(1))
            h = re.sub(r'^\s*<span class="num">\d+</span>\s*', "", h)
            tr = TIME_RANGE.search(h)
            if tr:
                eb += " · ▶ " + re.sub(r"\s", "", tr.group(1))
                h = TIME_RANGE.sub("", h, count=1)
            inner = inner.replace(hm.group(0), f'<p class="pn-eb">{eb}</p><h2>{h.strip()}</h2>', 1)
        sec_ids.append(sid)
        # 區塊開頭的 emoji（callout 的小圖示）拿掉，改由 CSS 畫左側色條
        inner = re.sub(r'(<p class="(?:note|quote|danger|money|big|small)"[^>]*>)(.*?)(</p>)',
                       lambda x: x.group(1) + strip_lead_emoji(x.group(2)) + x.group(3), inner, flags=re.S)
        inner = re.sub(r'(<div class="step">\s*<p>)(.*?)(</p>)',
                       lambda x: x.group(1) + strip_lead_emoji(x.group(2)) + x.group(3), inner, flags=re.S)
        inner = re.sub(r"<h([34])>(.*?)</h\1>",
                       lambda x: f"<h{x.group(1)}>{strip_lead_emoji(x.group(2))}</h{x.group(1)}>", inner, flags=re.S)
        cls = ""
        if sid in ("pumpkin", "adopt"):
            cls = ' class="pn-stage"'
        elif sid == "takeaway":
            cls = ' class="pn-take"'
        return f'<section id="{sid}"{cls}>{inner}</section>'

    body = re.sub(r'<section id="([^"]+)">(.*?)</section>', fix_section, body, flags=re.S)

    # 3) 目錄：跟章節同一套編號
    toc_links = ""
    for i, (href, txt) in enumerate(re.findall(r'<a href="#([^"]+)">(.*?)</a>', toc_src), 1):
        label = plain(strip_lead_emoji(txt))
        label = re.sub(r"^\d+\s*", "", label)
        num = f"{sec_ids.index(href) + 1:02d}" if href in sec_ids else f"{i:02d}"
        toc_links += f'<a href="#{E(href)}" data-toc="{E(href)}"><span class="pn-toc__n">{num}</span><span>{E(label)}</span></a>'

    # 4) 延伸閱讀（重做成封面卡）
    rel_html = ""
    rel = related_for(rp, reports)
    if rel:
        me_dir = Path(rp["file"]).parent
        cards = ""
        for _, o, shared in rel:
            od = Path(o["file"])
            href = od.name if od.parent == me_dir else depth_prefix + o["file"]
            why = "、".join(leaf(t) for t in sorted(shared)) or "同一個書架"
            cv = (f'<div class="pn-rel__cv"><img loading="lazy" src="{depth_prefix}{E(o["cover"])}" alt=""></div>'
                  if o.get("cover") else "")
            cards += (f'<a class="ig-card ig-card--link pn-rel" href="{E(href)}">{cv}<div class="pn-rel__b">'
                      f'<span class="pn-rel__m">{E(o.get("duration",""))} · {E(o.get("speaker","").split("（")[0])}</span>'
                      f'<b>{E(o["title"])}</b><span class="pn-rel__w">共同標籤：{E(why)}</span></div></a>')
        rel_html = (f'<div class="pn-related"><p class="ig-eyebrow">Related · 延伸閱讀</p>'
                    f'<h2 class="pn-related__h">跟這篇有關的其他筆記</h2><div class="pn-rel-grid">{cards}</div></div>')

    # 封面：class 一定要是 "cover"，check_report.py 靠它認（鐵則 1）
    cover = ""
    if m_cover:
        img = re.search(r"<img[^>]*>", m_cover.group(1))
        if img:
            cover = f'<figure class="cover">{img.group(0)}</figure>'

    kicker = shelf_name.get(rp.get("shelf"), "")
    sec = sec_name.get((rp.get("shelf"), rp.get("section")), "")
    kicker_txt = kicker + (f" · {sec}" if sec else "")
    read_min = rp.get("read_min") or meta.get("read_min") or meta.get("est_min")
    level = rp.get("level") or meta.get("level") or guess_level(meta)
    slug = Path(rp["file"]).stem
    kws = list(dict.fromkeys((rp.get("keywords") or []) + meta.get("keywords", [])
                             + [leaf(t) for t in rp.get("tags", [])] + meta.get("glossary", [])[:8]))

    doc = REPORT_TEMPLATE
    for k, v in {
        "%%PAGETITLE%%": E(page_title),
        "%%SLUG%%": E(slug),
        "%%KEYWORDS%%": E("|".join(kws)),
        "%%LEVEL%%": E(level),
        "%%READMIN%%": E(str(read_min)),
        "%%SOURCEURL%%": E(meta.get("source_url", "")),
        "%%FONTS%%": FONTS,
        "%%KIT%%": kit_css(),
        "%%CSS%%": REPORT_CSS,
        "%%SPRITE%%": sprite(["left", "clock", "list-tree", "arrow", "file", "heart", "users",
                              "print", "copy", "download", "sun", "moon", "x", "check"]),
        "%%LOGO%%": logo_svg(),
        "%%UP%%": depth_prefix,
        "%%HOME%%": depth_prefix + "index.html",
        "%%SHELFHREF%%": depth_prefix + "index.html#library?shelf=" + E(rp.get("shelf", "")),
        "%%KICKER%%": E(kicker_txt),
        "%%STRONG%%": E(strong),
        "%%LIGHT%%": f'<span class="ig-display__light">{E(light)}</span>' if light else "",
        "%%META%%": (f'{ic("clock")}<span class="ig-num">{E(rp.get("duration",""))}</span><span class="pn-dot"></span>'
                     f'讀約 <span class="ig-num">{read_min}</span> 分<span class="pn-dot"></span>'
                     f'難度 {E(level)}<span class="pn-dot"></span>'
                     f'閱讀 <span class="ig-num">{E(rp.get("date",""))}</span>'),
        "%%COVER%%": cover,
        "%%FACTS%%": facts_html,
        "%%ONE%%": (f'<div class="pn-one"><p class="ig-eyebrow">One-liner · 一句話大綱</p><p class="pn-one__t">{one}</p></div>'
                    if one else ""),
        "%%TOC%%": toc_links,
        "%%BODY%%": body,
        "%%RELATED%%": rel_html,
        "%%FOOTER%%": m_body.group(2),
    }.items():
        doc = doc.replace(k, v)
    return doc


REPORT_TEMPLATE = r"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="robots" content="noindex,nofollow">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="pn:slug" content="%%SLUG%%">
<meta name="pn:keywords" content="%%KEYWORDS%%">
<meta name="pn:level" content="%%LEVEL%%">
<meta name="pn:read-min" content="%%READMIN%%">
<meta name="pn:source" content="%%SOURCEURL%%">
<title>%%PAGETITLE%%</title>
%%FONTS%%
<style>
%%KIT%%
%%CSS%%
</style></head><body class="ig pn-report">
<script>try{var t=localStorage.getItem('pnTheme');if(!t)t=matchMedia('(prefers-color-scheme: dark)').matches?'night':'day';var m=location.search.match(/[?&]theme=(day|night)/);if(m)t=m[1];document.body.setAttribute('data-theme',t);}catch(e){}</script>
%%SPRITE%%
<canvas id="pn-dots" aria-hidden="true"></canvas>
<div class="pn-progress" aria-hidden="true"><i id="pn-bar"></i></div>

<div class="pn-tools" role="toolbar" aria-label="這篇筆記的工具">
  <a class="pn-tools__back" href="%%HOME%%#library"><svg><use href="#i-left"/></svg><span>回書架</span></a>
  <span class="pn-tools__brand">%%LOGO%%</span>
  <span class="pn-tools__t">%%STRONG%%</span>
  <div class="pn-tools__r">
    <button class="pn-tbtn" data-act="fav" aria-pressed="false" title="加入我的最愛"><svg><use href="#i-heart"/></svg><span class="pn-tbtn__l">收藏</span></button>
    <button class="pn-tbtn" data-act="share" title="分享給團隊" hidden><svg><use href="#i-users"/></svg><span class="pn-tbtn__l">分享給團隊</span></button>
    <button class="pn-tbtn" data-act="pdf" title="匯出 PDF"><svg><use href="#i-print"/></svg><span class="pn-tbtn__l">匯出 PDF</span></button>
    <button class="pn-tbtn" data-act="md" title="複製 Markdown"><svg><use href="#i-copy"/></svg><span class="pn-tbtn__l">複製 Markdown</span></button>
    <button class="pn-tbtn" data-act="obs" title="下載 Obsidian 包"><svg><use href="#i-download"/></svg><span class="pn-tbtn__l">下載 Obsidian 包</span></button>
    <button class="pn-tbtn pn-tbtn--icon" data-act="theme" title="切換深淺色" aria-label="切換深淺色"><svg class="pn-i-sun"><use href="#i-sun"/></svg><svg class="pn-i-moon"><use href="#i-moon"/></svg></button>
  </div>
</div>

<main class="ig-container pn-doc">
  <header class="pn-hero">
    <div class="pn-hero__text">
      <a class="ig-kicker" href="%%SHELFHREF%%">%%KICKER%%</a>
      <h1 class="ig-display pn-title"><span class="ig-display__strong">%%STRONG%%</span>%%LIGHT%%</h1>
      <p class="pn-meta">%%META%%</p>
    </div>
    %%COVER%%
  </header>

  <div class="ig-card pn-facts">%%FACTS%%</div>
  %%ONE%%

  <div class="pn-layout">
    <aside class="pn-toc" aria-label="目錄">
      <p class="ig-eyebrow">Contents · 目錄</p>
      <nav class="pn-toc__list">%%TOC%%</nav>
    </aside>
    <article class="pn-article">
%%BODY%%
      <div class="pn-mine ig-card">
        <p class="ig-eyebrow">My note · 我的一句話（只有你看得到）</p>
        <textarea id="pn-mine" rows="3" placeholder="讀完想記住的一句話…"></textarea>
        <p class="ig-small pn-mine__s" id="pn-mine-s">打完點一下外面就會存起來。</p>
      </div>
%%RELATED%%
      <footer class="pn-foot" data-src="%%SOURCEURL%%">%%FOOTER%%</footer>
    </article>
  </div>
</main>

<div class="pn-modal" id="pn-share" hidden>
  <div class="pn-modal__box ig-card" role="dialog" aria-modal="true" aria-labelledby="pn-share-h">
    <button class="pn-modal__x" data-close aria-label="關閉"><svg><use href="#i-x"/></svg></button>
    <h2 id="pn-share-h">一句話告訴夥伴為什麼值得看</h2>
    <textarea id="pn-share-t" rows="3" placeholder="例：第 12 分鐘那段把 Harness 講得最清楚。"></textarea>
    <div class="pn-modal__f">
      <button class="ig-btn ig-btn--ghost ig-btn--sm" data-close>再想想</button>
      <button class="ig-btn ig-btn--ink ig-btn--sm" id="pn-share-ok">分享給團隊</button>
    </div>
    <p class="ig-small" id="pn-share-note">分享之後，夥伴在「團隊共筆」就看得到這篇和你寫的這句話。</p>
  </div>
</div>
<div class="toast" id="pn-toast" role="status" aria-live="polite"></div>

<script src="%%UP%%data/config.js"></script>
<script src="%%UP%%data/reports.js"></script>
<script src="%%UP%%data/store.js"></script>
<script>
(function(){
  var slug=document.querySelector('meta[name="pn:slug"]').content;
  var S=window.PN&&PN.store;

  /* 閱讀進度條 */
  var bar=document.getElementById('pn-bar');
  function prog(){var h=document.documentElement,max=h.scrollHeight-h.clientHeight;bar.style.width=(max>0?(h.scrollTop/max*100):0)+'%';}
  document.addEventListener('scroll',prog,{passive:true});prog();

  /* 目錄跟著捲動高亮 */
  var links=[].slice.call(document.querySelectorAll('[data-toc]'));
  if('IntersectionObserver' in window){
    var map={};links.forEach(function(a){map[a.dataset.toc]=a;});
    var io=new IntersectionObserver(function(es){es.forEach(function(e){
      if(e.isIntersecting&&map[e.target.id]){links.forEach(function(a){a.classList.remove('is-active');});map[e.target.id].classList.add('is-active');}
    });},{rootMargin:'-30% 0px -60% 0px'});
    [].forEach.call(document.querySelectorAll('.pn-article section[id]'),function(s){io.observe(s);});
  }

  function toast(m){var t=document.getElementById('pn-toast');t.textContent=m;t.classList.add('on');clearTimeout(t._h);t._h=setTimeout(function(){t.classList.remove('on');},2200);}

  /* 收藏 / 分享 狀態（跟首頁共用同一套 PN.store：示範模式存瀏覽器，登入後存 Supabase） */
  var favBtn=document.querySelector('[data-act="fav"]'),shareBtn=document.querySelector('[data-act="share"]');
  function paint(){
    if(!S)return;
    var f=S.isFav(slug);favBtn.setAttribute('aria-pressed',f?'true':'false');
    favBtn.querySelector('.pn-tbtn__l').textContent=f?'已收藏':'收藏';
    var sh=S.getShare(slug);shareBtn.classList.toggle('is-on',!!sh);
    shareBtn.querySelector('.pn-tbtn__l').textContent=sh?'收回私人':'分享給團隊';
    /* 只有擁有者（或 owner 還沒認領、owner_email 是自己）才看得到分享鈕 */
    shareBtn.hidden=!S.canShare(slug);
  }
  if(S){
    S.ready().then(function(){
      paint();
      S.markRead(slug);
      var m0=document.getElementById('pn-mine');
      if(m0)m0.value=S.getTakeaway(slug)||'';
      var s2=document.getElementById('pn-mine-s');
      if(s2&&S.isOffline())s2.textContent=(PN.mode==='demo'?'示範模式：':'還沒登入：')+'先存在這台電腦的瀏覽器裡。';
    });
  }

  favBtn.addEventListener('click',function(){
    Promise.resolve(S.toggleFav(slug)).then(function(on){paint();toast(on?'已加入我的最愛':'已從我的最愛移除');});
  });

  var modal=document.getElementById('pn-share');
  function closeModal(){modal.hidden=true;}
  [].forEach.call(modal.querySelectorAll('[data-close]'),function(b){b.addEventListener('click',closeModal);});
  modal.addEventListener('click',function(e){if(e.target===modal)closeModal();});
  shareBtn.addEventListener('click',function(){
    if(S.getShare(slug)){Promise.resolve(S.unshare(slug)).then(function(){paint();toast('已收回成私人筆記');});return;}
    document.getElementById('pn-share-t').value='';modal.hidden=false;document.getElementById('pn-share-t').focus();
  });
  document.getElementById('pn-share-ok').addEventListener('click',function(){
    Promise.resolve(S.share(slug,document.getElementById('pn-share-t').value.trim())).then(function(){
      closeModal();paint();toast(S.isOffline()?'已分享給團隊（示範資料）':'已分享給團隊');
    });
  });

  /* 我的一句話（只有你看得到） */
  var mine=document.getElementById('pn-mine');
  mine.addEventListener('change',function(){
    Promise.resolve(S.setTakeaway(slug,mine.value.trim())).then(function(){
      document.getElementById('pn-mine-s').textContent=S.isOffline()?'已存到這台電腦的瀏覽器。':'已存起來，只有你看得到。';
    });
  });

  /* 匯出 PDF：用瀏覽器列印，@media print 已經把工具列、目錄藏起來 */
  document.querySelector('[data-act="pdf"]').addEventListener('click',function(){window.print();});

  /* 複製 Markdown：直接把這頁的內文轉成 MD */
  function md(){
    var out=[],m=document.querySelector('meta[name="pn:source"]').content;
    out.push('# '+document.querySelector('.pn-title').innerText.replace(/\n+/g,' ').trim());
    out.push('');
    [].forEach.call(document.querySelectorAll('.pn-facts .pn-fact'),function(f){
      out.push('- **'+f.querySelector('.pn-fact__k').innerText.trim()+'**：'+f.querySelector('.pn-fact__v').innerText.trim());
    });
    if(m)out.push('- **原片**：'+m);
    var one=document.querySelector('.pn-one__t');
    if(one){out.push('');out.push('> '+one.innerText.trim());}
    [].forEach.call(document.querySelectorAll('.pn-article > section'),function(sec){
      out.push('');
      walk(sec,out);
    });
    return out.join('\n').replace(/\n{3,}/g,'\n\n')+'\n';
  }
  function walk(node,out){
    [].forEach.call(node.children,function(el){
      var tag=el.tagName.toLowerCase(),tx=el.innerText.trim();
      if(tag==='h2'){out.push('## '+tx);}
      else if(tag==='h3'){out.push('');out.push('### '+tx);}
      else if(tag==='h4'){out.push('');out.push('#### '+tx);}
      else if(tag==='p'){
        if(el.classList.contains('pn-eb'))return;
        if(tx)out.push(el.classList.contains('quote')?('> '+tx):tx);
      }
      else if(tag==='ul'||tag==='ol'){
        [].forEach.call(el.querySelectorAll('li'),function(li,i){
          out.push((tag==='ol'?(i+1)+'. ':'- ')+li.innerText.trim().replace(/\n+/g,' '));
        });
      }
      else if(tag==='figure'){
        var cap=el.querySelector('figcaption');
        if(cap)out.push('*（圖）'+cap.innerText.trim().replace(/\n+/g,' ')+'*');
      }
      else if(tag==='table'){
        var rows=[].slice.call(el.querySelectorAll('tr'));
        rows.forEach(function(tr,i){
          var cells=[].slice.call(tr.children).map(function(td){return td.innerText.trim().replace(/\n+/g,' ').replace(/\|/g,'\\|');});
          out.push('| '+cells.join(' | ')+' |');
          if(i===0)out.push('|'+cells.map(function(){return '---';}).join('|')+'|');
        });
      }
      else if(el.children.length){walk(el,out);}
      else if(tx){out.push(tx);}
    });
  }
  document.querySelector('[data-act="md"]').addEventListener('click',function(){
    var t=md();
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(function(){toast('Markdown 已複製');},function(){fallback(t);});}
    else fallback(t);
  });
  function fallback(t){var ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');toast('Markdown 已複製');}catch(e){toast('複製失敗，請改用下載');}ta.remove();}

  /* 下載 Obsidian 包：Phase 1 先給單一 .md（含 frontmatter），截圖之後由 worker 打包 */
  document.querySelector('[data-act="obs"]').addEventListener('click',function(){
    var r=(window.PN_DATA&&PN_DATA.bySlug&&PN_DATA.bySlug[slug])||{};
    var fm=['---','title: "'+(r.title||document.title).replace(/"/g,'')+'"','speaker: "'+(r.speaker||'')+'"',
            'date: '+(r.date||''),'source: '+document.querySelector('meta[name="pn:source"]').content,
            'level: '+document.querySelector('meta[name="pn:level"]').content,
            'tags: ['+(r.tags||[]).map(function(t){return '"'+t+'"';}).join(', ')+']','---',''].join('\n');
    var blob=new Blob([fm+md()],{type:'text/markdown;charset=utf-8'});
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=slug+'.md';a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href);},1000);
    toast('已下載 '+slug+'.md（Phase 1 先給單檔，截圖之後補）');
  });

  /* 深淺色切換 */
  document.querySelector('[data-act="theme"]').addEventListener('click',function(){PN.theme.toggle();});

  /* 互動點格背景 */
  PN.dots(document.getElementById('pn-dots'));
})();
</script>
</body></html>"""

# ───────────────────────── 報告頁 CSS ─────────────────────────
REPORT_CSS = r"""
/* ── 小南瓜數位筆記 V03：報告頁 ── */
body.pn-report{background-image:none}            /* 點格改用 canvas 畫（會跟著滑鼠亮） */
#pn-dots{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:-1}
.pn-progress{position:fixed;top:0;left:0;right:0;height:3px;z-index:60;pointer-events:none}
.pn-progress i{display:block;height:100%;width:0;background:var(--ig-gold-gradient);transition:width 80ms linear}

/* 頂部工具列（sticky） */
.pn-tools{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:12px;padding:10px 24px;
  background:color-mix(in srgb,var(--ig-paper) 88%,transparent);backdrop-filter:blur(10px);
  border-bottom:1px solid var(--ig-ink-hairline)}
.pn-tools__back{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;border-radius:999px;
  border:1px solid var(--ig-ink-hairline);background:var(--ig-card);font-size:14px;color:var(--ig-ink);white-space:nowrap;
  transition:border-color var(--ig-fast) var(--ig-ease)}
.pn-tools__back:hover{border-color:var(--ig-ink-faint)}
.pn-tools__back svg{width:15px;height:15px}
.pn-tools__brand{display:flex;align-items:center;color:var(--ig-ink);opacity:.85}
.pn-logo{height:17px;width:auto;display:block}
.pn-tools__t{flex:1;min-width:0;font-size:14px;color:var(--ig-ink-soft);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  padding-left:12px;border-left:1px solid var(--ig-ink-hairline)}
.pn-tools__r{display:flex;align-items:center;gap:6px;flex-wrap:nowrap}
.pn-tbtn{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;border-radius:999px;cursor:pointer;
  border:1px solid var(--ig-ink-hairline);background:var(--ig-card);color:var(--ig-ink-muted);font:400 13px/1 var(--ig-font-sans);
  transition:color var(--ig-fast) var(--ig-ease),border-color var(--ig-fast) var(--ig-ease)}
.pn-tbtn:hover{color:var(--ig-ink);border-color:var(--ig-ink-faint)}
.pn-tbtn svg{width:15px;height:15px}
.pn-tbtn[aria-pressed="true"],.pn-tbtn.is-on{color:var(--ig-ink);border-color:var(--ig-ink);font-weight:600}
.pn-tbtn[aria-pressed="true"] svg{fill:var(--ig-ink)}
.pn-tbtn--icon{padding:0 9px}
.pn-i-moon{display:none}
[data-theme="night"] .pn-i-sun{display:none}
[data-theme="night"] .pn-i-moon{display:block}
@media(max-width:1100px){.pn-tbtn__l{display:none}.pn-tbtn{padding:0 9px}.pn-tools__t{display:none}}
@media(max-width:640px){.pn-tools{padding:8px 12px;gap:8px}.pn-tools__back span{display:none}.pn-tools__brand{display:none}}

.pn-doc{padding-top:44px}
.pn-hero{display:grid;grid-template-columns:1.08fr 1fr;gap:48px;align-items:center;padding-bottom:36px}
@media(max-width:900px){.pn-hero{grid-template-columns:minmax(0,1fr);gap:28px}}
.pn-title{margin:18px 0 20px;font-size:clamp(32px,3.9vw,50px)}
.pn-title span{text-wrap:balance}
.pn-title .ig-display__light{margin-top:4px}
.pn-meta{display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:14px;color:var(--ig-ink-soft)}
.pn-meta svg{width:16px;height:16px}
.pn-meta .ig-num{color:var(--ig-ink)}
.pn-dot{width:3px;height:3px;border-radius:50%;background:var(--ig-ink-faint);margin:0 4px}
.pn-report .cover{margin:0;border-radius:var(--ig-r-lg);overflow:hidden;line-height:0;border:1px solid var(--ig-ink-hairline);background:var(--ig-night);box-shadow:var(--ig-shadow-hover)}
.pn-report .cover img{width:100%;display:block;aspect-ratio:16/9;object-fit:cover}

.pn-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0;padding:6px 8px}
@media(max-width:800px){.pn-facts{grid-template-columns:1fr 1fr}}
@media(max-width:520px){.pn-facts{grid-template-columns:minmax(0,1fr)}}
.pn-fact{padding:14px 18px;display:flex;flex-direction:column;gap:4px;min-width:0}
.pn-fact__k{font-family:var(--ig-font-mono);font-size:12px;letter-spacing:.08em;color:var(--ig-ink-soft)}
.pn-fact__v{font-size:15px;line-height:1.55;color:var(--ig-ink);overflow-wrap:anywhere}
.pn-fact__v a{color:var(--ig-ink);text-decoration:underline;text-decoration-color:var(--ig-ink-faint);text-underline-offset:3px}
.pn-fact__v a:hover{text-decoration-color:var(--ig-gold)}

.pn-one{margin:14px 0 0;background:var(--ig-card);border:1px solid var(--ig-ink-hairline);border-left:3px solid var(--ig-gold);border-radius:4px var(--ig-r-card) var(--ig-r-card) 4px;padding:22px 28px}
.pn-one__t{margin-top:8px;font-size:18px;line-height:1.85;color:var(--ig-ink)}
.pn-one__t b{font-weight:700;background:linear-gradient(transparent 60%,var(--ig-mark-yellow) 60%,var(--ig-mark-yellow) 92%,transparent 92%)}
[data-theme="night"] .pn-one__t b{background:none;color:var(--ig-gold-deep)}

.pn-layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:48px;margin-top:56px;align-items:start}
.pn-toc{position:sticky;top:96px;max-height:calc(100vh - 120px);overflow:auto;padding-right:4px}
.pn-toc__list{display:grid;gap:2px;margin-top:14px}
.pn-toc__list a{display:flex;gap:10px;align-items:baseline;padding:7px 10px;border-radius:10px;font-size:14px;line-height:1.5;color:var(--ig-ink-muted);border-left:2px solid transparent;transition:background-color var(--ig-fast) var(--ig-ease),color var(--ig-fast) var(--ig-ease)}
.pn-toc__list a:hover{background:var(--ig-ink-wash);color:var(--ig-ink)}
.pn-toc__list a.is-active{color:var(--ig-ink);font-weight:600;background:var(--ig-card);border-left-color:var(--ig-ink);border-radius:2px 10px 10px 2px;box-shadow:var(--ig-shadow-xs)}
.pn-toc__n{font-family:var(--ig-font-mono);font-size:12px;color:var(--ig-ink-soft);flex:0 0 auto}
@media(max-width:1000px){
  .pn-layout{grid-template-columns:minmax(0,1fr);gap:20px;margin-top:36px}
  .pn-toc{position:static;max-height:none;overflow:visible;min-width:0}
  .pn-toc__list{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;-webkit-overflow-scrolling:touch}
  .pn-toc__list a{flex:0 0 auto;white-space:nowrap;background:var(--ig-card);border:1px solid var(--ig-ink-hairline);border-radius:999px;padding:6px 14px}
  .pn-toc__list a.is-active{background:var(--ig-ink);border-color:var(--ig-ink);color:var(--ig-paper);border-radius:999px}
  .pn-toc__list a.is-active .pn-toc__n{color:var(--ig-ink-soft)}
}

/* 章節白卡 */
.pn-article{min-width:0;max-width:800px}
.pn-article section{background:var(--ig-card);border:1px solid var(--ig-ink-hairline);border-radius:var(--ig-r-card);padding:36px 40px;margin:0 0 14px;scroll-margin-top:96px;color:var(--ig-ink-muted);font-size:16.5px;line-height:1.85;overflow-wrap:anywhere}
@media(max-width:640px){.pn-article section{padding:24px 20px;font-size:16px}}
.pn-eb{font-family:var(--ig-font-mono);font-size:12px;font-weight:500;letter-spacing:.12em;color:var(--ig-ink-soft)}
.pn-article h2{font-size:clamp(22px,2.4vw,27px);font-weight:700;line-height:1.4;color:var(--ig-ink);margin:8px 0 18px}
.pn-article h3{font-size:19px;font-weight:600;line-height:1.45;color:var(--ig-ink);margin:30px 0 8px}
.pn-article h4{font-size:16px;font-weight:600;color:var(--ig-ink);margin:20px 0 4px}
.pn-article p{margin:12px 0}
.pn-article b,.pn-article strong{color:var(--ig-ink);font-weight:700}
.pn-article a{color:var(--ig-ink);text-decoration:underline;text-decoration-color:var(--ig-ink-faint);text-underline-offset:3px}
.pn-article a:hover{text-decoration-color:var(--ig-gold)}
.pn-article figure{margin:18px 0}
.pn-article figure img{width:100%;display:block;border-radius:var(--ig-r-md);border:1px solid var(--ig-ink-hairline);background:var(--ig-card-alt)}
.pn-article figcaption{margin-top:10px;font-size:14px;line-height:1.65;color:var(--ig-ink-muted)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:640px){.grid2{grid-template-columns:1fr}}
.grid2 figure{margin:14px 0}

/* 時間戳：墨色小膠囊，等寬字 */
.pn-article a.t,.pn-article .t{display:inline-flex;align-items:center;height:22px;padding:0 9px;margin-right:8px;border-radius:999px;background:var(--ig-night);color:#fff;font:500 12px/1 var(--ig-font-mono);text-decoration:none;white-space:nowrap;vertical-align:1px;transition:background-color var(--ig-fast) var(--ig-ease),color var(--ig-fast) var(--ig-ease)}
.pn-article a.t:hover{background:var(--ig-ink);color:var(--ig-gold-soft)}
[data-theme="night"] .pn-article a.t,[data-theme="night"] .pn-article .t{background:var(--ig-card-alt);color:var(--ig-ink);border:1px solid var(--ig-ink-hairline)}

/* 名詞：點線底＋等寬問號 */
.pn-article .term{color:var(--ig-ink);font-weight:600;text-decoration:none;border-bottom:1.5px dotted var(--ig-ink-soft);cursor:help;transition:border-color var(--ig-fast) var(--ig-ease)}
.pn-article .term:hover{border-bottom-color:var(--ig-gold)}
.pn-article .term::after{content:"?";font:500 10px/1 var(--ig-font-mono);vertical-align:super;margin-left:2px;color:var(--ig-ink-soft)}

/* 重點框 */
.pn-article .quote{margin:18px 0;padding:4px 0 4px 20px;border-left:3px solid var(--ig-ink);font-size:17px;line-height:1.85;color:var(--ig-ink)}
.pn-article .note,.pn-article .danger,.pn-article .money{margin:18px 0;padding:14px 20px;border-radius:4px 14px 14px 4px;font-size:15.5px;line-height:1.8}
.pn-article .note{background:var(--ig-card-alt);border:1px solid var(--ig-ink-hairline);border-left:3px solid var(--ig-ink)}
.pn-article .danger{background:var(--ig-card-alt);border:1px solid rgba(220,38,38,.18);border-left:3px solid var(--ig-danger)}
.pn-article .money{background:var(--ig-card-alt);border:1px solid var(--ig-ink-hairline);border-left:3px solid var(--ig-night)}
.pn-article .step{background:var(--ig-card-alt);border:1px solid var(--ig-ink-hairline);border-radius:14px;padding:4px 20px;margin:16px 0}
.pn-article .big{font-size:19px;font-weight:600;line-height:1.7;color:var(--ig-ink)}
.pn-article .big b{background:linear-gradient(transparent 60%,var(--ig-mark-yellow) 60%,var(--ig-mark-yellow) 92%,transparent 92%)}
[data-theme="night"] .pn-article .big b{background:none;color:var(--ig-gold-deep)}
.pn-article .small{font-size:14px;line-height:1.75;color:var(--ig-ink-soft)}
.pn-article .num{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--ig-night);color:#fff;font:500 12px/1 var(--ig-font-mono);flex:0 0 auto}
.pn-article code{font-family:var(--ig-font-mono);font-size:.88em;background:var(--ig-ink-wash);border-radius:6px;padding:1px 6px}
.pn-article pre{font-family:var(--ig-font-mono);font-size:13px;line-height:1.7;background:var(--ig-card-alt);border:1px solid var(--ig-ink-hairline);border-radius:12px;padding:14px 16px;overflow:auto}
.pn-article pre code{background:none;padding:0}

/* 表格：無直線、表頭淡底 */
.tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:16px 0;border:1px solid var(--ig-ink-hairline);border-radius:14px}
.pn-article table{border-collapse:collapse;width:100%;font-size:15px;line-height:1.7;margin:0}
.pn-article th,.pn-article td{padding:12px 16px;text-align:left;vertical-align:top;border:0;border-bottom:1px solid var(--ig-ink-hairline)}
.pn-article tr:last-child td{border-bottom:0}
.pn-article th{background:var(--ig-card-alt);font-size:13px;font-weight:600;color:var(--ig-ink-soft);white-space:nowrap}
.pn-article td:first-child{color:var(--ig-ink)}
.pn-article :target{animation:pn-hl 2.2s var(--ig-ease)}
@keyframes pn-hl{0%,40%{background:var(--ig-gold-wash)}100%{background:transparent}}

/* 🎯 三句話帶走 */
.pn-take{border-left:3px solid var(--ig-ink)!important;border-radius:4px var(--ig-r-card) var(--ig-r-card) 4px!important}
.pn-take ul.take{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:12px}
.pn-take ul.take li{display:flex;gap:12px;align-items:flex-start;font-size:17px;line-height:1.75;color:var(--ig-ink)}
.pn-take .action{margin-top:18px;padding:14px 18px;border-radius:4px 14px 14px 4px;background:var(--ig-card-alt);border:1px solid var(--ig-ink-hairline);border-left:3px solid var(--ig-ink);font-size:15.5px;line-height:1.8}

/* 夜間版把套件裡「墨底白字」的元件翻過來 */
[data-theme="night"] .ig-btn--ink{background:var(--ig-ink);color:var(--ig-paper)}
[data-theme="night"] .ig-btn--ink:hover{background:#fff}
[data-theme="night"] .ig-pill.is-active{color:var(--ig-paper)}

/* 收尾深色舞台：對南瓜的用處 */
.pn-article section.pn-stage{background:var(--ig-night-gradient);border-color:var(--ig-night-deep);border-radius:var(--ig-r-xl);padding:44px 44px 40px;color:var(--ig-on-night-muted);box-shadow:var(--ig-shadow-stage);margin:28px 0}
@media(max-width:640px){.pn-article section.pn-stage{padding:28px 22px}}
.pn-stage .pn-eb{color:var(--ig-on-night-soft)}
.pn-stage h2,.pn-stage h3,.pn-stage h4,.pn-stage b,.pn-stage strong{color:#fff}
.pn-stage a{color:#fff;text-decoration-color:rgba(255,255,255,.3)}
.pn-stage .term{color:#fff;border-bottom-color:rgba(255,255,255,.45)}
.pn-stage .term::after{color:var(--ig-on-night-soft)}
.pn-stage .tbl-wrap{border-color:var(--ig-night-line)}
.pn-stage th{background:var(--ig-night-wash);color:var(--ig-on-night-soft)}
.pn-stage td{border-bottom-color:var(--ig-night-line)}
.pn-stage td:first-child{color:#fff}
.pn-stage .small{color:var(--ig-on-night-soft)}
.pn-stage .note,.pn-stage .money,.pn-stage .step{background:var(--ig-night-wash);border-color:var(--ig-night-line)}
.pn-stage .quote{color:#fff;border-left-color:var(--ig-gold)}

/* 我的一句話 */
.pn-mine{margin:14px 0;padding:22px 24px}
.pn-mine textarea{width:100%;margin-top:10px;padding:12px 14px;border-radius:var(--ig-r-md);border:1px solid var(--ig-ink-hairline);
  background:var(--ig-card-alt);color:var(--ig-ink);font:400 15px/1.75 var(--ig-font-sans);resize:vertical}
.pn-mine textarea:focus{outline:none;box-shadow:var(--ig-focus)}
.pn-mine__s{margin-top:8px;color:var(--ig-ink-soft)}

/* 延伸閱讀 */
.pn-related{margin:40px 0 0}
.pn-related__h{font-size:24px;font-weight:700;margin:8px 0 18px}
.pn-rel-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
@media(max-width:760px){.pn-rel-grid{grid-template-columns:1fr}}
.pn-rel{padding:0;overflow:hidden;display:flex;flex-direction:column}
.pn-rel__cv{aspect-ratio:16/9;background:var(--ig-night);line-height:0}
.pn-rel__cv img{width:100%;height:100%;object-fit:cover}
.pn-rel__b{padding:14px 16px 16px;display:flex;flex-direction:column;gap:4px}
.pn-rel__b b{font-size:15px;line-height:1.5;font-weight:600;color:var(--ig-ink)}
.pn-rel__m{font-family:var(--ig-font-mono);font-size:12px;color:var(--ig-ink-soft)}
.pn-rel__w{font-size:12px;color:var(--ig-ink-soft)}

.pn-foot{margin-top:48px;padding-top:24px;border-top:1px solid var(--ig-ink-hairline);font-size:13px;line-height:1.8;color:var(--ig-ink-soft)}
.pn-foot b{color:var(--ig-ink-muted)}
.pn-foot p{margin:0 0 8px}

/* 分享小框 */
.pn-modal{position:fixed;inset:0;z-index:80;display:grid;place-items:center;padding:24px;background:rgba(22,20,21,.45);backdrop-filter:blur(3px)}
.pn-modal[hidden]{display:none}
.pn-modal__box{position:relative;width:min(520px,100%);padding:28px 30px 24px}
.pn-modal__box h2{font-size:20px;font-weight:700;color:var(--ig-ink)}
.pn-modal__box textarea{width:100%;margin-top:14px;padding:12px 14px;border-radius:var(--ig-r-md);border:1px solid var(--ig-ink-hairline);
  background:var(--ig-card-alt);color:var(--ig-ink);font:400 15px/1.7 var(--ig-font-sans);resize:vertical}
.pn-modal__box textarea:focus{outline:none;box-shadow:var(--ig-focus)}
.pn-modal__f{display:flex;justify-content:flex-end;gap:8px;margin:14px 0 10px}
.pn-modal__x{position:absolute;top:14px;right:14px;width:30px;height:30px;display:grid;place-items:center;border:0;background:none;
  color:var(--ig-ink-soft);cursor:pointer;border-radius:8px}
.pn-modal__x:hover{color:var(--ig-ink);background:var(--ig-ink-wash)}
.pn-modal__x svg{width:16px;height:16px}

.toast{position:fixed;left:50%;bottom:24px;z-index:90;transform:translate(-50%,8px);background:var(--ig-night);color:#fff;padding:10px 18px;border-radius:999px;font-size:14px;opacity:0;transition:opacity var(--ig-base) var(--ig-ease),transform var(--ig-base) var(--ig-ease);pointer-events:none;box-shadow:var(--ig-shadow-float)}
.toast.on{opacity:1;transform:translate(-50%,0)}

/* ── 列印／匯出 PDF ── */
@media print{
  @page{margin:14mm 12mm}
  .pn-tools,.pn-progress,.pn-toc,.pn-related,.pn-mine,.pn-modal,.toast,#pn-dots{display:none!important}
  body.ig{background:#fff!important;color:#161415!important}
  body.ig[data-theme="night"]{--ig-paper:#fff;--ig-card:#fff;--ig-card-alt:#fff;--ig-ink:#161415;
    --ig-ink-muted:rgba(22,20,21,.72);--ig-ink-soft:rgba(22,20,21,.5);--ig-ink-hairline:rgba(22,20,21,.16)}
  .pn-doc{padding-top:0;max-width:none}
  .pn-layout{grid-template-columns:1fr;gap:0;margin-top:20px}
  .pn-article{max-width:none}
  .pn-article section{break-inside:auto;page-break-inside:auto;box-shadow:none;border-color:rgba(22,20,21,.16);padding:16px 0;margin:0 0 6px;border-width:0 0 1px}
  .pn-article section.pn-stage{background:#fff!important;color:#161415!important;border:1px solid rgba(22,20,21,.16);border-radius:12px;padding:18px 20px}
  .pn-stage h2,.pn-stage h3,.pn-stage b,.pn-stage strong,.pn-stage td:first-child{color:#161415!important}
  .pn-stage th{background:#f2f2f2!important;color:#444!important}
  .pn-article figure,.pn-article table,.pn-article tr,.pn-take,.pn-one{break-inside:avoid;page-break-inside:avoid}
  .pn-article h2,.pn-article h3{break-after:avoid;page-break-after:avoid}
  .pn-article figure img{max-height:11cm;object-fit:contain}
  .pn-report .cover{box-shadow:none}
  .pn-article a{text-decoration:none}
  .pn-foot::after{content:"原片：" attr(data-src) "　·　小南瓜數位筆記｜南瓜虛擬科技";display:block;margin-top:10px;font-size:11px;color:#777}
}
"""

# ═════════════════════════ 前端資料層 ═════════════════════════
# ⚠️ Phase 2 起 data/store.js（雙模式資料層：Supabase ／ 離線示範）改成手維護，
#    不再由這支產生，這裡也不要再覆蓋它。同理 data/config.js（後端網址與 anon key）。


def build_data_js(data, reports, metas, out):
    shelves = data.get("shelves", [])
    shelf_name = {s["id"]: s["name"] for s in shelves}
    sec_name = {(s["id"], x["id"]): x["name"] for s in shelves for x in s.get("sections", [])}

    # Phase 1 的示範夥伴。標明 demo，Phase 2 換成 profiles 表。
    profiles = [
        {"slug": "terry", "name": "南瓜", "department": "管理層", "title": "共同創辦人／美術總監", "demo": False},
        {"slug": "blueberry", "name": "小藍莓", "department": "企劃", "title": "產品企劃", "demo": True},
        {"slug": "walnut", "name": "小核桃", "department": "程式", "title": "後端工程師", "demo": True},
    ]

    items = []
    for rp in reports:
        mt = metas[rp["file"]]
        slug = Path(rp["file"]).stem
        tags = rp.get("tags", [])
        level = rp.get("level") or mt.get("level") or guess_level(mt)
        read = rp.get("read_min") or mt.get("read_min") or mt.get("est_min")
        kws = list(dict.fromkeys((rp.get("keywords") or []) + mt.get("keywords", [])))
        hay = " ".join(p for p in [
            rp.get("title", ""), rp.get("speaker", ""), rp.get("summary", ""),
            shelf_name.get(rp.get("shelf", ""), ""), sec_name.get((rp.get("shelf"), rp.get("section")), ""),
            rp.get("source", ""), level, " ".join(leaf(t) for t in tags), " ".join(tags),
            " ".join(kws), " ".join(mt["glossary"]), " ".join(mt["headings"])] if p).lower()
        items.append({
            "slug": slug, "file": rp["file"], "title": rp["title"], "speaker": rp.get("speaker", ""),
            "shelf": rp.get("shelf", ""), "shelfName": shelf_name.get(rp.get("shelf", ""), ""),
            "section": rp.get("section", ""), "sectionName": sec_name.get((rp.get("shelf"), rp.get("section")), ""),
            "source": rp.get("source", ""), "sourceUrl": mt.get("source_url", ""),
            "duration": rp.get("duration", ""), "durationSec": dur_sec(rp.get("duration", "")),
            "date": rp.get("date", ""), "summary": rp.get("summary", ""), "cover": rp.get("cover", ""),
            "tags": tags, "keywords": kws, "glossary": mt["glossary"][:12], "headings": mt["headings"],
            "level": level, "levelAuto": not (rp.get("level") or mt.get("level")),
            "readMin": read, "figs": mt.get("figs", 0),
            "owner": "terry", "visibility": "team", "hay": hay,
        })
    items.sort(key=lambda r: r["date"], reverse=True)

    tag_count = {}
    for r in items:
        for t in r["tags"]:
            tag_count[t] = tag_count.get(t, 0) + 1

    payload = {
        "generated": date.today().isoformat(),
        "site": data.get("site", {}),
        "shelves": [{"id": s["id"], "name": s["name"], "desc": s.get("desc", ""),
                     "sections": s.get("sections", []),
                     "n": sum(1 for r in items if r["shelf"] == s["id"])} for s in shelves],
        "tagFamilies": data.get("tag_families", []),
        "tagCount": tag_count,
        "profiles": profiles,
        "reports": items,
    }
    js = ("/* 這支檔案是 build_v03.py 產的，不要手改。改資料請改 ~/pumpkin-digital-notes/reports.json 再重跑。 */\n"
          "window.PN_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n"
          "PN_DATA.bySlug = {};\n"
          "PN_DATA.reports.forEach(function(r){ PN_DATA.bySlug[r.slug] = r; });\n")
    out.write_text(js, encoding="utf-8")
    return len(items)


# ═════════════════════════ 主程式 ═════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(Path.home() / "pumpkin-digital-notes"), help="V01 分享庫（只讀）")
    a = ap.parse_args()
    src = Path(a.src).expanduser().resolve()
    if src == HERE:
        sys.exit("❌ 來源不能是 V03 自己")
    data = json.loads((src / "reports.json").read_text(encoding="utf-8"))
    reports = data["reports"]
    shelves = data.get("shelves", [])
    shelf_name = {s["id"]: s["name"] for s in shelves}
    sec_name = {(s["id"], x["id"]): x["name"] for s in shelves for x in s.get("sections", [])}

    # 封面照抄
    for rp in reports:
        cv = rp.get("cover")
        if cv and (src / cv).exists():
            (HERE / cv).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / cv, HERE / cv)

    metas, ok, added_take, skipped = {}, 0, 0, []
    for rp in reports:
        p = src / rp["file"]
        if not p.exists():
            skipped.append(rp["file"])
            metas[rp["file"]] = {"keywords": [], "glossary": [], "headings": [], "est_min": 5, "source_url": ""}
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        metas[rp["file"]] = scan_report(s)
        if 'id="takeaway"' not in s:
            added_take += 1
        depth = "../" * (len(Path(rp["file"]).parts) - 1)
        out = reskin_report(s, rp, reports, metas[rp["file"]], shelf_name, sec_name, depth_prefix=depth)
        if out is None:
            skipped.append(rp["file"])
            continue
        dst = HERE / rp["file"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(out, encoding="utf-8")
        ok += 1

    (HERE / "data").mkdir(exist_ok=True)
    n = build_data_js(data, reports, metas, HERE / "data/reports.js")

    print(f"✅ V03 產出：報告 {ok} 篇（其中 {added_take} 篇自動補了「三句話帶走」）")
    print(f"   data/reports.js：{n} 篇｜data/store.js 與 data/config.js 不動（手維護）")
    if skipped:
        print(f"   ⚠️ 略過 {len(skipped)}：{skipped}")
    print(f"   首頁（手寫、不由這支產生）：{HERE / 'index.html'}")


if __name__ == "__main__":
    main()
