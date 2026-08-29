#!/usr/bin/env python3
"""
실소 카드뉴스 렌더러 (파이프라인 4단계)

카드 JSON → HTML 템플릿 → Playwright 캡처 → 1080×1350 PNG

사용법:
    python3 render_cards.py card.clean.json out/
"""

import json
import os
import re
import sys
from html import escape

import visuals

REGISTRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_registry.json")
try:
    with open(REGISTRY_PATH, encoding="utf-8") as _f:
        _reg = json.load(_f)
    INSTITUTIONS = _reg["institutions"]
    TYPE_LABEL = _reg["type_label"]
except (OSError, KeyError, json.JSONDecodeError):
    INSTITUTIONS, TYPE_LABEL = {}, {}


def lookup(url):
    """URL의 도메인으로 기관을 찾는다. 서브도메인은 상위 도메인까지 거슬러 본다."""
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    host = host[4:] if host.startswith("www.") else host
    parts = host.split(".")
    for i in range(len(parts) - 1):
        cand = ".".join(parts[i:])
        if cand in INSTITUTIONS:
            return INSTITUTIONS[cand]
    return None

W, H = 1080, 1350

# 표제용 서체를 바꿔 끼울 수 있게 한다. 이전 카드 중 반응이 좋았던 것은 명조 계열이었다.
FONT_TEXT = '"Noto Sans CJK KR","Noto Sans KR",sans-serif'
FONTS = {
    "sans":  '"Noto Sans CJK KR","Noto Sans KR",sans-serif',
    "serif": '"Noto Serif CJK KR","Noto Serif KR",serif',
}

# 실소 브랜드 팔레트 (블로그 CSS에서 가져옴)
CSS_TMPL = """
@page { margin: 0 }
* { margin:0; padding:0; box-sizing:border-box }
:root{
  --ivory:#F7F3EA;
  --paper:#FFFFFF;
  --charcoal:#1E211F;
  --text:#3E423F;
  --muted:#727A75;
  --green:#2F5B4B;
  --green-dark:#25493C;
  --green-soft:#E8EEE9;
  --border:#C8D2CC;
  --warm:#FBF1DC;
  --warm-ink:#8A6118;
}
body{
  background:#555;
  font-family:__TEXT__;
  -webkit-font-smoothing:antialiased;
  display:flex; flex-direction:column; align-items:center; gap:28px; padding:28px;
}
.card{
  width:1080px; height:1350px; position:relative; overflow:hidden;
  display:flex; flex-direction:column;
  padding:80px 78px 72px;
  background:var(--ivory); color:var(--charcoal);
  letter-spacing:-.035em;
  /* 한국어는 어절 단위로 끊어야 읽힌다. 이 한 줄이 없으면 '돈이'가 '돈/이'로 쪼개진다. */
  word-break:keep-all; overflow-wrap:break-word;
}
/* 크게 쓰는 글자는 표제용 서체로 (고딕/명조 전환) */
.hook, .toplabel, .answer .text, .heading, .anchor, .callout .val, .vtitle, .caution .text{
  font-family:__DISPLAY__;
}

/* 상단 브랜드 바 */
.brandbar{ display:flex; align-items:center; justify-content:space-between; }
.mark{ display:flex; align-items:baseline; gap:12px; }
.mark .name{ font-size:38px; font-weight:900; color:var(--green); letter-spacing:-.05em }
.mark .sub{ font-size:26px; font-weight:500; color:var(--muted); letter-spacing:-.02em }
.pill{
  padding:13px 28px; border-radius:999px; font-size:27px; font-weight:700;
  background:var(--green-soft); color:var(--green); border:1px solid var(--border);
  letter-spacing:-.02em;
}
.idx{ font-size:27px; font-weight:700; color:var(--muted); letter-spacing:.08em;
      font-variant-numeric:tabular-nums }

.spacer{ flex:1 }

/* 하단 */
.foot{ display:flex; align-items:center; justify-content:space-between;
       padding-top:30px; border-top:1px solid var(--border); }
.foot .site{ font-size:27px; font-weight:600; color:var(--muted); letter-spacing:-.02em }
.foot .swipe{ font-size:27px; font-weight:700; color:var(--green) }

/* ---------- 01 표지 ---------- */
/* 이전 카드의 문법: 작은 라벨 → 큰 문구 → 그중 숫자만 더 크게 → 굵은 규칙선 → 설명 */
.cover .spacer:nth-of-type(1){ flex:.42 }
.cover .toplabel{
  font-size:78px; font-weight:900; line-height:1.22; letter-spacing:-.05em;
  color:var(--charcoal); margin-bottom:8px;
}
.cover .hook{
  font-size:132px; font-weight:900; line-height:1.18; letter-spacing:-.06em;
  color:var(--green-dark); text-wrap:balance;
}
.cover .hook .big{ font-size:1.34em; color:var(--green); letter-spacing:-.07em }
.cover .rule{ width:460px; height:14px; background:var(--green); margin:44px 0 36px; border-radius:7px }
.cover .title{ font-size:50px; font-weight:500; line-height:1.58; color:var(--text); max-width:880px }

/* ---------- 02 한 줄 답 ---------- */
.answer{ background:var(--green); color:#FFFFFF }
.answer .mark .name{ color:#FFFFFF }
.answer .mark .sub{ color:#B9CFC3 }
.answer .pill{ background:rgba(255,255,255,.14); color:#FFFFFF; border-color:rgba(255,255,255,.3) }
.answer .label{ font-size:30px; font-weight:800; letter-spacing:.16em; color:#A9C8B8; margin-bottom:34px }
.answer .text{ font-size:84px; font-weight:900; line-height:1.38; letter-spacing:-.055em; text-wrap:balance }
.answer .spacer:nth-of-type(1){ flex:.62 }
.answer .foot{ border-top-color:rgba(255,255,255,.25) }
.answer .foot .site{ color:#B9CFC3 }
.answer .foot .swipe{ color:#FFFFFF }

/* ---------- 본문 ---------- */
.body-card{ background:var(--paper) }
.body-card .spacer:nth-of-type(1){ flex:.34 }
.body-card .heading{
  font-size:78px; font-weight:900; line-height:1.28; letter-spacing:-.055em;
  color:var(--charcoal); margin-bottom:36px; text-wrap:balance;
}
/* 핵심 숫자는 연녹색 상자에 담아 한 번에 읽히게 한다 (이전 카드의 방식) */
.callout{
  background:var(--green-soft); border-radius:24px; padding:36px 44px 40px;
  margin:4px 0 40px;
}
.callout .val{
  font-size:118px; font-weight:900; line-height:1.06; letter-spacing:-.07em; color:var(--green);
}
.anchor{
  font-size:190px; font-weight:900; line-height:1; letter-spacing:-.07em;
  color:var(--green); margin-bottom:44px;
}
.body-card .text{ font-size:52px; font-weight:500; line-height:1.66; color:var(--text) }
.body-card .text .em{
  font-weight:800; color:var(--green-dark);
  background:linear-gradient(transparent 62%, var(--green-soft) 62%);
  padding:0 3px;
}
/* 큰 숫자를 이미 보여준 카드에서는 본문 형광을 빼서 중복감을 줄인다 */
.body-card.has-anchor .text .em{ background:none; padding:0; font-weight:700 }
/* 앵커가 없는 카드는 그만큼 타이포를 키워 여백을 메운다 */
.body-card:not(.has-anchor) .spacer:nth-of-type(1){ flex:.85 }
.body-card:not(.has-anchor) .heading{ font-size:92px; margin-bottom:44px }
.body-card:not(.has-anchor) .text{ font-size:62px; line-height:1.6; font-weight:500 }

/* ---------- 도식 ---------- */
.viz{ background:var(--ivory) }
.viz .spacer:nth-of-type(1){ flex:.9 }
.viz .label{ font-size:30px; font-weight:800; letter-spacing:.16em; color:var(--green); margin-bottom:26px }
.viz .vtitle{ font-size:72px; font-weight:900; line-height:1.26; letter-spacing:-.055em;
              color:var(--charcoal); margin-bottom:56px; text-wrap:balance }
.viz svg{ display:block; overflow:visible }
.viz .vnote{ margin-top:56px; font-size:38px; font-weight:500; line-height:1.6; color:var(--text) }

/* ---------- 주의 ---------- */
.caution{ background:var(--warm) }
.caution .spacer:nth-of-type(1){ flex:.58 }
.caution .label{
  display:inline-block; padding:11px 26px; border-radius:999px; margin-bottom:40px;
  font-size:30px; font-weight:800; letter-spacing:-.02em;
  background:var(--warm-ink); color:#FFF7F0;
}
.caution .text{ font-size:64px; font-weight:800; line-height:1.5; letter-spacing:-.05em; color:#3C3016 }

/* ---------- 출처 ---------- */
.source .spacer:nth-of-type(1){ flex:.28 }
.source .label{ font-size:30px; font-weight:800; letter-spacing:.16em; color:var(--green); margin-bottom:40px }
.src{ padding:32px 0; border-bottom:1px solid var(--border);
       display:flex; align-items:center; gap:28px }
.srcmark{
  flex:0 0 auto; width:92px; height:92px; border-radius:12px;
  background:var(--green-soft); border:2px solid var(--green);
  display:flex; align-items:center; justify-content:center;
  font-size:36px; font-weight:900; color:var(--green); letter-spacing:-.05em;
}
.srcbody{ flex:1; min-width:0 }
.srctype{ font-size:25px; font-weight:700; color:var(--green); letter-spacing:.06em; margin-bottom:4px }
.src:first-of-type{ border-top:1px solid var(--border) }
.src .nm{ font-size:54px; font-weight:800; letter-spacing:-.045em; color:var(--charcoal) }
.src .dm{ font-size:29px; font-weight:500; color:var(--muted); margin-top:10px; letter-spacing:0 }
.source .verified{ margin-top:44px; font-size:35px; font-weight:600; color:var(--text) }
.source .cta{
  margin-top:48px; padding:38px 42px; border-radius:14px; background:var(--green);
  color:#FFFFFF; font-size:44px; font-weight:700; line-height:1.5; letter-spacing:-.04em;
}
.source .cta b{ font-weight:900 }
"""



# ---------------------------------------------------------------------------
# 카테고리별 색 테마
#
# 블로그는 하나의 톤을 유지하지만, 카드뉴스는 넘길 때마다 다른 글이라는 것이
# 한눈에 보이는 편이 낫다. 뼈대(여백·서체·배치)는 그대로 두고 색만 바꾼다.
# 그래야 다섯 갈래가 달라 보이면서도 같은 집 카드로 읽힌다.
# ---------------------------------------------------------------------------
THEMES = {
    3: {  # 돈·절약 — 숲 초록
        "accent": "#2F5B4B", "accent_dark": "#25493C", "soft": "#E5EDE7",
        "tint": "#F6F3EA", "border": "#C8D2CC", "on_accent_sub": "#A9C8B8",
    },
    4: {  # 정부·제도 — 감청
        "accent": "#2A4A73", "accent_dark": "#1F3A5C", "soft": "#E3EAF3",
        "tint": "#F3F5F9", "border": "#C6D0DE", "on_accent_sub": "#A9BFD8",
    },
    5: {  # 건강생활 — 청록
        "accent": "#1D6A66", "accent_dark": "#155450", "soft": "#DFEDEB",
        "tint": "#F1F7F6", "border": "#BFD5D2", "on_accent_sub": "#9FCCC7",
    },
    6: {  # 생활 — 테라코타
        "accent": "#9A5426", "accent_dark": "#7C411B", "soft": "#F4E7DC",
        "tint": "#FBF5EE", "border": "#DFCBB8", "on_accent_sub": "#E2BE9E",
    },
    7: {  # 가족·노후 — 플럼
        "accent": "#6E3B5A", "accent_dark": "#572C47", "soft": "#F0E4EB",
        "tint": "#FAF3F7", "border": "#D9C3CF", "on_accent_sub": "#D3A9C1",
    },
}
DEFAULT_THEME = THEMES[3]


def theme_of(d):
    return THEMES.get(d.get("category_id"), DEFAULT_THEME)


def themed_css(t, display_font):
    css = CSS_TMPL
    css = css.replace("__DISPLAY__", display_font).replace("__TEXT__", FONT_TEXT)
    css = css.replace("#2F5B4B", t["accent"]).replace("#25493C", t["accent_dark"])
    css = css.replace("#E8EEE9", t["soft"]).replace("#F7F3EA", t["tint"])
    css = css.replace("#C8D2CC", t["border"]).replace("#A9C8B8", t["on_accent_sub"])
    css = css.replace("#B9CFC3", t["on_accent_sub"])
    return css


NUM_RE = re.compile(
    r"(?:만\s*)?\d[\d,]*(?:\.\d+)?\s*(?:억|만|천)?\s*"
    r"(?:원|년|개월|일|세|%|배|회|건|월|주|시간|명|분|점|kg|km)?"
)


def hero(html):
    """문구 안의 첫 숫자 덩어리만 더 크게 키운다.
    이전 카드들이 '만 55세', '최대 5년'처럼 숫자를 표지의 주인공으로 쓰던 방식."""
    m = NUM_RE.search(html)
    if not m or not m.group().strip():
        return html
    a, b = m.span()
    return html[:a] + '<span class="big">' + m.group().strip() + "</span>" + html[b:]


def brandbar(right_html=""):
    return (
        '<div class="brandbar">'
        '<div class="mark"><span class="name">실소</span>'
        '<span class="sub">생활정보</span></div>'
        f"{right_html}</div>"
    )


def foot(swipe="넘기기 →"):
    return (
        '<div class="foot"><span class="site">silsolife.kr</span>'
        f'<span class="swipe">{swipe}</span></div>'
    )


WJ = "\u2060"  # word joiner — 이 문자 자리에서는 줄이 끊기지 않는다


def nb(text):
    """가운뎃점·물결·슬래시 앞뒤에서 줄이 끊기지 않게 막는다.
    '사고·진료'가 '사고 / ·진료'로 갈라지는 것을 방지."""
    for ch in ("·", "~", "/"):
        text = text.replace(ch, WJ + ch + WJ)
    return text


def emphasize(body, highlight):
    """body 안의 highlight를 인라인 강조로 감싼다."""
    safe = escape(body)
    if not highlight:
        return nb(safe)
    hl = escape(highlight)
    return nb(safe.replace(hl, f'\x00{hl}\x01', 1)).replace(
        "\x00", '<span class="em">').replace("\x01", "</span>")


def is_numeric(highlight):
    return bool(highlight and re.search(r"\d", highlight))


def build_cards(d):
    out = []

    # 01 표지
    out.append(
        f'<div class="card cover" id="card-1">'
        f'{brandbar(f"""<span class="pill">{nb(escape(d["category"]))}</span>""")}'
        f'<div class="spacer"></div>'
        f'<div class="toplabel">{nb(escape(d["topic_label"]))}</div>'
        f'<div class="hook">{hero(nb(escape(d["hook"])))}</div>'
        f'<div class="rule"></div>'
        f'<div class="title">{nb(escape(d["title"]))}</div>'
        f'<div class="spacer"></div>'
        f'{foot()}</div>'
    )

    # 02 한 줄 답
    out.append(
        f'<div class="card answer" id="card-2">'
        f'{brandbar(f"""<span class="pill">{nb(escape(d["category"]))}</span>""")}'
        f'<div class="spacer"></div>'
        f'<div class="label">핵심 결론</div>'
        f'<div class="text">{nb(escape(d["answer"]))}</div>'
        f'<div class="spacer"></div>'
        f'{foot()}</div>'
    )

    # 03 도식 (있을 때만)
    t = theme_of(d)
    palette = {
        "accent": t["accent"], "accent_soft": t["soft"], "line": t["border"],
        "ink": "#1E211F", "muted": "#727A75", "paper": t["tint"],
    }
    svg = visuals.build(d.get("visual"), palette)
    offset = 2
    if svg:
        v = d["visual"]
        note = v.get("note", "")
        out.append(
            f'<div class="card viz" id="card-3">'
            f'{brandbar()}'
            f'<div class="spacer"></div>'
            f'<div class="label">한눈에 보기</div>'
            f'<div class="vtitle">{nb(escape(v.get("title", "")))}</div>'
            f'{svg}'
            + (f'<div class="vnote">{nb(escape(note))}</div>' if note else "")
            + f'<div class="spacer"></div>'
            f'{foot()}</div>'
        )
        offset = 3

    # 본문
    total = len(d["cards"])
    for i, c in enumerate(d["cards"], 1):
        hl = c.get("highlight")
        # 숫자는 연녹색 상자에 담아 따로 세운다 — 본문에 묻히면 읽히지 않는다
        anchor = (
            f'<div class="callout"><div class="val">{nb(escape(hl))}</div></div>'
            if is_numeric(hl) else ""
        )
        cls = "body-card has-anchor" if anchor else "body-card"
        out.append(
            f'<div class="card {cls}" id="card-{i + offset}">'
            f'{brandbar(f"""<span class="idx">{i:02d} / {total:02d}</span>""")}'
            f'<div class="spacer"></div>'
            f'<div class="heading">{nb(escape(c["heading"]))}</div>'
            f'{anchor}'
            f'<div class="text">{emphasize(c["body"], hl)}</div>'
            f'<div class="spacer"></div>'
            f'{foot()}</div>'
        )

    n = total + offset + 1

    # 주의
    out.append(
        f'<div class="card caution" id="card-{n}">'
        f'{brandbar()}'
        f'<div class="spacer"></div>'
        f'<div><span class="label">이것만은 주의</span></div>'
        f'<div class="text">{nb(escape(d["caution"]))}</div>'
        f'<div class="spacer"></div>'
        f'{foot()}</div>'
    )

    # 출처
    srcs = ""
    for s in d["sources"]:
        domain = re.sub(r"^https?://", "", s["url"]).split("/")[0]
        inst = lookup(s["url"])
        abbr = inst["abbr"] if inst else s["name"][:2]
        tlabel = TYPE_LABEL.get(inst["type"], "") if inst else ""
        srcs += (
            f'<div class="src">'
            f'<div class="srcmark">{escape(abbr)}</div>'
            f'<div class="srcbody">'
            + (f'<div class="srctype">{escape(tlabel)}</div>' if tlabel else "")
            + f'<div class="nm">{nb(escape(s["name"]))}</div>'
            f'<div class="dm">{escape(domain)}</div>'
            f'</div></div>'
        )
    out.append(
        f'<div class="card source" id="card-{n + 1}">'
        f'{brandbar()}'
        f'<div class="spacer"></div>'
        f'<div class="label">출처</div>'
        f'{srcs}'
        f'<div class="verified">최근 확인 {escape(d["verified_on"].replace("-", "."))}</div>'
        f'<div class="cta">자세한 내용은 <b>프로필 링크</b>에서<br>확인하실 수 있습니다.</div>'
        f'<div class="spacer"></div>'
        f'{foot("저장해 두세요")}</div>'
    )

    return out


def main():
    if len(sys.argv) < 3:
        print("사용법: python3 render_cards.py card.json out/", file=sys.stderr)
        sys.exit(2)

    src, outdir = sys.argv[1], sys.argv[2]
    font = "serif" if "--serif" in sys.argv else "sans"
    if os.environ.get("CARD_FONT") in FONTS:
        font = os.environ["CARD_FONT"]
    os.makedirs(outdir, exist_ok=True)
    d = json.load(open(src, encoding="utf-8"))

    cards = build_cards(d)
    css = themed_css(theme_of(d), FONTS[font])
    html = f"<!doctype html><meta charset='utf-8'><style>{css}</style>" + "".join(cards)

    page_path = os.path.abspath(os.path.join(outdir, "_cards.html"))
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(html)

    from playwright.sync_api import sync_playwright

    paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W + 60, "height": H}, device_scale_factor=1)
        page.goto("file://" + page_path)
        page.wait_for_timeout(600)

        for i in range(1, len(cards) + 1):
            out = os.path.join(outdir, f"{d['slug']}_{i:02d}.png")
            page.locator(f"#card-{i}").screenshot(path=out)
            paths.append(out)
            print(f"  [{i:02d}/{len(cards)}] {os.path.basename(out)}", file=sys.stderr)

        browser.close()

    print(f"\n카드 {len(paths)}장 생성 완료 → {outdir}", file=sys.stderr)


if __name__ == "__main__":
    main()
