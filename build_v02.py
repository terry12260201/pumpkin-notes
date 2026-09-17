#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小南瓜數位筆記 V02（墨金美學版）產生器。

只「讀」V01 分享庫（~/pumpkin-digital-notes），產出全新的一份到本資料夾：
  • index.html            首頁（墨金目錄風）
  • gaiconf-2026/*.html   報告（換皮：換掉 <style>、重排頁首／目錄／延伸閱讀，內文一字不改）
  • youtube/*.html
  • covers/*              封面照抄

V01 完全不動。V01 加了新報告後，重跑一次就同步：
  python3 build_v02.py
  python3 build_v02.py --src <V01 路徑>
"""
import argparse, html, json, re, shutil, sys
from datetime import date
from pathlib import Path

E = html.escape
HERE = Path(__file__).resolve().parent
KIT = Path.home() / ".claude/skills/pumpkin-ink-gold/references/ink-gold.css"

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
    "image": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
    "tag": '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.2"/>',
    "layers": '<path d="M12 2 2 7l10 5 10-5z"/><path d="m2 12 10 5 10-5"/><path d="m2 17 10 5 10-5"/>',
    "file": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "filter": '<path d="M4 6h16M7 12h10M10 18h4"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "list": '<rect x="3" y="4" width="6" height="6" rx="1.5"/><rect x="3" y="14" width="6" height="6" rx="1.5"/><path d="M13 6h8M13 9h5M13 16h8M13 19h5"/>',
    "down": '<path d="m6 9 6 6 6-6"/>',
    "spark": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16v4M17 18h4"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    "list-tree": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
}


def sprite(names):
    sym = "".join(f'<symbol id="i-{n}" {_S}>{ICONS[n]}</symbol>' for n in names)
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
            '<linearGradient id="pn-gold" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FDC302"/>'
            '<stop offset="1" stop-color="#FFD83A"/></linearGradient></defs>' + sym + '</svg>')


def ic(name, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f'<svg{c} aria-hidden="true"><use href="#i-{name}"/></svg>'


# 自家 Logo：金色南瓜符號（深炭底用）。16px 也認得出來：圓胖外形＋兩道瓣線＋梗
def pumpkin_mark(size=28):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" aria-hidden="true">'
            '<path d="M16 9.2c-2.6-1.9-8.4-1.6-10.6 3.2-2 4.4-.7 10.7 4 12.6 2.3.9 4.5.6 6.6-.3 2.1.9 4.3 1.2 6.6.3 '
            '4.7-1.9 6-8.2 4-12.6-2.2-4.8-8-5.1-10.6-3.2z" fill="url(#pn-gold)"/>'
            '<path d="M16 10.5v13.8M11.2 9.6c-1.8 3.8-1.8 10 .2 14.6M20.8 9.6c1.8 3.8 1.8 10-.2 14.6" '
            'stroke="#2D2B2C" stroke-width="1.4" stroke-linecap="round" fill="none" opacity=".55"/>'
            '<path d="M16 9.4c0-2.4.9-4.1 3-5" stroke="#FFD83A" stroke-width="2" stroke-linecap="round" fill="none"/></svg>')


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


# ───────────────────────── 從報告撈搜尋材料（同 V01 規則） ─────────────────────────
def scan_report(s):
    s2 = re.sub(r"data:image/[^\"']{50,}", "", s)
    out = {"keywords": [], "level": "", "read_min": ""}
    for key, name in (("keywords", "pn:keywords"), ("level", "pn:level"), ("read_min", "pn:read-min")):
        m = re.search(rf'name="{name}" content="([^"]*)"', s2)
        if m:
            out[key] = [k for k in html.unescape(m.group(1)).split("|") if k] if key == "keywords" else m.group(1)
    out["glossary"] = [plain(t) for t in re.findall(r'<tr id="g-[^"]+"><td><b>(.*?)</b>', s2)]
    out["headings"] = [plain(strip_lead_emoji(t)) for t in re.findall(r"<h2[^>]*>(.*?)</h2>", s2, re.S)]
    # 章節字數估讀秒（沒有 read-min 時用）：中文約 450 字／分
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s2, flags=re.S)
    n = len(re.sub(r"\s", "", plain(body)))
    out["est_min"] = max(3, round(n / 450))
    return out


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


# ═════════════════════════ 報告換皮 ═════════════════════════
H1_SPLIT = re.compile(r"^(.+?)([：，？])(.+)$")
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

    # 2) 章節：去開頭 emoji、時間區段變眉標、編號
    body = m_body.group(1)
    body = re.sub(r"<!--PN:RELATED-->.*?<!--/PN:RELATED-->", "", body, flags=re.S)
    # Obsidian 內部連結 [[slug|顯示字]] 在網頁上只留顯示字（不外露內部筆記檔名）
    body = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", body)
    body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)
    sec_ids, sec_titles = [], {}
    counter = [0]

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
            sec_titles[sid] = plain(h)
            inner = inner.replace(hm.group(0), f'<p class="pn-eb">{eb}</p><h2>{h.strip()}</h2>', 1)
        sec_ids.append(sid)
        # 區塊開頭的 emoji（callout 的小圖示）拿掉，改由 CSS 畫左側色條
        inner = re.sub(r'(<p class="(?:note|quote|danger|money|big|small)"[^>]*>)(.*?)(</p>)',
                       lambda x: x.group(1) + strip_lead_emoji(x.group(2)) + x.group(3), inner, flags=re.S)
        inner = re.sub(r'(<div class="step">\s*<p>)(.*?)(</p>)',
                       lambda x: x.group(1) + strip_lead_emoji(x.group(2)) + x.group(3), inner, flags=re.S)
        inner = re.sub(r"<h([34])>(.*?)</h\1>", lambda x: f"<h{x.group(1)}>{strip_lead_emoji(x.group(2))}</h{x.group(1)}>", inner, flags=re.S)
        stage = sid in ("pumpkin", "adopt")
        cls = ' class="pn-stage"' if stage else ""
        return f'<section id="{sid}"{cls}>{inner}</section>'

    body = re.sub(r'<section id="([^"]+)">(.*?)</section>', fix_section, body, flags=re.S)

    # 3) 目錄：跟章節同一套編號
    toc_links = ""
    for i, (href, txt) in enumerate(re.findall(r'<a href="#([^"]+)">(.*?)</a>', m_toc.group(1)), 1):
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

    cover = ""
    if m_cover:
        img = re.search(r"<img[^>]*>", m_cover.group(1))
        if img:
            cover = f'<figure class="pn-cover">{img.group(0)}</figure>'

    kicker = shelf_name.get(rp.get("shelf"), "")
    sec = sec_name.get((rp.get("shelf"), rp.get("section")), "")
    kicker_txt = kicker + (f" · {sec}" if sec else "")
    read_min = meta.get("read_min") or meta.get("est_min")

    doc = REPORT_TEMPLATE
    for k, v in {
        "%%PAGETITLE%%": E(page_title),
        "%%FONTS%%": FONTS,
        "%%KIT%%": kit_css(),
        "%%CSS%%": REPORT_CSS,
        "%%SPRITE%%": sprite(["left", "clock", "list-tree", "arrow", "file"]),
        "%%MARK%%": pumpkin_mark(28),
        "%%HOME%%": depth_prefix + "index.html",
        "%%SHELFHREF%%": depth_prefix + "index.html#shelf-" + E(rp.get("shelf", "")),
        "%%KICKER%%": E(kicker_txt),
        "%%STRONG%%": E(strong),
        "%%LIGHT%%": f'<span class="ig-display__light">{E(light)}</span>' if light else "",
        "%%META%%": (f'{ic("clock")}<span class="ig-num">{E(rp.get("duration",""))}</span><span class="pn-dot"></span>'
                     f'讀約 <span class="ig-num">{read_min}</span> 分<span class="pn-dot"></span>'
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
<title>%%PAGETITLE%%</title>
%%FONTS%%
<style>
%%KIT%%
%%CSS%%
</style></head><body class="ig pn-report">
%%SPRITE%%
<div class="pn-progress" aria-hidden="true"><i id="pn-bar"></i></div>
<nav class="ig-nav pn-nav" aria-label="主選單">
  <a class="ig-nav__brand" href="%%HOME%%">%%MARK%%小南瓜數位筆記</a>
  <span class="pn-nav__title" id="pn-navtitle">%%STRONG%%</span>
  <div class="ig-nav__right"><a class="ig-btn ig-btn--line ig-btn--sm" href="%%HOME%%"><svg><use href="#i-left"/></svg>全部筆記</a></div>
</nav>

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
%%RELATED%%
      <footer class="pn-foot">%%FOOTER%%</footer>
    </article>
  </div>
</main>
<script>
(function(){
  var bar=document.getElementById('pn-bar');
  function prog(){var h=document.documentElement,max=h.scrollHeight-h.clientHeight;bar.style.width=(max>0?(h.scrollTop/max*100):0)+'%';}
  document.addEventListener('scroll',prog,{passive:true});prog();
  var links=[].slice.call(document.querySelectorAll('[data-toc]'));
  if('IntersectionObserver' in window){
    var map={};links.forEach(function(a){map[a.dataset.toc]=a;});
    var io=new IntersectionObserver(function(es){es.forEach(function(e){
      if(e.isIntersecting&&map[e.target.id]){links.forEach(function(a){a.classList.remove('is-active');});map[e.target.id].classList.add('is-active');}
    });},{rootMargin:'-30% 0px -60% 0px'});
    [].forEach.call(document.querySelectorAll('.pn-article section[id]'),function(s){io.observe(s);});
  }
})();
</script>
</body></html>"""

REPORT_CSS = r"""
/* ── 小南瓜數位筆記 V02：報告頁 ── */
.pn-progress{position:fixed;top:0;left:0;right:0;height:3px;z-index:40;pointer-events:none}
.pn-progress i{display:block;height:100%;width:0;background:var(--ig-gold-gradient);transition:width 80ms linear}
.pn-nav{margin:16px 24px 0}
@media(min-width:1328px){.pn-nav{margin:16px auto 0}}
.pn-nav .ig-nav__brand{margin-right:0;white-space:nowrap}
.pn-nav__title{flex:1;min-width:0;margin:0 16px;padding-left:16px;border-left:1px solid rgba(255,255,255,.12);font-size:14px;color:var(--ig-on-night-soft);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pn-nav .ig-nav__right{margin-left:0}
.pn-nav .ig-btn svg{width:14px;height:14px}
@media(max-width:640px){.pn-nav{margin:12px 12px 0}.pn-nav__title{display:none}.pn-nav .ig-nav__right{margin-left:auto}}

.pn-doc{padding-top:56px}
.pn-hero{display:grid;grid-template-columns:1.08fr 1fr;gap:48px;align-items:center;padding-bottom:36px}
@media(max-width:900px){.pn-hero{grid-template-columns:minmax(0,1fr);gap:28px}}
.pn-title{margin:18px 0 20px;font-size:clamp(32px,3.9vw,50px)}
.pn-title span{text-wrap:balance}
.pn-title .ig-display__light{margin-top:4px}
.pn-meta{display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:14px;color:var(--ig-ink-soft)}
.pn-meta svg{width:16px;height:16px}
.pn-meta .ig-num{color:var(--ig-ink)}
.pn-dot{width:3px;height:3px;border-radius:50%;background:var(--ig-ink-faint);margin:0 4px}
.pn-cover{margin:0;border-radius:var(--ig-r-lg);overflow:hidden;line-height:0;border:1px solid var(--ig-ink-hairline);background:var(--ig-night);box-shadow:var(--ig-shadow-hover)}
.pn-cover img{width:100%;display:block;aspect-ratio:16/9;object-fit:cover}

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

.pn-layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:48px;margin-top:56px;align-items:start}
.pn-toc{position:sticky;top:100px;max-height:calc(100vh - 120px);overflow:auto;padding-right:4px}
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
  .pn-toc__list a.is-active{background:var(--ig-ink);border-color:var(--ig-ink);color:#fff;border-radius:999px}
  .pn-toc__list a.is-active .pn-toc__n{color:rgba(255,255,255,.5)}
}

/* 章節白卡 */
.pn-article{min-width:0;max-width:800px}
.pn-article section{background:var(--ig-card);border:1px solid var(--ig-ink-hairline);border-radius:var(--ig-r-card);padding:36px 40px;margin:0 0 14px;scroll-margin-top:96px;color:#4A4849;font-size:16.5px;line-height:1.85;overflow-wrap:anywhere}
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

/* 名詞：點線底＋等寬問號 */
.pn-article .term{color:var(--ig-ink);font-weight:600;text-decoration:none;border-bottom:1.5px dotted var(--ig-ink-soft);cursor:help;transition:border-color var(--ig-fast) var(--ig-ease)}
.pn-article .term:hover{border-bottom-color:var(--ig-gold)}
.pn-article .term::after{content:"?";font:500 10px/1 var(--ig-font-mono);vertical-align:super;margin-left:2px;color:var(--ig-ink-soft)}

/* 重點框 */
.pn-article .quote{margin:18px 0;padding:4px 0 4px 20px;border-left:3px solid var(--ig-ink);font-size:17px;line-height:1.85;color:var(--ig-ink)}
.pn-article .note,.pn-article .danger,.pn-article .money{margin:18px 0;padding:14px 20px;border-radius:4px 14px 14px 4px;font-size:15.5px;line-height:1.8}
.pn-article .note{background:var(--ig-card-alt);border:1px solid var(--ig-ink-hairline);border-left:3px solid var(--ig-gold)}
.pn-article .danger{background:#FEF2F2;border:1px solid rgba(220,38,38,.12);border-left:3px solid var(--ig-danger)}
.pn-article .money{background:var(--ig-card-alt);border:1px solid var(--ig-ink-hairline);border-left:3px solid var(--ig-night)}
.pn-article .step{background:var(--ig-card-alt);border:1px solid var(--ig-ink-hairline);border-radius:14px;padding:4px 20px;margin:16px 0}
.pn-article .big{font-size:19px;font-weight:600;line-height:1.7;color:var(--ig-ink)}
.pn-article .big b{background:linear-gradient(transparent 60%,var(--ig-mark-yellow) 60%,var(--ig-mark-yellow) 92%,transparent 92%)}
.pn-article .small{font-size:14px;line-height:1.75;color:var(--ig-ink-muted)}
.pn-article .num{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--ig-night);color:#fff;font:500 12px/1 var(--ig-font-mono)}
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
@media print{.pn-nav,.pn-progress,.pn-toc{display:none}.pn-layout{grid-template-columns:1fr}body.ig{background:#fff}}
"""


# ═════════════════════════ 首頁 ═════════════════════════
def build_index(src, data, reports, metas):
    site = data.get("site", {})
    fams = data.get("tag_families", [])
    shelves = data.get("shelves", [])
    shelf_name = {s["id"]: s["name"] for s in shelves}
    sec_name = {(s["id"], x["id"]): x["name"] for s in shelves for x in s.get("sections", [])}
    tag_count = {}
    for r in reports:
        for t in r.get("tags", []):
            tag_count[t] = tag_count.get(t, 0) + 1

    def card(rp):
        mt = metas[rp["file"]]
        tags = rp.get("tags", [])
        level = rp.get("level") or mt.get("level", "")
        read = rp.get("read_min") or mt.get("read_min") or mt.get("est_min")
        hay = " ".join(p for p in [
            rp.get("title", ""), rp.get("speaker", ""), rp.get("summary", ""),
            shelf_name.get(rp.get("shelf", ""), ""), sec_name.get((rp.get("shelf"), rp.get("section")), ""),
            rp.get("source", ""), level, " ".join(leaf(t) for t in tags), " ".join(tags),
            " ".join(rp.get("keywords", []) + mt["keywords"]), " ".join(mt["glossary"]), " ".join(mt["headings"])] if p).lower()
        cv = rp.get("cover", "")
        cover = (f'<div class="nc__cv"><img loading="lazy" src="{E(cv)}" alt=""></div>' if cv
                 else f'<div class="nc__cv nc__cv--none">{pumpkin_mark(40)}</div>')
        show, more = tags[:3], len(tags) - 3
        tag_html = "".join(f'<span class="ig-tag nc__tag" data-tag="{E(t)}" role="button" tabindex="0">{E(leaf(t))}</span>' for t in show)
        if more > 0:
            tag_html += f'<span class="ig-tag nc__more">+{more}</span>'
        src_label = {"gaiconf": "GAICONF", "youtube": "YOUTUBE", "YouTube": "YOUTUBE"}.get(rp.get("source", ""), (rp.get("source") or "VIDEO").upper())
        spk = rp.get("speaker", "")
        return f"""<a class="ig-card ig-card--link nc" href="{E(rp['file'])}" data-tags="{E('|'.join(tags))}" data-hay="{E(hay)}"
 data-date="{E(rp.get('date',''))}" data-dur="{dur_sec(rp.get('duration',''))}" data-level="{E(level)}" data-shelf="{E(rp.get('shelf',''))}">
  {cover}
  <div class="nc__body">
    <p class="nc__meta"><span>{E(src_label)}</span><span class="nc__sep"></span>{ic('clock')}<span>{E(rp.get('duration',''))}</span><span class="nc__sep"></span><span>讀約 {read} 分</span></p>
    <h3 class="nc__title">{E(rp['title'])}</h3>
    <p class="nc__spk">{E(spk)}</p>
    <p class="nc__desc">{E(rp.get('summary',''))}</p>
    <div class="nc__foot"><div class="nc__tags">{tag_html}</div><span class="nc__date">{E(rp.get('date',''))}</span></div>
  </div>
  {ic('arrow', 'ig-tool__arrow nc__arrow')}
</a>"""

    shelves_html = ""
    for si, sh in enumerate(shelves, 1):
        items = [r for r in reports if r.get("shelf") == sh["id"]]
        if not items:
            continue
        inner, used = "", set()
        for sec in sh.get("sections", []):
            sub = sorted([r for r in items if r.get("section") == sec["id"]], key=lambda r: r.get("date", ""), reverse=True)
            if not sub:
                continue
            used.update(r["file"] for r in sub)
            inner += (f'<div class="sec" data-sec><div class="sec__h"><span>{E(sec["name"])}</span>'
                      f'<span class="sec__rule"></span><span class="ig-num sec__n">{len(sub)}</span></div>'
                      f'<div class="nc-grid">{"".join(card(r) for r in sub)}</div></div>')
        rest = sorted([r for r in items if r["file"] not in used], key=lambda r: r.get("date", ""), reverse=True)
        if rest:
            head = (f'<div class="sec__h"><span>其他</span><span class="sec__rule"></span><span class="ig-num sec__n">{len(rest)}</span></div>'
                    if sh.get("sections") else "")
            inner += f'<div class="sec" data-sec>{head}<div class="nc-grid">{"".join(card(r) for r in rest)}</div></div>'
        shelves_html += f"""<section class="shelf" data-shelf="{E(sh['id'])}" id="shelf-{E(sh['id'])}">
  <div class="shelf__h">
    <div><p class="ig-eyebrow">Shelf {si:02d}</p><h3 class="shelf__t">{E(sh['name'])}</h3><p class="ig-small">{E(sh.get('desc',''))}</p></div>
    <span class="ig-kicker"><span class="ig-num shelf__n">{len(items)}</span> 篇</span>
  </div>
  {inner}
</section>"""

    shelf_pills = f'<button class="ig-pill is-active" data-shelfpill="">全部<span class="ig-pill__n">{len(reports)}</span></button>'
    for sh in shelves:
        n = sum(1 for r in reports if r.get("shelf") == sh["id"])
        if n:
            shelf_pills += f'<button class="ig-pill" data-shelfpill="{E(sh["id"])}">{E(sh["name"])}<span class="ig-pill__n">{n}</span></button>'

    filters = ""
    for f in fams:
        tags = sorted({t for r in reports for t in r.get("tags", []) if fam_of(t) == f["id"]}, key=lambda t: (-tag_count[t], t))
        if not tags:
            continue
        pills = "".join(f'<button class="ig-pill ft" data-tag="{E(t)}">{E(leaf(t))}<span class="ig-pill__n">{tag_count[t]}</span></button>' for t in tags)
        filters += f'<div class="frow"><p class="frow__l">{E(f["name"])}</p><div class="ig-pills">{pills}</div></div>'
    levels = [l for l in ["入門", "進階", "深入"] if any((r.get("level") or metas[r["file"]].get("level")) == l for r in reports)]
    if levels:
        filters += ('<div class="frow"><p class="frow__l">難度</p><div class="ig-pills">'
                    + "".join(f'<button class="ig-pill lv" data-level="{l}">{l}</button>' for l in levels) + '</div></div>')

    total_sec = sum(dur_sec(r.get("duration", "")) for r in reports)
    hrs, mins = total_sec // 3600, (total_sec % 3600) // 60
    ntags = len(tag_count)
    latest = max(reports, key=lambda r: r.get("date", ""))
    title = re.sub(r"^\W+", "", site.get("title", "小南瓜數位筆記")).strip() or "小南瓜數位筆記"

    doc = INDEX_TEMPLATE
    for k, v in {
        "%%TITLE%%": E(title),
        "%%FONTS%%": FONTS,
        "%%KIT%%": kit_css(),
        "%%CSS%%": INDEX_CSS,
        "%%SPRITE%%": sprite(["search", "arrow", "right", "play", "image", "clock", "book", "tag", "layers", "file",
                              "link", "lock", "filter", "grid", "list", "down", "spark", "x", "copy"]),
        "%%MARK%%": pumpkin_mark(28),
        "%%MARK_BIG%%": pumpkin_mark(60),
        "%%N%%": str(len(reports)),
        "%%NSHELF%%": str(sum(1 for s in shelves if any(r.get("shelf") == s["id"] for r in reports))),
        "%%NTAGS%%": str(ntags),
        "%%HOURS%%": f'{hrs}<small> 小時 </small>{mins}<small> 分</small>' if hrs else f'{mins}<small> 分</small>',
        "%%TODAY%%": date.today().isoformat(),
        "%%LATEST_HREF%%": E(latest["file"]),
        "%%LATEST_DATE%%": E(latest.get("date", "")),
        "%%SHELFPILLS%%": shelf_pills,
        "%%FILTERS%%": filters,
        "%%SHELVES%%": shelves_html,
    }.items():
        doc = doc.replace(k, v)
    (HERE / "index.html").write_text(doc, encoding="utf-8")


INDEX_TEMPLATE = r"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>%%TITLE%%</title>
%%FONTS%%
<style>
%%KIT%%
%%CSS%%
</style></head><body class="ig">
%%SPRITE%%
<nav class="ig-nav pn-nav" aria-label="主選單">
  <a class="ig-nav__brand" href="#top">%%MARK%%%%TITLE%%</a>
  <div class="ig-nav__links">
    <a class="ig-nav__link is-active" href="#library">筆記書架</a>
    <a class="ig-nav__link" href="#how">怎麼讀</a>
  </div>
  <div class="ig-nav__right"><span class="pn-nav__meta"><span class="ig-live"></span><span class="ig-num">%%LATEST_DATE%%</span> 更新</span></div>
</nav>

<main class="ig-container ig-container--wide" id="top">
  <section class="hero">
    <div>
      <span class="ig-kicker">影片筆記 · 白話圖文報告</span>
      <h1 class="ig-display">
        <span class="ig-display__strong">一支影片</span>
        <span class="ig-display__light">變一頁看得懂的重點</span>
      </h1>
      <p class="ig-lead">白話寫、<span class="ig-mark">截圖標重點</span>、專有名詞附小辭典。用書架收好，用標籤找回來。</p>
      <div class="hero__cta">
        <a class="ig-btn ig-btn--gold ig-btn--lg" href="#library">開始找筆記 <svg><use href="#i-right"/></svg></a>
        <a class="ig-btn ig-btn--ghost ig-btn--lg" href="%%LATEST_HREF%%">讀最新一篇</a>
      </div>
    </div>

    <div class="hub" aria-hidden="true">
      <svg class="lines" viewBox="0 0 100 91" preserveAspectRatio="none">
        <defs><linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="#FDC302" stop-opacity="0"/><stop offset=".5" stop-color="#FDC302" stop-opacity=".75"/><stop offset="1" stop-color="#FDC302" stop-opacity="0"/></linearGradient></defs>
        <g stroke="url(#ln)" stroke-width=".35" fill="none">
          <path d="M50 45.5 20 17"/><path d="M50 45.5 82 15"/><path d="M50 45.5 12 57"/><path d="M50 45.5 89 55"/><path d="M50 45.5 30 84"/><path d="M50 45.5 72 83"/>
        </g>
      </svg>
      <div class="hub__core">%%MARK_BIG%%</div>
      <div class="float float--pink" style="left:9%;top:8%;rotate:-10deg;animation-delay:-1s"><svg><use href="#i-play"/></svg><span>影片</span></div>
      <div class="float" style="right:9%;top:5%;rotate:8deg;animation-delay:-3s"><svg><use href="#i-image"/></svg><span>截圖</span></div>
      <div class="float float--blue" style="left:1%;top:48%;rotate:6deg;animation-delay:-2s"><svg><use href="#i-clock"/></svg><span>時間戳</span></div>
      <div class="float float--gold" style="right:1%;top:46%;rotate:-7deg;animation-delay:-4s"><svg><use href="#i-book"/></svg><span>小辭典</span></div>
      <div class="float" style="left:20%;bottom:0;rotate:-5deg;animation-delay:-5s"><svg><use href="#i-tag"/></svg><span>標籤</span></div>
      <div class="float float--ink" style="right:18%;bottom:1%;rotate:10deg;animation-delay:-2.5s"><svg><use href="#i-file"/></svg><span>報告</span></div>
    </div>
  </section>

  <section class="stats">
    <div class="ig-card ig-stat"><svg><use href="#i-file"/></svg><div><div class="ig-stat__n">%%N%%</div><div class="ig-stat__l">篇筆記</div></div></div>
    <div class="ig-card ig-stat"><svg><use href="#i-layers"/></svg><div><div class="ig-stat__n">%%NSHELF%%</div><div class="ig-stat__l">個書架</div></div></div>
    <div class="ig-card ig-stat"><svg><use href="#i-tag"/></svg><div><div class="ig-stat__n">%%NTAGS%%</div><div class="ig-stat__l">個標籤</div></div></div>
    <div class="ig-card ig-stat"><svg><use href="#i-play"/></svg><div><div class="ig-stat__n">%%HOURS%%</div><div class="ig-stat__l">影片濃縮成筆記</div></div></div>
  </section>

  <section class="ig-section lib" id="library">
    <div class="dir-head">
      <div>
        <span class="ig-eyebrow">Library · 筆記書架</span>
        <h2 class="ig-h2" style="margin-top:8px">找一篇來讀</h2>
      </div>
      <span class="ig-meta" id="cnt">顯示 %%N%% / %%N%% 篇</span>
    </div>

    <div class="dir-tools">
      <label class="ig-search"><svg><use href="#i-search"/></svg>
        <input id="q" type="search" placeholder="搜尋標題、講者、關鍵字、辭典裡的詞、章節…" autocomplete="off"><span class="ig-kbd">/</span></label>
      <p class="hint">空一格＝兩個都要有，例如「agent 成本」。卡片上的標籤點了也能篩。</p>
      <div class="toolbar">
        <div class="ig-pills" id="shelfpills">%%SHELFPILLS%%</div>
        <div class="toolbar__r">
          <button class="ig-btn ig-btn--ghost ig-btn--sm" id="ft" aria-expanded="false"><svg><use href="#i-filter"/></svg>標籤篩選<span class="ft-n" id="ftn"></span><svg class="ft-caret"><use href="#i-down"/></svg></button>
          <label class="sortbox"><span class="ig-meta">排序</span>
            <select id="sort"><option value="date">最新在前</option><option value="short">最短先看</option><option value="title">照標題</option></select></label>
          <div class="viewsw" role="group" aria-label="檢視方式">
            <button class="vbtn is-on" data-view="grid" title="卡片"><svg><use href="#i-grid"/></svg></button>
            <button class="vbtn" data-view="list" title="清單"><svg><use href="#i-list"/></svg></button>
          </div>
        </div>
      </div>
      <div class="ig-card fpanel" id="fb" hidden>%%FILTERS%%</div>
      <div class="activebar" id="activebar" hidden>
        <span class="ig-meta" id="activetxt"></span>
        <button class="ig-link linkbtn" id="clr"><svg><use href="#i-x"/></svg>清除條件</button>
        <button class="ig-link linkbtn" id="share"><svg><use href="#i-link"/></svg>複製這個篩選結果的網址</button>
      </div>
    </div>

    <div id="shelves">%%SHELVES%%</div>
    <p class="empty" id="empty">沒有符合的筆記。換個關鍵字，或少選幾個標籤試試。</p>
  </section>

  <section class="ig-stage how" id="how">
    <div class="how__head">
      <span class="ig-eyebrow">How to read · 怎麼讀</span>
      <h2 class="ig-h2" style="margin:10px 0 12px">每一篇都照同一個格式寫</h2>
      <p class="ig-lead">不用看完整支影片。先讀一句話大綱，想細看再點時間戳回原片。</p>
    </div>
    <div class="how__grid">
      <div class="ig-stage-card"><svg><use href="#i-spark"/></svg><h3>一句話大綱</h3><p class="ig-small">開頭先講整場在說什麼，30 秒決定要不要往下讀。</p></div>
      <div class="ig-stage-card"><svg><use href="#i-image"/></svg><h3>截圖＝重點</h3><p class="ig-small">每張截圖都是一個重點，旁邊寫白話說明。</p></div>
      <div class="ig-stage-card"><svg><use href="#i-play"/></svg><h3>時間戳可以點</h3><p class="ig-small">點 <span class="ig-num">▶ 3:26</span> 直接跳回影片那一秒。登入型平台要自己拉進度條。</p></div>
      <div class="ig-stage-card"><svg><use href="#i-book"/></svg><h3>看不懂查辭典</h3><p class="ig-small">有點線底的詞點下去，會跳到文末小辭典。</p></div>
    </div>
    <p class="how__lock"><svg><use href="#i-lock"/></svg>私人分享頁，未被搜尋引擎收錄。連結請勿公開張貼。</p>
  </section>
</main>

<footer class="ig-footer">
  <div class="ig-container ig-container--wide foot">
    <span class="foot__brand">%%MARK%%%%TITLE%%</span>
    <span class="ig-meta">V02 墨金版預覽 · 產生於 <span class="ig-num">%%TODAY%%</span></span>
  </div>
</footer>
<div class="toast" id="toast" role="status"></div>

<script>
(function(){
  var $=function(s,r){return (r||document).querySelector(s);}, $$=function(s,r){return [].slice.call((r||document).querySelectorAll(s));};
  var q=$('#q'),fb=$('#fb'),ft=$('#ft'),sortSel=$('#sort'),cards=$$('.nc');
  var picked=[],level='',shelf='',view='grid';
  var webUrl=/^(https?|file):$/.test(location.protocol);
  function toast(m){var t=$('#toast');t.textContent=m;t.classList.add('on');setTimeout(function(){t.classList.remove('on');},1600);}
  function tokens(){return (q.value||'').trim().toLowerCase().split(/\s+/).filter(Boolean);}
  function openPanel(on){fb.hidden=!on;ft.setAttribute('aria-expanded',on?'true':'false');ft.classList.toggle('is-open',on);}
  ft.onclick=function(){openPanel(fb.hidden);};

  function apply(push){
    var tk=tokens(),n=0;
    cards.forEach(function(c){
      var tags=(c.dataset.tags||'').split('|'),hay=c.dataset.hay||'';
      var ok=tk.every(function(t){return hay.indexOf(t)>=0;})
        && picked.every(function(t){return tags.indexOf(t)>=0;})
        && (!level||c.dataset.level===level) && (!shelf||c.dataset.shelf===shelf);
      c.classList.toggle('hid',!ok); if(ok)n++;
    });
    $$('[data-sec]').forEach(function(s){var v=$$('.nc:not(.hid)',s).length;s.classList.toggle('hid',!v);var b=$('.sec__n',s);if(b)b.textContent=v;});
    $$('[data-shelf]').forEach(function(s){if(!s.classList.contains('shelf'))return;var v=$$('.nc:not(.hid)',s).length;s.classList.toggle('hid',!v);var b=$('.shelf__n',s);if(b)b.textContent=v;});
    $('#cnt').textContent='顯示 '+n+' / '+cards.length+' 篇';
    $('#empty').classList.toggle('on',n===0);
    var parts=[];
    if(tk.length)parts.push('關鍵字「'+q.value.trim()+'」');
    if(picked.length)parts.push('標籤 '+picked.map(function(t){return t.split('/').pop();}).join('＋'));
    if(level)parts.push('難度 '+level);
    if(shelf){var p=$('[data-shelfpill="'+shelf+'"]');parts.push('書架 '+(p?p.firstChild.textContent:shelf));}
    $('#activebar').hidden=!parts.length;
    $('#activetxt').textContent=parts.length?('篩選中：'+parts.join('、')+'　→ 找到 '+n+' 篇'):'';
    $('#ftn').textContent=picked.length+(level?1:0)?(' '+(picked.length+(level?1:0))):'';
    if(push!==false&&webUrl){try{
      var u=new URL(location.href);
      tk.length?u.searchParams.set('q',q.value.trim()):u.searchParams.delete('q');
      picked.length?u.searchParams.set('t',picked.join('|')):u.searchParams.delete('t');
      level?u.searchParams.set('lv',level):u.searchParams.delete('lv');
      shelf?u.searchParams.set('s',shelf):u.searchParams.delete('s');
      history.replaceState(null,'',u.pathname+(u.search||'')+u.hash);
    }catch(e){}}
  }
  function sortCards(){
    var mode=sortSel.value;
    $$('.nc-grid').forEach(function(g){
      var cs=$$('.nc',g);
      cs.sort(function(a,b){
        if(mode==='short')return (+a.dataset.dur||1e9)-(+b.dataset.dur||1e9);
        if(mode==='title')return $('.nc__title',a).textContent.localeCompare($('.nc__title',b).textContent,'zh-Hant');
        return (b.dataset.date||'').localeCompare(a.dataset.date||'');
      });
      cs.forEach(function(c){g.appendChild(c);});
    });
  }
  function paintTag(t,on){
    $$('[data-tag]').forEach(function(el){if(el.dataset.tag===t)el.classList.toggle(el.classList.contains('ig-pill')?'is-active':'is-on',on);});
  }
  function toggleTag(t){var i=picked.indexOf(t);if(i>=0)picked.splice(i,1);else picked.push(t);paintTag(t,i<0);apply();}
  function setLevel(l){level=(level===l)?'':l;$$('.lv').forEach(function(c){c.classList.toggle('is-active',c.dataset.level===level);});apply();}
  function setShelf(s){shelf=s;$$('[data-shelfpill]').forEach(function(p){p.classList.toggle('is-active',p.dataset.shelfpill===shelf);});apply();}
  function setView(v){view=v;$('#shelves').classList.toggle('is-list',v==='list');$$('.vbtn').forEach(function(b){b.classList.toggle('is-on',b.dataset.view===v);});try{localStorage.setItem('pn-view',v);}catch(e){}}

  $$('[data-tag]').forEach(function(el){
    var h=function(e){e.preventDefault();e.stopPropagation();toggleTag(el.dataset.tag);};
    el.addEventListener('click',h);
    el.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' ')h(e);});
  });
  $$('.lv').forEach(function(el){el.addEventListener('click',function(){setLevel(el.dataset.level);});});
  $$('[data-shelfpill]').forEach(function(el){el.addEventListener('click',function(){setShelf(el.dataset.shelfpill);});});
  $$('.vbtn').forEach(function(el){el.addEventListener('click',function(){setView(el.dataset.view);});});
  q.addEventListener('input',function(){apply();});
  sortSel.addEventListener('change',sortCards);
  document.addEventListener('keydown',function(e){if(e.key==='/'&&document.activeElement!==q&&!/input|select|textarea/i.test(document.activeElement.tagName)){e.preventDefault();q.focus();}});
  $('#clr').onclick=function(){q.value='';picked=[];level='';$$('.is-active[data-tag],.lv.is-active,.is-on[data-tag]').forEach(function(c){c.classList.remove('is-active','is-on');});setShelf('');};
  $('#share').onclick=function(){var u=location.href;
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(u).then(function(){toast('已複製網址');},function(){prompt('複製這個網址',u);});}
    else{prompt('複製這個網址',u);}};

  try{var sv=localStorage.getItem('pn-view');if(sv)setView(sv);}catch(e){}
  if(webUrl){try{
    var u=new URL(location.href);
    if(u.searchParams.get('q'))q.value=u.searchParams.get('q');
    (u.searchParams.get('t')||'').split('|').filter(Boolean).forEach(function(t){picked.push(t);paintTag(t,true);});
    if(u.searchParams.get('lv')){level=u.searchParams.get('lv');$$('.lv').forEach(function(c){c.classList.toggle('is-active',c.dataset.level===level);});}
    if(u.searchParams.get('s')){shelf=u.searchParams.get('s');$$('[data-shelfpill]').forEach(function(p){p.classList.toggle('is-active',p.dataset.shelfpill===shelf);});}
    if(picked.length||level)openPanel(true);
  }catch(e){}}
  sortCards();apply(false);
})();
</script>
</body></html>"""

INDEX_CSS = r"""
/* ── 小南瓜數位筆記 V02：首頁 ── */
.pn-nav{margin:16px 24px 0}
@media(min-width:1328px){.pn-nav{margin:16px auto 0}}
.pn-nav .ig-nav__brand{margin-right:0}
.pn-nav .ig-nav__links{margin-left:auto}
.pn-nav .ig-nav__right{margin-left:12px;padding-right:10px}
.pn-nav__meta{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--ig-on-night-soft)}
.pn-nav__meta .ig-num{color:var(--ig-on-night-muted)}
@media(max-width:860px){.pn-nav .ig-nav__right{margin-left:auto}}
@media(max-width:640px){.pn-nav{margin:12px 12px 0}}

.hero{display:grid;grid-template-columns:1.05fr 1fr;gap:40px;align-items:center;padding:72px 0 56px}
@media(max-width:900px){.hero{grid-template-columns:1fr;padding-top:48px}}
.hero .ig-display{margin:18px 0 20px}
.hero__cta{display:flex;gap:10px;flex-wrap:wrap;margin-top:28px}

.hub{position:relative;aspect-ratio:1.1;max-width:500px;margin:0 auto;width:100%}
@media(max-width:900px){.hub{max-width:380px}}
.hub svg.lines{position:absolute;inset:0;width:100%;height:100%}
.hub__core{position:absolute;left:50%;top:50%;width:118px;height:118px;transform:translate(-50%,-50%);border-radius:30px;background:var(--ig-night-gradient);box-shadow:var(--ig-shadow-stage),0 0 0 8px rgba(255,255,255,.7);display:grid;place-items:center}
.float{position:absolute;width:78px;height:78px;border-radius:20px;display:grid;place-items:center;align-content:center;gap:4px;background:#fff;border:1px solid var(--ig-ink-hairline);color:var(--ig-ink);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.9),0 18px 30px -18px rgba(22,20,21,.35),0 3px 0 rgba(22,20,21,.06);animation:bob 6s var(--ig-ease) infinite alternate}
.float svg{width:26px;height:26px;stroke-width:1.75}
.float span{font-size:12px;font-weight:500;line-height:1}
.float--gold{background:linear-gradient(160deg,#FFE27A,#FDC302);color:var(--ig-on-gold);border-color:rgba(255,255,255,.6)}
.float--blue{background:linear-gradient(160deg,#DDF2FE,#BAE6FD);color:#1E3A8A}
.float--pink{background:linear-gradient(160deg,#FFE0E5,#FDA4AF);color:#7F1D1D}
.float--ink{background:linear-gradient(160deg,#3A3839,#242223);color:#fff;border-color:#242223}
@keyframes bob{from{translate:0 0}to{translate:0 -10px}}
@media(prefers-reduced-motion:reduce){.float{animation:none}}
@media(max-width:520px){.float{width:64px;height:64px;border-radius:16px}.float svg{width:22px;height:22px}}

.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
@media(max-width:900px){.stats{grid-template-columns:repeat(2,1fr)}}
.ig-stat__n small{font-family:var(--ig-font-sans);font-size:13px;color:var(--ig-ink-soft);font-weight:400}

.lib{padding-bottom:64px}
section[id],.shelf{scroll-margin-top:92px}
.dir-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:20px}
.dir-tools{display:grid;gap:12px;margin-bottom:36px;position:relative}
.ig-search{max-width:640px}
.hint{font-size:13px;color:var(--ig-ink-soft);margin-top:-4px}
.toolbar{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-top:6px}
.toolbar__r{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#ft svg{width:14px;height:14px}
#ft .ft-caret{transition:transform var(--ig-base) var(--ig-ease)}
#ft.is-open .ft-caret{transform:rotate(180deg)}
.ft-n{font-family:var(--ig-font-mono);font-size:12px;color:var(--ig-ink-soft)}
.sortbox{display:inline-flex;align-items:center;gap:8px;height:32px;padding:0 6px 0 14px;border-radius:999px;background:var(--ig-card);border:1px solid var(--ig-ink-hairline)}
.sortbox select{border:0;outline:0;background:transparent;font:500 14px/1 var(--ig-font-sans);color:var(--ig-ink);cursor:pointer;padding:4px 2px}
.viewsw{display:inline-flex;padding:3px;gap:2px;border-radius:999px;background:var(--ig-card);border:1px solid var(--ig-ink-hairline)}
.vbtn{display:grid;place-items:center;width:30px;height:26px;border:0;border-radius:999px;background:transparent;color:var(--ig-ink-soft);cursor:pointer;transition:background-color var(--ig-fast) var(--ig-ease),color var(--ig-fast) var(--ig-ease)}
.vbtn svg{width:16px;height:16px}
.vbtn:hover{color:var(--ig-ink)}
.vbtn.is-on{background:var(--ig-ink);color:#fff}
.fpanel{padding:8px 20px}
.frow{display:grid;grid-template-columns:120px 1fr;gap:12px;align-items:start;padding:12px 0;border-top:1px solid var(--ig-ink-hairline)}
.frow:first-child{border-top:0}
.frow__l{font-size:13px;color:var(--ig-ink-soft);padding-top:6px}
@media(max-width:640px){.frow{grid-template-columns:1fr;gap:6px}}
.fpanel .ig-pill{height:30px;font-size:13px;padding:0 12px}
.activebar{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:10px 16px;border-radius:14px;background:var(--ig-ink-wash)}
.activebar[hidden],.fpanel[hidden]{display:none}
.linkbtn{background:none;border:0;padding:0;font-size:13px;cursor:pointer}
.linkbtn svg{width:14px;height:14px}
.hid{display:none!important}
.empty{display:none;padding:56px 0;text-align:center;color:var(--ig-ink-soft)}
.empty.on{display:block}

.shelf{margin-bottom:56px}
.shelf__h{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;padding-bottom:18px;margin-bottom:22px;border-bottom:1px solid var(--ig-ink-hairline)}
.shelf__t{font-size:26px;font-weight:700;margin:6px 0 4px}
.sec{margin-bottom:30px}
.sec__h{display:flex;align-items:center;gap:12px;margin:0 0 14px;font-size:14px;font-weight:600;color:var(--ig-ink)}
.sec__rule{flex:1;height:1px;background:var(--ig-ink-hairline)}
.sec__n{font-size:12px;color:var(--ig-ink-soft)}

/* 筆記卡（格狀） */
.nc-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr))}
.nc{padding:0;overflow:hidden;display:flex;flex-direction:column}
.nc__cv{aspect-ratio:16/9;background:var(--ig-night);line-height:0;overflow:hidden;border-bottom:1px solid var(--ig-ink-hairline)}
.nc__cv img{width:100%;height:100%;object-fit:cover;transition:transform var(--ig-slow) var(--ig-ease)}
.nc:hover .nc__cv img{transform:scale(1.03)}
.nc__cv--none{display:grid;place-items:center;background:var(--ig-night-gradient)}
.nc__body{padding:16px 18px 18px;display:flex;flex-direction:column;flex:1;min-width:0}
.nc__meta{display:flex;align-items:center;gap:6px;font:500 12px/1 var(--ig-font-mono);color:var(--ig-ink-soft);letter-spacing:.04em}
.nc__meta svg{width:13px;height:13px}
.nc__sep{width:3px;height:3px;border-radius:50%;background:var(--ig-ink-faint);margin:0 2px}
.nc__title{margin:12px 0 4px;font-size:17px;font-weight:600;line-height:1.45;color:var(--ig-ink);padding-right:18px}
.nc__spk{font-size:13px;color:var(--ig-ink-soft);line-height:1.5}
.nc__desc{margin-top:8px;font-size:14px;line-height:1.65;color:var(--ig-ink-muted);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.nc__foot{margin-top:auto;padding-top:14px;display:flex;align-items:center;justify-content:space-between;gap:8px}
.nc__tags{display:flex;gap:6px;flex-wrap:wrap;min-width:0}
.nc__tag{cursor:pointer;transition:background-color var(--ig-fast) var(--ig-ease),color var(--ig-fast) var(--ig-ease)}
.nc__tag:hover{background:rgba(22,20,21,.08);color:var(--ig-ink)}
.nc__tag.is-on{background:var(--ig-ink);color:#fff}
.nc__more{background:transparent;border:1px dashed var(--ig-ink-faint)}
.nc__date{font:400 12px/1 var(--ig-font-mono);color:var(--ig-ink-soft);white-space:nowrap}
.nc .nc__arrow{top:12px;right:12px;width:30px;height:30px;padding:7px;border-radius:50%;background:rgba(255,255,255,.94);color:var(--ig-ink);opacity:0;transition:opacity var(--ig-base) var(--ig-ease),transform var(--ig-base) var(--ig-ease)}
.nc:hover .nc__arrow{opacity:1;color:var(--ig-ink)}

/* 筆記卡（清單） */
#shelves.is-list .nc-grid{grid-template-columns:1fr}
#shelves.is-list .nc{flex-direction:row;align-items:stretch;padding:14px;gap:18px}
#shelves.is-list .nc__cv{flex:0 0 208px;aspect-ratio:16/9;align-self:flex-start;border-radius:var(--ig-r-md);border:1px solid var(--ig-ink-hairline)}
#shelves.is-list .nc__body{padding:2px 36px 0 0}
#shelves.is-list .nc__title{margin-top:8px}
#shelves.is-list .nc__foot{padding-top:10px}
#shelves.is-list .nc .nc__arrow{top:18px;right:18px;width:16px;height:16px;padding:0;background:none;opacity:1;color:var(--ig-ink-faint)}
#shelves.is-list .nc:hover .nc__arrow{color:var(--ig-ink)}
@media(max-width:640px){#shelves.is-list .nc{flex-direction:column;gap:12px}#shelves.is-list .nc__cv{flex-basis:auto;width:100%}}

/* 深色舞台：怎麼讀 */
.how{margin:32px 0 0}
.how__head{max-width:620px;margin-bottom:32px}
.how__grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
@media(max-width:900px){.how__grid{grid-template-columns:1fr 1fr}}
@media(max-width:520px){.how__grid{grid-template-columns:1fr}}
.how .ig-stage-card svg{width:22px;height:22px;color:var(--ig-gold-soft);stroke-width:1.75}
.how .ig-stage-card h3{font-size:16px;font-weight:600;margin:14px 0 6px}
.how .ig-num{color:#fff}
.how__lock{display:flex;align-items:center;gap:8px;margin-top:28px;font-size:13px;color:var(--ig-on-night-soft)}
.how__lock svg{width:15px;height:15px}

.ig-footer{margin-top:64px}
.foot{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
.foot__brand{display:inline-flex;align-items:center;gap:10px;font-weight:700}
.foot__brand svg{background:var(--ig-night);border-radius:8px;padding:3px}

.toast{position:fixed;left:50%;bottom:24px;transform:translate(-50%,8px);background:var(--ig-night);color:#fff;padding:10px 18px;border-radius:999px;font-size:14px;opacity:0;transition:opacity var(--ig-base) var(--ig-ease),transform var(--ig-base) var(--ig-ease);pointer-events:none;box-shadow:var(--ig-shadow-float)}
.toast.on{opacity:1;transform:translate(-50%,0)}
"""


# ═════════════════════════ 主程式 ═════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(Path.home() / "pumpkin-digital-notes"), help="V01 分享庫（只讀）")
    a = ap.parse_args()
    src = Path(a.src).expanduser().resolve()
    if src == HERE:
        sys.exit("❌ 來源不能是 V02 自己")
    data = json.loads((src / "reports.json").read_text(encoding="utf-8"))
    reports = data["reports"]
    shelves = data.get("shelves", [])
    shelf_name = {s["id"]: s["name"] for s in shelves}
    sec_name = {(s["id"], x["id"]): x["name"] for s in shelves for x in s.get("sections", [])}

    # 封面
    for rp in reports:
        cv = rp.get("cover")
        if cv and (src / cv).exists():
            (HERE / cv).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / cv, HERE / cv)

    metas, ok, skipped = {}, 0, []
    for rp in reports:
        p = src / rp["file"]
        if not p.exists():
            skipped.append(rp["file"]); metas[rp["file"]] = {"keywords": [], "glossary": [], "headings": [], "est_min": 5}
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        metas[rp["file"]] = scan_report(s)
        depth = "../" * (len(Path(rp["file"]).parts) - 1)
        out = reskin_report(s, rp, reports, metas[rp["file"]], shelf_name, sec_name, depth_prefix=depth)
        if out is None:
            skipped.append(rp["file"]); continue
        dst = HERE / rp["file"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(out, encoding="utf-8")
        ok += 1

    build_index(src, data, reports, metas)
    print(f"✅ V02 產出：首頁 1 頁／報告 {ok} 篇" + (f"｜略過 {len(skipped)}：{skipped}" if skipped else ""))
    print(f"   位置：{HERE/'index.html'}")


if __name__ == "__main__":
    main()
