#!/usr/bin/env python3
"""
검수 페이지 생성 (파이프라인 5단계)

생성된 카드와 캡션을 한 화면에 모아 보여줍니다.
GitHub Pages로 공개되므로 휴대폰에서도 확인할 수 있습니다.

사용법:
    python3 build_preview.py docs/cards/<slug> docs/index.html
"""

import glob
import json
import os
import sys
from html import escape

TPL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>실소 카드뉴스 검수 · {slug}</title>
<style>
  :root {{
    --ivory:#F7F3EA; --paper:#fff; --ink:#1E211F; --body:#3E423F;
    --muted:#727A75; --green:#2F5B4B; --line:#D6DCD4;
  }}
  * {{ box-sizing:border-box }}
  body {{
    margin:0; background:var(--ivory); color:var(--body);
    font-family:"Noto Sans KR","Apple SD Gothic Neo",system-ui,sans-serif;
    line-height:1.75; word-break:keep-all;
  }}
  .wrap {{ width:min(1000px,calc(100% - 32px)); margin:0 auto; padding:48px 0 80px }}
  h1 {{ font-size:30px; font-weight:800; letter-spacing:-.04em; color:var(--ink); margin:0 0 8px }}
  .meta {{ display:flex; flex-wrap:wrap; gap:8px 20px; font-size:14px; color:var(--muted);
          padding-bottom:20px; border-bottom:1px solid var(--line); margin-bottom:32px }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:14px }}
  .cards figure {{ margin:0 }}
  .cards img {{ width:100%; border:1px solid var(--line); border-radius:8px; display:block; background:#fff }}
  .cards figcaption {{ font-size:12px; color:var(--muted); margin-top:6px; text-align:center }}
  h2 {{ font-size:15px; font-weight:700; letter-spacing:.08em; color:var(--green);
       margin:44px 0 14px; text-transform:uppercase }}
  .caption {{ background:var(--paper); border:1px solid var(--line); border-radius:10px;
             padding:24px 26px; white-space:pre-wrap; font-size:15px; color:var(--ink) }}
  .tags {{ margin-top:14px; display:flex; flex-wrap:wrap; gap:8px }}
  .tags span {{ font-size:13px; color:var(--green); background:#E8EEE9;
               border:1px solid #C8D2CC; border-radius:999px; padding:4px 12px }}
  .go {{ display:inline-block; margin-top:36px; padding:16px 26px; border-radius:10px;
        background:var(--green); color:#fff; font-weight:700; text-decoration:none; font-size:15px }}
  .note {{ margin-top:18px; font-size:13px; color:var(--muted) }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title}</h1>
  <div class="meta">
    <span>{category}</span>
    <span>{slug}</span>
    <span>최근 확인 {verified}</span>
    <span>카드 {count}장</span>
  </div>

  <h2>카드</h2>
  <div class="cards">{figures}</div>

  <h2>캡션</h2>
  <div class="caption">{caption}</div>
  <div class="tags">{tags}</div>

  <a class="go" href="{actions_url}">인스타그램 발행 워크플로 열기 →</a>
  <p class="note">확인 후 위 버튼에서 <b>Run workflow</b> → slug에 <code>{slug}</code>를 넣고,
  모의 실행으로 한 번 확인한 뒤 실제 발행하세요.</p>
</div>
</body>
</html>
"""


def main():
    if len(sys.argv) < 3:
        print("사용법: python3 build_preview.py <카드폴더> <출력 html>", file=sys.stderr)
        sys.exit(2)

    folder, out = sys.argv[1], sys.argv[2]
    card = json.load(open(os.path.join(folder, "card.json"), encoding="utf-8"))

    pngs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(folder, "*.png")))
    rel = os.path.relpath(folder, os.path.dirname(out) or ".")

    figures = "".join(
        f'<figure><img src="{rel}/{p}" alt="카드 {i}"><figcaption>{i:02d}</figcaption></figure>'
        for i, p in enumerate(pngs, 1)
    )
    tags = "".join(f"<span>#{escape(t)}</span>" for t in card.get("hashtags", []))

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    actions_url = (
        f"https://github.com/{repo}/actions/workflows/publish-instagram.yml"
        if repo else "#"
    )

    html = TPL.format(
        slug=escape(card["slug"]),
        title=escape(card["title"]),
        category=escape(card.get("category", "")),
        verified=escape(card.get("verified_on", "")),
        count=len(pngs),
        figures=figures,
        caption=escape(card["caption"]),
        tags=tags,
        actions_url=actions_url,
    )

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"검수 페이지 → {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
