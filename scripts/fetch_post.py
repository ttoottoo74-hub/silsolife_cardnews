#!/usr/bin/env python3
"""
실소 카드뉴스 수집기 (파이프라인 1~2단계)

WordPress REST API에서 최신 글을 읽어 카드 JSON을 만들어 냅니다.
- 커스텀 필드(silso_cardnews)에 GPT가 넣어준 JSON이 있으면 그것을 씁니다.
- 없으면 처리를 건너뜁니다(빈 카드를 지어내지 않습니다).
- link/date/category는 GPT 값을 믿지 않고 실제 발행본으로 덮어씁니다.

사용법:
    python3 fetch_post.py --out card.json              # 최신 글
    python3 fetch_post.py --slug my-post --out card.json
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

BASE = "https://silsolife.kr/wp-json/wp/v2"

CATEGORY_BY_ID = {
    3: "돈·절약",
    4: "정부·제도",
    5: "건강생활",
    6: "생활",
    7: "가족·노후",
}


def get(path, **params):
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "silso-cardnews/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="특정 글의 slug. 생략하면 최신 글")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    fields = "id,slug,date,link,categories,meta,title"
    if args.slug:
        posts = get("posts", slug=args.slug, _fields=fields)
    else:
        posts = get("posts", per_page=1, _fields=fields)

    if not posts:
        print("발행된 글을 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    post = posts[0]
    raw = (post.get("meta") or {}).get("silso_cardnews", "")

    if not raw:
        print(
            f"'{post['slug']}'에 카드뉴스 JSON(silso_cardnews)이 없습니다.\n"
            "GPT가 발행 시 이 필드를 채우도록 지시문을 확인하세요.",
            file=sys.stderr,
        )
        sys.exit(78)  # EX_CONFIG — 워크플로에서 '오늘은 건너뜀'으로 처리

    try:
        card = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"커스텀 필드의 JSON 문법 오류: {e}", file=sys.stderr)
        sys.exit(1)

    # ---- 실제 발행본으로 덮어쓰기 ----
    card["slug"] = post["slug"]
    card["published_at"] = post["date"]
    card["link"] = post["link"]

    cat_ids = [c for c in post.get("categories", []) if c in CATEGORY_BY_ID]
    if cat_ids:
        card["category_id"] = cat_ids[0]
        card["category"] = CATEGORY_BY_ID[cat_ids[0]]
    else:
        print(
            f"경고: '{post['slug']}'가 카테고리 없이 발행됐습니다(Uncategorized). "
            "GPT 값을 그대로 씁니다.",
            file=sys.stderr,
        )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=2)

    print(f"{post['slug']} → {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
