#!/usr/bin/env python3
"""
build_index.py — 掃描 reports/*.html，重建整個站台（首頁 + 英文版 + sitemap）。

用法：
    python3 build_index.py

每份日報必須在 <head> 內含下列 meta 標籤，本腳本靠它們取得資訊：

    <meta name="report-date"       content="2026-08-16">
    <meta name="report-theme"      content="weekly-review">
    <meta name="report-title-zh"   content="中文標題">
    <meta name="report-title-en"   content="English headline">
    <meta name="report-summary-zh" content="一句話中文摘要">
    <meta name="report-summary-en" content="One-line English summary">

沒有這些標籤的檔案會被跳過並在 stdout 提示。腳本不依賴任何第三方套件。
產生的 index.html 已內含 Google Analytics 標籤（G-HJLDQZDK5V）。

一個語言一個網址
----------------
中文在原網址、英文在 /en/ 底下，兩邊是各自獨立的檔案：

    index.html                     en/index.html
    reports/YYYY-MM-DD.html        en/reports/YYYY-MM-DD.html

**每一頁只留一種語言的節點**，不是用 CSS 把另一種藏起來——藏起來的話搜尋引擎
兩種語言都讀得到，等於沒有分開。每一頁的 <head> 帶：canonical 指自己、三行
hreflang（zh-Hant / en / x-default 指中文版）、og:url；語言切換是真的 <a href>，
不是 JavaScript，這樣爬蟲才走得過去。

新的日報寫進 reports/ 時仍然是中英文並排的單一檔案，本腳本會在建置時把它拆成
上面兩份；已經拆過的檔案不會再被動。所以日報產生流程不需要改，照舊丟進
reports/ 再跑一次本腳本即可。
"""

import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(ROOT, "reports")
OUT = os.path.join(ROOT, "index.html")

# 星期輪值主題：key -> (中文, English, 色票 index)
THEMES = {
    "clinical":      ("臨床應用與研究", "Clinical & Research",      0),
    "industry":      ("產業與商業動向", "Industry & Business",      1),
    "regulation":    ("法規與政策",     "Regulation & Policy",      2),
    "technology":    ("技術突破",       "Technology",               3),
    "product":       ("產品與公司分析", "Product & Company",        4),
    "general-ai":    ("廣義 AI 新知",   "General AI",               5),
    "weekly-review": ("本週回顧",       "Weekly Review",            6),
}
FALLBACK_THEME = ("其他", "Other", 7)

META_RE = {
    "date":       re.compile(r'<meta\s+name="report-date"\s+content="([^"]*)"', re.I),
    "theme":      re.compile(r'<meta\s+name="report-theme"\s+content="([^"]*)"', re.I),
    "title_zh":   re.compile(r'<meta\s+name="report-title-zh"\s+content="([^"]*)"', re.I),
    "title_en":   re.compile(r'<meta\s+name="report-title-en"\s+content="([^"]*)"', re.I),
    "summary_zh": re.compile(r'<meta\s+name="report-summary-zh"\s+content="([^"]*)"', re.I),
    "summary_en": re.compile(r'<meta\s+name="report-summary-en"\s+content="([^"]*)"', re.I),
}

WEEKDAY_ZH = ["一", "二", "三", "四", "五", "六", "日"]
WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def unescape(s: str) -> str:
    return (s.replace("&amp;", "&").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))


def collect():
    if not os.path.isdir(REPORTS_DIR):
        print(f"! 找不到 {REPORTS_DIR}")
        return []

    items, skipped = [], []
    for fn in sorted(os.listdir(REPORTS_DIR)):
        if not fn.endswith(".html"):
            continue
        path = os.path.join(REPORTS_DIR, fn)
        try:
            with open(path, encoding="utf-8") as f:
                head = f.read(20000)   # meta 一定在檔頭
        except Exception as e:
            skipped.append((fn, f"讀取失敗: {e}"))
            continue

        got = {}
        for key, rx in META_RE.items():
            m = rx.search(head)
            got[key] = unescape(m.group(1).strip()) if m else ""

        # 日期：優先 meta，其次檔名 YYYY-MM-DD.html
        d = got["date"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d or ""):
            m = re.match(r"(\d{4}-\d{2}-\d{2})", fn)
            if not m:
                skipped.append((fn, "缺少 report-date 且檔名非 YYYY-MM-DD"))
                continue
            d = m.group(1)

        y, mo, dd = (int(x) for x in d.split("-"))
        try:
            wd = date(y, mo, dd).weekday()
        except ValueError:
            skipped.append((fn, f"日期無效: {d}"))
            continue

        theme_key = got["theme"] if got["theme"] in THEMES else "other"
        zh, en, ci = THEMES.get(theme_key, FALLBACK_THEME)

        items.append({
            "date": d,
            "file": f"reports/{fn}",
            "theme": theme_key,
            "themeZh": zh,
            "themeEn": en,
            "ci": ci,
            "wdZh": WEEKDAY_ZH[wd],
            "wdEn": WEEKDAY_EN[wd],
            "titleZh": got["title_zh"] or f"{d} 日報",
            "titleEn": got["title_en"] or f"Daily brief for {d}",
            "sumZh": got["summary_zh"],
            "sumEn": got["summary_en"],
        })

    for fn, why in skipped:
        print(f"  跳過 {fn} — {why}")

    items.sort(key=lambda x: x["date"], reverse=True)
    return items


SITE = "https://ai-medical-daily.peteraim.com"
SITEMAP = os.path.join(ROOT, "sitemap.xml")

TWIN_DIR = "en"                                  # 英文版放這個子目錄
LANG_CODE = {"zh": "zh-Hant", "en": "en"}        # hreflang / <html lang> 用的語言碼
ALT_LABEL = {"zh": "中文版", "en": "English version"}

# 頁面標題：中文版沿用原本的，英文版用站台自己的英文名稱（切換鈕本來就是這樣寫的）
TITLE = {
    "index": {"zh": "AI／醫療AI 每日新知日報", "en": "AI &amp; Medical AI Daily"},
    "report": {"zh": "AI／醫療AI 每日新知日報 · {d}", "en": "AI &amp; Medical AI Daily · {d}"},
}
INDEX_DESC = {
    "zh": "每日自動整理的 AI 與醫療 AI 新知、產業動向、法規與產品分析。",
    "en": "Generated automatically at 08:00 Taipei time: the day's news in AI and "
          "medical AI, with product analysis, company moves, competitive read, "
          "further reading and full references.",
}

# 只有英文版要改的屬性：原文把兩種語言塞在同一個 title / aria-label 裡，
# 拆開之後英文頁不該再出現中文。中文版一個字都不動。
EN_ATTRS = [
    ('title="回到日報首頁"', 'title="Back to all reports"'),
    ('aria-label="回到日報首頁 / Back to all reports"',
     'aria-label="Back to all reports"'),
    ('aria-label="Star this project on GitHub / 在 GitHub 給這個專案一顆星"',
     'aria-label="Star this project on GitHub"'),
    ('aria-label="Back to peteraim.com / 返回 peteraim.com"',
     'aria-label="Back to peteraim.com"'),
    ('placeholder="搜尋標題、摘要或日期…"',
     'placeholder="Search titles, summaries or dates…"'),
]

# 舊版日報把樣式寫在頁內，新版共用 assets/report.css（那一份已經改好）。頁內版
# 要做兩件事：拿掉「用 CSS 藏起另一種語言」的規則，以及讓切換鈕從 <button> 變 <a>。
OLD_LANG_CSS = ("body.lang-zh .en, body.lang-en .zh{display:none}\n"
                "body.lang-zh .en-inline, body.lang-en .zh-inline{display:none}\n"
                ".en-inline,.zh-inline{display:inline}\n")
NEW_LANG_CSS = (".lang-alt-link{margin:0}\n"
                ".lang-alt-link a{color:var(--accent);text-decoration:none;"
                "font-weight:600}\n")
OLD_SEG_CSS = """.seg button{
  border:0;background:transparent;color:var(--muted);font-family:inherit;
  padding:5px 13px;font-size:13px;font-weight:600;cursor:pointer;transition:.15s
}
.seg button.on{background:var(--accent);color:#fff}"""
NEW_SEG_CSS = """.seg a{
  border:0;background:transparent;color:var(--muted);font-family:inherit;
  padding:5px 13px;font-size:13px;font-weight:600;cursor:pointer;transition:.15s;
  display:flex;align-items:center;justify-content:center;
  text-decoration:none;line-height:normal
}
.seg a.on{background:var(--accent);color:#fff}"""

SEG_BUTTONS = """    <div class="seg">
      <button id="b-zh" class="on" onclick="setLang('zh')">中文</button>
      <button id="b-en" onclick="setLang('en')">EN</button>
    </div>"""

SPAN_OPEN = re.compile(r"<span\b[^>]*>", re.I)
SPAN_CLOSE = re.compile(r"</span\s*>", re.I)
LANG_SPAN = re.compile(r'<span class="(zh|en|zh-inline|en-inline)">')
SETLANG = re.compile(r"function setLang\(l\)\{.*?\n\}\n", re.S)


def path_of(rel: str) -> str:
    """頁面的站內路徑。index.html 用目錄形式（結尾斜線），與既有 canonical 一致。"""
    if os.path.basename(rel) == "index.html":
        d = os.path.dirname(rel)
        return f"/{d}/" if d else "/"
    return "/" + rel


def url_of(rel: str) -> str:
    return SITE + path_of(rel)


def twin_of(rel: str) -> str:
    return f"{TWIN_DIR}/{rel}"


def lang_spans(src: str):
    """找出每一個語言節點的起訖位置。<span> 會巢狀（標籤裡還有標籤），
       所以要數進出的層數，不能用最近的 </span>。"""
    out = []
    for m in LANG_SPAN.finditer(src):
        depth, i = 1, m.end()
        while depth:
            o, c = SPAN_OPEN.search(src, i), SPAN_CLOSE.search(src, i)
            if c is None:
                raise SystemExit(f"! 找不到對應的 </span>（位置 {m.start()}）")
            if o and o.start() < c.start():
                depth, i = depth + 1, o.end()
            else:
                depth, i = depth - 1, c.end()
        out.append((m.start(), i, m.group(1)))
    return out


def keep_only(src: str, lang: str) -> str:
    """把另一種語言的節點整個刪掉。整行只有那個節點時連同該行一起刪，
       免得留下一堆只有縮排的空行。"""
    drop = {"zh": ("en", "en-inline"), "en": ("zh", "zh-inline")}[lang]
    for start, end, cls in reversed(lang_spans(src)):
        if cls not in drop:
            continue
        line_start = src.rfind("\n", 0, start) + 1
        nl = src.find("\n", end)
        rest = src[end:] if nl == -1 else src[end:nl]
        if src[line_start:start].strip() == "" and rest.strip() == "":
            src = src[:line_start] + ("" if nl == -1 else src[nl + 1:])
        else:
            src = src[:start] + src[end:]
    return src


def lang_switch(rel: str, lang: str) -> str:
    """語言切換：兩個都是真的連結，各自指向這一頁的另一個語言版本。"""
    def link(code, href, label):
        cls = ' class="on"' if code == lang else ''
        state = ' aria-current="page"' if code == lang else ' rel="alternate"'
        return (f'<a{cls} href="{href}" hreflang="{LANG_CODE[code]}"'
                f' lang="{LANG_CODE[code]}"{state}>{label}</a>')
    return ('    <div class="seg">\n'
            f'      {link("zh", path_of(rel), "中文")}\n'
            f'      {link("en", path_of(twin_of(rel)), "EN")}\n'
            '    </div>')


def hreflang_trio(rel: str) -> str:
    """兩個語言版本放的是完全相同的三行，缺一行或兩邊不一致就整組失效。
       x-default 指中文版，因為那是這個站的主要語言。"""
    zh_url, en_url = url_of(rel), url_of(twin_of(rel))
    return "\n".join([
        f'<link rel="alternate" hreflang="zh-Hant" href="{zh_url}" />',
        f'<link rel="alternate" hreflang="en" href="{en_url}" />',
        f'<link rel="alternate" hreflang="x-default" href="{zh_url}" />',
    ])


def set_head(src: str, rel: str, lang: str, title: str, desc: str) -> str:
    """<head> 手術：語言碼、標題、canonical（指自己）、hreflang、og:url、描述。"""
    page = twin_of(rel) if lang == "en" else rel
    canonical = url_of(page)
    src = re.sub(r'(<html lang=")[^"]*(")', lambda m: m.group(1) + LANG_CODE[lang]
                 + m.group(2), src, count=1)
    src = re.sub(r"(?s)(<title>).*?(</title>)",
                 lambda m: m.group(1) + title + m.group(2), src, count=1)
    src = re.sub(r'<meta property="og:url" content="[^"]*" />',
                 lambda _: f'<meta property="og:url" content="{canonical}" />',
                 src, count=1)
    block = f'<link rel="canonical" href="{canonical}" />\n' + hreflang_trio(rel)
    if desc:
        block += f'\n<meta name="description" content="{desc}">'
    src = re.sub(r'<meta name="description"[^>]*>\n?', "", src, count=1)
    return re.sub(r'<link rel="canonical" href="[^"]*" />', lambda _: block,
                  src, count=1)


def add_alt_link(src: str, rel: str, lang: str) -> str:
    """<body> 結尾放一個指向另一個語言的靜態連結——不跑 JavaScript 也走得過去。"""
    other = "en" if lang == "zh" else "zh"
    href = path_of(twin_of(rel)) if lang == "zh" else path_of(rel)
    block = (f'<p class="lang-alt-link" style="text-align:center;padding:12px;">'
             f'<a href="{href}" hreflang="{LANG_CODE[other]}" rel="alternate"'
             f' lang="{LANG_CODE[other]}">{ALT_LABEL[other]}</a></p>\n')
    return src.replace("</body>", block + "</body>", 1)


def esc(t: str) -> str:
    """與 index.html 內 JS 的 esc() 完全一致的跳脫規則。"""
    return (t or "").replace("&", "&amp;").replace("<", "&lt;") \
                    .replace(">", "&gt;").replace('"', "&quot;")


def static_chips(items, lang):
    """產生與前端 chips() 相同的 HTML，供爬蟲第一波抓取。"""
    used = [(k, v) for k, v in THEMES.items() if any(i["theme"] == k for i in items)]
    out = [f'<button class="chip on" onclick="pick(null)">'
           f'{"全部" if lang == "zh" else "All"}</button>']
    for k, (zh, en, ci) in used:
        out.append(
            f'<button class="chip" onclick="pick(\'{k}\')">\n'
            f'      <span class="dot" style="background:var(--c{ci})"></span>'
            f'{esc(zh if lang == "zh" else en)}</button>')
    return "".join(out)


def static_items(items, lang):
    """產生與前端 list() 相同的 HTML，供爬蟲第一波抓取。"""
    zh = lang == "zh"
    out = []
    for d in items:
        text = d["sumZh"] if zh else d["sumEn"]
        summary = f'<p>{esc(text)}</p>' if text else ''
        out.append(
            f'<a class="item" href="{d["file"]}" style="--bar:var(--c{d["ci"]})">\n'
            f'      <div class="meta">\n'
            f'        <span class="d">{d["date"]} · '
            f'{"星期" + d["wdZh"] if zh else d["wdEn"]}</span>\n'
            f'        <span class="th">{esc(d["themeZh"] if zh else d["themeEn"])}</span>\n'
            f'      </div>\n'
            f'      <h3>{esc(d["titleZh"] if zh else d["titleEn"])}</h3>\n'
            f'      {summary}\n'
            f'    </a>')
    return "".join(out)


def raw_meta(src, name):
    """直接取出 meta 的原字串（已經是跳脫過的），不做解碼再編碼的來回。"""
    m = re.search(r'<meta name="' + name + r'" content="([^"]*)"', src)
    return m.group(1) if m else ""


def is_bilingual(src):
    return '<span class="en">' in src or '<span class="en-inline">' in src


def transform_report(src, rel, lang, date_str, desc):
    """把一份中英並排的日報，變成只有一種語言的那一份。"""
    if OLD_LANG_CSS in src:
        src = src.replace(OLD_LANG_CSS, NEW_LANG_CSS, 1)
        if OLD_SEG_CSS not in src:
            raise SystemExit(f"! {rel} 頁內的 .seg 樣式不是預期的樣子")
        src = src.replace(OLD_SEG_CSS, NEW_SEG_CSS, 1)
    elif "/assets/report.css" not in src:
        raise SystemExit(f"! {rel} 找不到語言切換的 CSS，也沒有引用共用樣式表")
    if SEG_BUTTONS not in src:
        raise SystemExit(f"! {rel} 的語言切換鈕不是預期的樣子，無法改成連結")
    src = keep_only(src, lang)
    src = src.replace('<body class="lang-zh">', "<body>", 1)
    src = src.replace(SEG_BUTTONS, lang_switch(rel, lang), 1)
    src = SETLANG.sub("", src, count=1)
    src = set_head(src, rel, lang, TITLE["report"][lang].format(d=date_str), desc)
    src = add_alt_link(src, rel, lang)
    if lang == "en":
        for old, new in EN_ATTRS:
            src = src.replace(old, new)
    return src


def split_reports(items):
    """把還是中英並排的日報就地拆成兩份；已經拆過的一個字都不動。"""
    done = []
    for d in items:
        rel, date_str = d["file"], d["date"]
        src_path = os.path.join(ROOT, rel)
        twin_path = os.path.join(ROOT, twin_of(rel))
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
        if not is_bilingual(src):
            if not os.path.exists(twin_path):
                print(f"  ! {rel} 已經沒有英文節點，卻也找不到 {twin_of(rel)}")
            continue
        pages = {lang: transform_report(src, rel, lang, date_str,
                                        raw_meta(src, f"report-summary-{lang}"))
                 for lang in ("zh", "en")}
        os.makedirs(os.path.dirname(twin_path), exist_ok=True)
        for path, text in ((src_path, pages["zh"]), (twin_path, pages["en"])):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        done.append(rel)
    return done


def write_sitemap(items):
    """sitemap 由 reports/ 掃描結果產生，不會漏掉任何一天，兩種語言都列。
       刻意不寫 <lastmod>：沒有可信的內容修改時間來源，給錯的比不給更糟。"""
    pages = ["index.html"] + [d["file"] for d in items]
    urls = [url_of(p) for p in pages] + [url_of(twin_of(p)) for p in pages]
    body = "\n".join(f"  <url>\n    <loc>{u}</loc>\n  </url>" for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<!--\n'
           '  本站自己的 sitemap，由 build_index.py 自動產生，請勿手動編輯。\n'
           '  刻意不寫 <lastmod>：沒有可信的「內容最後修改時間」來源\n'
           '  (git commit 時間不等於內容變動時間)，給錯的 lastmod 比不給更糟。\n'
           '-->\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + body + '\n</urlset>\n')
    with open(SITEMAP, "w", encoding="utf-8") as f:
        f.write(xml)
    return len(urls)


def render(items, lang):
    data = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    themes = json.dumps(
        [{"key": k, "zh": v[0], "en": v[1], "ci": v[2]} for k, v in THEMES.items()],
        ensure_ascii=False, separators=(",", ":"))
    total = len(items)
    latest = items[0]["date"] if items else "—"

    src = TEMPLATE.replace("__DATA__", data) \
                  .replace("__THEMES__", themes) \
                  .replace("__TOTAL__", str(total)) \
                  .replace("__LATEST__", latest) \
                  .replace("__CHIPS__", static_chips(items, lang)) \
                  .replace("__ITEMS__", static_items(items, lang)) \
                  .replace("__LANGSWITCH__", lang_switch("index.html", lang))
    src = keep_only(src, lang)
    src = set_head(src, "index.html", lang, TITLE["index"][lang], INDEX_DESC[lang])
    src = add_alt_link(src, "index.html", lang)
    if lang == "en":
        for old, new in EN_ATTRS:
            src = src.replace(old, new)
    return src


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<title>AI／醫療AI 每日新知日報</title>
<meta property="og:url" content="https://ai-medical-daily.peteraim.com/" />
<link rel="canonical" href="https://ai-medical-daily.peteraim.com/" />
<meta name="description" content="每日自動整理的 AI 與醫療 AI 新知、產業動向、法規與產品分析。">
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-HJLDQZDK5V"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-HJLDQZDK5V');
</script>
<style>
:root{
  --bg:#f7f8fa;--surface:#fff;--surface-2:#f0f2f5;--border:#e2e5ea;
  --text:#16181d;--muted:#5c636e;--faint:#8a919c;
  --accent:#0d7a6f;--accent-soft:#e3f2f0;--accent-text:#0a5c54;
  --shadow:0 1px 2px rgba(16,24,40,.04),0 4px 16px rgba(16,24,40,.05);
  --c0:#0d7a6f;--c1:#1d5fa8;--c2:#a8562a;--c3:#6b4ba8;
  --c4:#a83e6b;--c5:#2a7a3e;--c6:#8a6d1f;--c7:#5c636e;
}
body.dark{
  --bg:#0e1014;--surface:#171a20;--surface-2:#1e222a;--border:#2a2f39;
  --text:#e8eaee;--muted:#a2a9b5;--faint:#6f7783;
  --accent:#3fbfae;--accent-soft:#12332f;--accent-text:#6fd6c6;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 4px 20px rgba(0,0,0,.3);
  --c0:#3fbfae;--c1:#63a8f0;--c2:#e0975c;--c3:#b192ee;
  --c4:#ef8ab4;--c5:#63c47c;--c6:#d4b74e;--c7:#a2a9b5;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC","PingFang TC","Helvetica Neue",Arial,sans-serif;
  font-size:16px;line-height:1.7;-webkit-font-smoothing:antialiased;transition:background .25s,color .25s}
.lang-alt-link{margin:0}
.lang-alt-link a{color:var(--accent);text-decoration:none;font-weight:600}

header.bar{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--surface) 88%,transparent);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
.bar-in{max-width:1000px;margin:0 auto;padding:10px 20px;display:flex;align-items:center;gap:10px}
.brand{font-weight:700;font-size:14px;white-space:nowrap}
.brand i{color:var(--accent);font-style:normal}
.sp{flex:1}
.btn{border:1px solid var(--border);background:var(--surface-2);color:var(--text);border-radius:999px;
  padding:5px 12px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s;white-space:nowrap}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.seg{display:flex;border:1px solid var(--border);border-radius:999px;overflow:hidden;background:var(--surface-2)}
.seg a{border:0;background:transparent;color:var(--muted);font-family:inherit;padding:5px 12px;
  font-size:13px;font-weight:600;cursor:pointer;transition:.15s;
  display:flex;align-items:center;justify-content:center;text-decoration:none;line-height:normal}
.seg a.on{background:var(--accent);color:#fff}

main{max-width:1000px;margin:0 auto;padding:0 20px 90px}
.hero{padding:46px 0 30px;border-bottom:1px solid var(--border)}
.kicker{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:12px}
h1{font-size:clamp(28px,5vw,42px);line-height:1.2;margin:0 0 12px;letter-spacing:-.02em;font-weight:750}
.tagline{font-size:16px;color:var(--muted);margin:0 0 20px;max-width:60ch}
.stats{display:flex;gap:26px;flex-wrap:wrap}
.stat b{display:block;font-size:24px;font-weight:750;letter-spacing:-.01em;line-height:1.2}
.stat span{font-size:12px;color:var(--faint);font-weight:600;letter-spacing:.06em;text-transform:uppercase}

.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:26px 0 18px}
#q{flex:1;min-width:200px;border:1px solid var(--border);background:var(--surface);color:var(--text);
  border-radius:10px;padding:10px 14px;font-size:15px;font-family:inherit}
#q:focus{outline:2px solid var(--accent);outline-offset:-1px;border-color:transparent}
.views{display:flex;border:1px solid var(--border);border-radius:10px;overflow:hidden;background:var(--surface-2)}
.views button{border:0;background:transparent;color:var(--muted);font-family:inherit;padding:9px 15px;
  font-size:13.5px;font-weight:600;cursor:pointer}
.views button.on{background:var(--accent);color:#fff}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:24px}
.chip{font-size:12.5px;font-weight:650;border:1px solid var(--border);background:var(--surface);
  color:var(--muted);border-radius:999px;padding:5px 12px;cursor:pointer;transition:.15s;font-family:inherit}
.chip:hover{border-color:var(--accent)}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
.chip .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:6px;vertical-align:1px}
.chip.on .dot{background:#fff!important}

a.item{display:block;text-decoration:none;color:inherit;background:var(--surface);border:1px solid var(--border);
  border-radius:14px;padding:18px 20px;margin-bottom:12px;box-shadow:var(--shadow);transition:.15s;position:relative;overflow:hidden}
a.item::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--bar,var(--accent))}
a.item:hover{transform:translateY(-1px);border-color:var(--accent)}
.meta{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:9px}
.d{font-size:13px;font-weight:700;color:var(--faint);font-variant-numeric:tabular-nums}
.th{font-size:11px;font-weight:750;letter-spacing:.05em;text-transform:uppercase;padding:3px 9px;border-radius:5px;
  background:var(--surface-2);color:var(--bar,var(--accent))}
a.item h3{margin:0 0 6px;font-size:17.5px;line-height:1.45;font-weight:700;letter-spacing:-.01em}
a.item p{margin:0;font-size:14.5px;color:var(--muted);line-height:1.65}

.cal{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px 22px;
  margin-bottom:14px;box-shadow:var(--shadow)}
.cal h4{margin:0 0 14px;font-size:15px;font-weight:700;letter-spacing:.01em}
.cg{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}
.cg .hd{font-size:11px;font-weight:750;color:var(--faint);text-align:center;padding-bottom:5px;letter-spacing:.05em}
.cg a,.cg span{height:42px;display:flex;align-items:center;justify-content:center;border-radius:8px;
  font-size:13px;font-weight:650;text-decoration:none;font-variant-numeric:tabular-nums}
.cg span{color:var(--faint);opacity:.4}
.cg a{background:var(--bar,var(--accent));color:#fff;transition:.15s}
.cg a:hover{transform:scale(1.09)}
.empty{text-align:center;padding:56px 20px;color:var(--faint);font-size:15px}
/* --- GitHub 星星徽章 + 頁尾社群連結 --- */
.gh-star{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--border);
  background:var(--surface-2);color:var(--muted);border-radius:999px;padding:5px 10px;
  font-size:13px;font-weight:700;text-decoration:none;font-variant-numeric:tabular-nums;
  transition:.15s;white-space:nowrap}
.gh-star:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
.gh-star svg{width:15px;height:15px;fill:currentColor;flex:none;display:block}
.gh-star .st{color:#e3a008}
.gh-star b{font-weight:700;min-width:1ch;font-size:12.5px}
.foot-row{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}
.foot-row>div:first-child{flex:1 1 320px;min-width:0}
.social{display:flex;gap:9px;align-items:center;flex:none}
.social a{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;
  border:1px solid var(--border);background:var(--surface-2);color:var(--muted);
  border-radius:999px;transition:.15s;text-decoration:none}
.social a:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-soft);
  transform:translateY(-1px)}
.social svg{width:16px;height:16px;fill:currentColor;display:block}
@media(max-width:430px){.gh-star b{display:none}.gh-star{padding:5px 9px;gap:4px}}
a.brand{color:inherit;text-decoration:none;transition:.15s;cursor:pointer}
a.brand:hover{opacity:.72}
a.brand:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:5px}
footer{margin-top:52px;padding-top:22px;border-top:1px solid var(--border);font-size:13px;color:var(--faint);line-height:1.8}
footer a{color:var(--accent);text-decoration:none}
@media(max-width:640px){
  main{padding:0 15px 80px}
  .cal{padding:15px}
  .cg a,.cg span{font-size:12px;border-radius:6px}
  .bar-in{padding:9px 14px;gap:8px}
}
</style>
</head>
<body>

<header class="bar">
  <div class="bar-in">
    <a class="brand" href="index.html" title="回到日報首頁" aria-label="回到日報首頁 / Back to all reports"><i>◆</i> <span class="zh">AI／醫療AI 日報</span><span class="en">AI &amp; Medical AI Daily</span></a>
    <div class="sp"></div>
    <a class="gh-star" href="https://github.com/tingwei161803/ai-medical-daily" target="_blank" rel="noopener" title="Star on GitHub" aria-label="Star this project on GitHub / 在 GitHub 給這個專案一顆星"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg><svg class="st" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg><b id="ghs">–</b></a>
__LANGSWITCH__
    <button class="btn" onclick="toggleTheme()"><span id="ti">◐</span></button>
  </div>
</header>

<main>
  <div class="hero">
    <div class="kicker"><span class="zh">每日自動更新</span><span class="en">Updated daily</span></div>
    <h1><span class="zh">AI／醫療AI 每日新知日報</span><span class="en">AI &amp; Medical AI Daily</span></h1>
    <p class="tagline">
      <span class="zh">每天台北時間早上 8:00 自動產出：AI 與醫療 AI 的重點新聞、產品分析、公司動向與競爭關係，附延伸閱讀與參考文獻。每天輪值不同主題。</span>
      <span class="en">Generated automatically at 08:00 Taipei time: the day's news in AI and medical AI, with product analysis, company moves, competitive read, further reading and full references. Each weekday rotates through a different theme.</span>
    </p>
    <div class="stats">
      <div class="stat"><b>__TOTAL__</b><span class="zh">份日報</span><span class="en">Reports</span></div>
      <div class="stat"><b>__LATEST__</b><span class="zh">最新一期</span><span class="en">Latest</span></div>
    </div>
  </div>

  <div class="controls">
    <input id="q" type="search" placeholder="搜尋標題、摘要或日期…" oninput="render()">
    <div class="views">
      <button id="vl" class="on" onclick="setView('list')"><span class="zh">列表</span><span class="en">List</span></button>
      <button id="vc" onclick="setView('cal')"><span class="zh">月曆</span><span class="en">Calendar</span></button>
    </div>
  </div>

  <div class="chips" id="chips">__CHIPS__</div>
  <div id="out">__ITEMS__</div>

  <footer>
  <div class="foot-row">
    <div>
      <span class="zh">由 Claude 自動產出並推送至此 repo。內容經來源查證，但不構成投資或醫療建議。</span>
    <span class="en">Generated and pushed automatically by Claude. Sourced and checked, but not investment or medical advice.</span>
    </div>
    <div class="social"><a href="https://www.peteraim.com" target="_blank" rel="noopener" title="peteraim.com" aria-label="Back to peteraim.com / 返回 peteraim.com"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 12h3v8h6v-6h2v6h6v-8h3z"/></svg></a><a href="https://www.linkedin.com/in/ai-med/" target="_blank" rel="noopener" title="LinkedIn" aria-label="LinkedIn (opens in new tab)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.94v5.67H9.36V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z"/></svg></a></div>
  </div>
</footer>
</main>

<script>
const DATA = __DATA__;
const THEMES = __THEMES__;
let view = 'list', active = null;

const cvar = i => `var(--c${i})`;
const esc = s => (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
/* 語言由網址決定（中文在 /、英文在 /en/），不是由頁面上的狀態決定。
   兩個版本是兩個檔案，切換是真的連結，所以這裡只要讀 <html lang> 就好。 */
const isZh = () => (document.documentElement.lang || '').toLowerCase().startsWith('zh');

function toggleTheme(){
  document.body.classList.toggle('dark');
  ti.textContent = document.body.classList.contains('dark') ? '◑' : '◐';
  render();
}
function setView(v){
  view = v;
  vl.classList.toggle('on', v==='list');
  vc.classList.toggle('on', v==='cal');
  render();
}
function chips(){
  const used = THEMES.filter(t => DATA.some(d => d.theme === t.key));
  const all = isZh() ? '全部' : 'All';
  document.getElementById('chips').innerHTML =
    `<button class="chip${active===null?' on':''}" onclick="pick(null)">${all}</button>` +
    used.map(t => `<button class="chip${active===t.key?' on':''}" onclick="pick('${t.key}')">
      <span class="dot" style="background:${cvar(t.ci)}"></span>${esc(isZh()?t.zh:t.en)}</button>`).join('');
}
function pick(k){ active = k; chips(); render(); }

function filtered(){
  const s = q.value.trim().toLowerCase();
  return DATA.filter(d => {
    if (active && d.theme !== active) return false;
    if (!s) return true;
    return [d.date, d.titleZh, d.titleEn, d.sumZh, d.sumEn, d.themeZh, d.themeEn]
      .join(' ').toLowerCase().includes(s);
  });
}

function render(){
  const items = filtered(), zh = isZh(), out = document.getElementById('out');
  if (!items.length){
    out.innerHTML = `<div class="empty">${zh?'沒有符合的日報。':'No reports match.'}</div>`;
    return;
  }
  out.innerHTML = view === 'list' ? list(items) : cal(items);
}

function list(items){
  return items.map(d => {
    const zh = isZh();
    return `<a class="item" href="${d.file}" style="--bar:${cvar(d.ci)}">
      <div class="meta">
        <span class="d">${d.date} · ${zh ? '星期'+d.wdZh : d.wdEn}</span>
        <span class="th">${esc(zh ? d.themeZh : d.themeEn)}</span>
      </div>
      <h3>${esc(zh ? d.titleZh : d.titleEn)}</h3>
      ${(zh?d.sumZh:d.sumEn) ? `<p>${esc(zh ? d.sumZh : d.sumEn)}</p>` : ''}
    </a>`;
  }).join('');
}

function cal(items){
  const zh = isZh();
  const byMonth = {};
  items.forEach(d => { (byMonth[d.date.slice(0,7)] ||= []).push(d); });
  const hdZh = ['一','二','三','四','五','六','日'], hdEn = ['M','T','W','T','F','S','S'];
  const mZh = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
  const mEn = ['January','February','March','April','May','June','July','August','September','October','November','December'];

  return Object.keys(byMonth).sort().reverse().map(ym => {
    const [y, m] = ym.split('-').map(Number);
    const map = {};
    byMonth[ym].forEach(d => { map[Number(d.date.slice(8,10))] = d; });
    const first = (new Date(y, m-1, 1).getDay() + 6) % 7;   // 週一為第一欄
    const days = new Date(y, m, 0).getDate();
    let cells = (zh?hdZh:hdEn).map(h => `<div class="hd">${h}</div>`).join('');
    for (let i=0;i<first;i++) cells += '<span></span>';
    for (let n=1;n<=days;n++){
      const d = map[n];
      cells += d
        ? `<a href="${d.file}" style="--bar:${cvar(d.ci)}" title="${esc(zh?d.titleZh:d.titleEn)}">${n}</a>`
        : `<span>${n}</span>`;
    }
    return `<div class="cal"><h4>${zh ? y+' 年 '+mZh[m-1] : mEn[m-1]+' '+y}</h4>
      <div class="cg">${cells}</div></div>`;
  }).join('');
}

if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches){
  document.body.classList.add('dark');
  document.getElementById('ti').textContent = '◑';
}
chips(); render();

/* GitHub 星星數：無需授權，失敗或被限流時靜默保留佔位符 */
(function(){
  var el = document.getElementById('ghs');
  if (!el || typeof fetch !== 'function') return;
  fetch('https://api.github.com/repos/tingwei161803/ai-medical-daily', {headers:{Accept:'application/vnd.github+json'}})
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(d){
      if (!d || typeof d.stargazers_count !== 'number') return;
      var n = d.stargazers_count;
      el.textContent = n >= 1000 ? (Math.round(n/100)/10) + 'k' : String(n);
    })
    .catch(function(){});
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    items = collect()

    split = split_reports(items)
    if split:
        print(f"✓ 已拆成中英文兩個網址：{len(split)} 份日報 → {', '.join(split)}")

    for lang, out in (("zh", OUT), ("en", os.path.join(ROOT, TWIN_DIR, "index.html"))):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(render(items, lang))
    n_urls = write_sitemap(items)
    print(f"✓ index.html + {TWIN_DIR}/index.html 已重建：{len(items)} 份日報"
          + (f"（最新 {items[0]['date']}）" if items else "（目前沒有日報）"))
    print(f"✓ sitemap.xml 已重建：{n_urls} 個網址")
    sys.exit(0)
