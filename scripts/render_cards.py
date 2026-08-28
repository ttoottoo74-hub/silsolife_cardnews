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

# 실소 브랜드 팔레트 (블로그 CSS에서 가져옴)
CSS = """
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
  --warm:#F4ECE7;
  --warm-ink:#8A5A2B;
}
body{
  background:#555;
  font-family:"Noto Sans CJK KR","Noto Sans KR",sans-serif;
  -webkit-font-smoothing:antialiased;
  display:flex; flex-direction:column; align-items:center; gap:28px; padding:28px;
}
.card{
  width:1080px; height:1350px; position:relative; overflow:hidden;
  display:flex; flex-direction:column;
  padding:86px 86px 74px;
  background:var(--ivory); color:var(--charcoal);
  letter-spacing:-.035em;
  /* 한국어는 어절 단위로 끊어야 읽힌다. 이 한 줄이 없으면 '돈이'가 '돈/이'로 쪼개진다. */
  word-break:keep-all; overflow-wrap:break-word;
}

/* 상단 브랜드 바 */
.brandbar{ display:flex; align-items:center; justify-content:space-between; }
.mark{ display:flex; align-items:baseline; gap:12px; }
.mark .name{ font-size:36px; font-weight:900; color:var(--green); letter-spacing:-.05em }
.mark .sub{ font-size:25px; font-weight:500; color:var(--muted); letter-spacing:-.02em }
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
.cover .hook{
  font-size:116px; font-weight:900; line-height:1.24; letter-spacing:-.055em;
  color:var(--green-dark); text-wrap:balance;
}
.cover .rule{ width:132px; height:9px; background:var(--green); margin:52px 0 40px; border-radius:5px }
.cover .title{ font-size:44px; font-weight:500; line-height:1.6; color:var(--text); max-width:830px }

/* ---------- 02 한 줄 답 ---------- */
.answer{ background:var(--green); color:#FFFFFF }
.answer .mark .name{ color:#FFFFFF }
.answer .mark .sub{ color:#B9CFC3 }
.answer .pill{ background:rgba(255,255,255,.14); color:#FFFFFF; border-color:rgba(255,255,255,.3) }
.answer .label{ font-size:29px; font-weight:800; letter-spacing:.16em; color:#A9C8B8; margin-bottom:34px }
.answer .text{ font-size:74px; font-weight:800; line-height:1.42; letter-spacing:-.05em; text-wrap:balance }
.answer .foot{ border-top-color:rgba(255,255,255,.25) }
.answer .foot .site{ color:#B9CFC3 }
.answer .foot .swipe{ color:#FFFFFF }

/* ---------- 본문 ---------- */
.body-card{ background:var(--paper) }
.body-card .heading{
  font-size:60px; font-weight:800; line-height:1.34; letter-spacing:-.05em;
  color:var(--green-dark); margin-bottom:40px; text-wrap:balance;
}
.anchor{
  font-size:190px; font-weight:900; line-height:1; letter-spacing:-.07em;
  color:var(--green); margin-bottom:44px;
}
.body-card .text{ font-size:48px; font-weight:400; line-height:1.72; color:var(--text) }
.body-card .text .em{
  font-weight:800; color:var(--green-dark);
  background:linear-gradient(transparent 62%, var(--green-soft) 62%);
  padding:0 3px;
}
/* 큰 숫자를 이미 보여준 카드에서는 본문 형광을 빼서 중복감을 줄인다 */
.body-card.has-anchor .text .em{ background:none; padding:0 }
/* 앵커가 없는 카드는 그만큼 타이포를 키워 여백을 메운다 */
.body-card:not(.has-anchor) .heading{ font-size:70px; margin-bottom:44px }
.body-card:not(.has-anchor) .text{ font-size:55px; line-height:1.66; font-weight:500 }
/* 본문은 살짝 위쪽으로 — 카드뉴스는 상단 무게가 안정적이다 */
.body-card .spacer:nth-of-type(1){ flex:.72 }

/* ---------- 도식 ---------- */
.viz{ background:var(--ivory) }
.viz .label{ font-size:29px; font-weight:800; letter-spacing:.16em; color:var(--green); margin-bottom:26px }
.viz .vtitle{ font-size:64px; font-weight:800; line-height:1.3; letter-spacing:-.05em;
              color:var(--green-dark); margin-bottom:56px; text-wrap:balance }
.viz svg{ display:block; overflow:visible }
.viz .vnote{ margin-top:56px; font-size:36px; font-weight:500; line-height:1.6; color:var(--text) }

/* ---------- 주의 ---------- */
.caution{ background:var(--warm) }
.caution .label{
  display:inline-block; padding:11px 26px; border-radius:999px; margin-bottom:40px;
  font-size:29px; font-weight:800; letter-spacing:-.02em;
  background:var(--warm-ink); color:#FFF7F0;
}
.caution .text{ font-size:54px; font-weight:600; line-height:1.56; letter-spacing:-.045em; color:#3A2E24 }

/* ---------- 출처 ---------- */
.source .label{ font-size:29px; font-weight:800; letter-spacing:.16em; color:var(--green); margin-bottom:44px }
.src{ padding:32px 0; border-bottom:1px solid var(--border);
       display:flex; align-items:center; gap:28px }
.srcmark{
  flex:0 0 auto; width:88px; height:88px; border-radius:12px;
  background:var(--green-soft); border:2px solid var(--green);
  display:flex; align-items:center; justify-content:center;
  font-size:34px; font-weight:900; color:var(--green); letter-spacing:-.05em;
}
.srcbody{ flex:1; min-width:0 }
.srctype{ font-size:24px; font-weight:700; color:var(--green); letter-spacing:.06em; margin-bottom:4px }
.src:first-of-type{ border-top:1px solid var(--border) }
.src .nm{ font-size:50px; font-weight:700; letter-spacing:-.04em; color:var(--charcoal) }
.src .dm{ font-size:29px; font-weight:500; color:var(--muted); margin-top:10px; letter-spacing:0 }
.source .verified{ margin-top:44px; font-size:34px; font-weight:600; color:var(--text) }
.source .cta{
  margin-top:52px; padding:36px 40px; border-radius:14px; background:var(--green);
  color:#FFFFFF; font-size:41px; font-weight:700; line-height:1.5; letter-spacing:-.04em;
}
.source .cta b{ font-weight:900 }
"""


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
        f'{brandbar(f"""<span class="pill">{nb(escape(d["topic_label"]))}</span>""")}'
        f'<div class="spacer"></div>'
        f'<div class="hook">{nb(escape(d["hook"]))}</div>'
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
    palette = {
        "accent": "#2F5B4B", "accent_soft": "#CBDBD1", "line": "#C8D2CC",
        "ink": "#1E211F", "muted": "#727A75", "paper": "#F7F3EA",
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
        anchor = f'<div class="anchor">{nb(escape(hl))}</div>' if is_numeric(hl) else ""
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
    os.makedirs(outdir, exist_ok=True)
    d = json.load(open(src, encoding="utf-8"))

    cards = build_cards(d)
    html = f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>" + "".join(cards)

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
