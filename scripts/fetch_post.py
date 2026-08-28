#!/usr/bin/env python3
"""
실소 카드뉴스 수집기 (파이프라인 1~2단계)

silsolife.kr 앞에는 자바스크립트 퍼즐을 내는 방화벽이 있습니다.
평범한 프로그램 요청은 HTML 안내 페이지를 받고 막히므로,
카드 렌더링용으로 이미 설치해 둔 크롬으로 읽습니다. 브라우저는 퍼즐을 스스로 풉니다.

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
import urllib.parse

BASE = "https://silsolife.kr/wp-json/wp/v2"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

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


def fetch_json(path, **params):
    """크롬으로 REST API를 읽는다. 방화벽 퍼즐은 브라우저가 알아서 푼다."""
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        die(
            "playwright가 설치돼 있지 않습니다.\n"
            "  pip install playwright && playwright install chromium"
        )

    last_preview = ""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(user_agent=UA, locale="ko-KR")
        page = ctx.new_page()

        # 퍼즐을 푸는 데 한 번의 새로고침이 필요할 수 있어 몇 번 더 시도한다
        for attempt in range(1, 6):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                if attempt == 5:
                    browser.close()
                    die(f"[블로그에 접속할 수 없습니다] {url}\n{e}")
                page.wait_for_timeout(2000)
                continue

            page.wait_for_timeout(1500)
            text = (page.evaluate("document.body ? document.body.innerText : ''") or "").strip()
            last_preview = text[:400].replace("\n", " ")

            if text.startswith("[") or text.startswith("{"):
                browser.close()
                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    die(f"[JSON 해석 실패] {url}\n{e}\n앞부분: {last_preview}")

            print(f"  방화벽 통과 시도 {attempt}/5…", file=sys.stderr)

        browser.close()

    die(
        f"[방화벽을 통과하지 못했습니다] {url}\n"
        f"마지막 응답 앞부분: {last_preview}\n\n"
        "브라우저로도 JSON을 받지 못했습니다. 다음을 확인해 보세요.\n"
        "  · 호스팅의 보안·DDoS 차단 설정에서 /wp-json/ 경로를 예외로 둘 수 있는지\n"
        "  · 워드프레스 보안 플러그인이 REST API를 막고 있지 않은지"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="특정 글의 slug. 생략하면 최신 글")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    fields = "id,slug,date,link,categories,meta,title"
    if args.slug:
        posts = fetch_json("posts", slug=args.slug, _fields=fields)
    else:
        posts = fetch_json("posts", per_page=1, _fields=fields)

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
