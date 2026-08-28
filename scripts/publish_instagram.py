#!/usr/bin/env python3
"""
실소 카드뉴스 인스타그램 발행 (파이프라인 6단계)

사람이 검수 페이지에서 확인한 뒤에만 실행됩니다(workflow_dispatch).
캐러셀 발행은 3단계입니다: 카드별 컨테이너 → 캐러셀 컨테이너 → 발행.

필요한 환경변수
    IG_USER_ID        인스타그램 프로페셔널 계정의 ID
    IG_ACCESS_TOKEN   콘텐츠 발행 권한이 있는 액세스 토큰
    CARD_BASE_URL     카드 PNG가 공개된 주소의 베이스 (예: https://<user>.github.io/<repo>)

사용법:
    python3 publish_instagram.py card.json --dry-run    # 요청만 출력, 발행 안 함
    python3 publish_instagram.py card.json
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

GRAPH = "https://graph.instagram.com/" + os.environ.get("GRAPH_VERSION", "v26.0")
MAX_CAROUSEL = 10


def api(path, params, method="POST"):
    url = f"{GRAPH}/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"[API 오류 {e.code}] {body}", file=sys.stderr)
        raise


def caption_with_tags(card):
    tags = " ".join("#" + t for t in card["hashtags"])
    return f"{card['caption']}\n\n{tags} #실소생활정보"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("card")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    card = json.load(open(args.card, encoding="utf-8"))
    slug = card["slug"]

    base = os.environ.get("CARD_BASE_URL", "").rstrip("/")
    user_id = os.environ.get("IG_USER_ID", "")
    token = os.environ.get("IG_ACCESS_TOKEN", "")

    if not args.dry_run and not all([base, user_id, token]):
        print("CARD_BASE_URL / IG_USER_ID / IG_ACCESS_TOKEN이 필요합니다.", file=sys.stderr)
        sys.exit(1)

    n_cards = len(card["cards"]) + 4  # 표지 + 답 + 본문 + 주의 + 출처
    if n_cards > MAX_CAROUSEL:
        print(f"카드가 {n_cards}장입니다 — 캐러셀 상한 {MAX_CAROUSEL}장을 넘습니다.", file=sys.stderr)
        sys.exit(1)

    urls = [f"{base}/cards/{slug}/{i:02d}.png" for i in range(1, n_cards + 1)]

    caption = caption_with_tags(card)
    if len(caption) > 2200:
        print(f"캡션이 {len(caption)}자입니다 — 인스타그램 상한 2200자를 넘습니다.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[모의 실행] {slug} · 카드 {n_cards}장")
        for u in urls:
            print("  " + u)
        print("\n--- 캡션 ---\n" + caption)
        return

    # 1단계 — 카드별 컨테이너
    children = []
    for i, url in enumerate(urls, 1):
        res = api(f"{user_id}/media", {
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token,
        })
        children.append(res["id"])
        print(f"  컨테이너 {i:02d}/{n_cards} 생성", file=sys.stderr)
        time.sleep(1)

    # 2단계 — 캐러셀 컨테이너
    carousel = api(f"{user_id}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": token,
    })
    print("  캐러셀 컨테이너 생성", file=sys.stderr)

    # 컨테이너가 준비될 때까지 잠시 대기
    time.sleep(5)

    # 3단계 — 발행
    published = api(f"{user_id}/media_publish", {
        "creation_id": carousel["id"],
        "access_token": token,
    })

    print(f"\n발행 완료 — media id {published['id']}", file=sys.stderr)


if __name__ == "__main__":
    main()
