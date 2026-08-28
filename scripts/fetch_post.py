#!/usr/bin/env python3
"""
실소 카드뉴스 수집기 (파이프라인 1~2단계)

WordPress REST API에서 최신 글을 읽어 카드 JSON을 만들어 냅니다.
- 커스텀 필드(silso_cardnews)에 GPT가 넣어준 JSON이 있으면 그것을 씁니다.
- 없으면 처리를 건너뜁니다(빈 카드를 지어내지 않습니다).
- link/date/category는 GPT 값을 믿지 않고 실제 발행본으로 덮어씁니다.

종료코드
    0   정상
    78  오늘은 건너뜀 (카드 JSON 없음) — 워크플로가 조용히 종료합니다
    1   진짜 오류

사용법:
    python3 fetch_post.py --out card.json              # 최신 글
    python3 fetch_post.py --slug my-post --out card.json
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://silsolife.kr/wp-json/wp/v2"

# 일부 호스팅은 프로그램처럼 보이는 요청을 차단하고 HTML 안내 페이지를 돌려줍니다.
# 브라우저와 같은 헤더를 보내 그 차단을 피합니다.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

CATEGORY_BY_ID = {
    3: "돈·절약",
    4: "정부·제도",
    5: "건강생활",
    6: "생활",
    7: "가족·노후",
}


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def get(path, **params):
    """WordPress REST API 호출. 실패하면 무엇이 돌아왔는지 보여주고 끝냅니다."""
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", "replace")
            ctype = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        die(f"[블로그 응답 오류 {e.code}] {url}\n{body}")
    except urllib.error.URLError as e:
        die(f"[블로그에 접속할 수 없습니다] {url}\n{e.reason}")

    if not raw.strip():
        die(f"[빈 응답] {url}\n블로그가 아무 내용도 돌려주지 않았습니다.")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        preview = raw.strip()[:400].replace("\n", " ")
        die(
            f"[JSON이 아닌 응답] {url}\n"
            f"Content-Type: {ctype}\n"
            f"돌아온 내용 앞부분: {preview}\n\n"
            "REST API가 아니라 HTML이 왔습니다. 대개 다음 중 하나입니다.\n"
            "  · 보안 플러그인이나 방화벽이 프로그램 접근을 막고 있다\n"
            "  · REST API가 비활성화돼 있다\n"
            "  · 점검 모드이거나 로그인 페이지로 넘어간다\n"
            "브라우저에서 같은 주소를 열어 JSON이 보이는지 확인해 보세요."
        )


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

    if not isinstance(posts, list) or not posts:
        die("발행된 글을 찾지 못했습니다.")

    post = posts[0]
    raw = (post.get("meta") or {}).get("silso_cardnews", "")

    if not raw:
        die(
            f"'{post['slug']}'에 카드뉴스 JSON(silso_cardnews)이 없습니다.\n"
            "GPT가 발행 시 이 필드를 채우도록 지시문을 확인하세요.",
            78,  # 오늘은 건너뜀 — 고장이 아닙니다
        )

    try:
        card = json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"커스텀 필드의 JSON 문법 오류: {e}")

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
