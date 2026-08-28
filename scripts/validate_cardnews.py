#!/usr/bin/env python3
"""
실소 카드뉴스 JSON 검증기 (파이프라인 3단계)

사용법:
    python3 validate_cardnews.py card.json

ERROR가 하나라도 있으면 카드 이미지를 만들지 않고 중단합니다.
WARN은 발행은 되지만 검수 화면에 표시합니다.
종료코드: 0 = 통과(WARN 포함), 1 = ERROR
"""

import json
import re
import sys
from datetime import date, datetime

CATEGORIES = {
    3: "돈·절약",
    4: "정부·제도",
    5: "건강생활",
    6: "생활",
    7: "가족·노후",
}

LIMITS = {
    "topic_label": 8,
    "hook": 20,
    "title": 40,
    "answer": 60,
    "heading": 14,
    "body": 75,
    "caution": 70,
    "caption": 300,
    "source_name": 12,
}

# 1차 출처로 인정하는 도메인
OFFICIAL_DOMAINS = (
    ".go.kr", ".or.kr", ".re.kr",
    "law.go.kr", "fsc.go.kr", "fss.or.kr",
)

errors, warns = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warns.append(msg)


def check(data):
    # ---- 필수 필드 ----
    for key in ("version", "published_at", "slug", "category", "category_id",
                "topic_label", "hook", "title", "answer", "cards",
                "caution", "sources", "verified_on", "caption", "hashtags"):
        if key not in data or data[key] in ("", None, []):
            err(f"필수 필드 누락: {key}")
    if errors:
        return

    # ---- 카테고리 ----
    cid = data["category_id"]
    if cid not in CATEGORIES:
        err(f"category_id {cid}는 사용할 수 없습니다 (3~7만 허용, 1=Uncategorized 금지)")
    elif CATEGORIES[cid] != data["category"]:
        err(f"category '{data['category']}'와 category_id {cid}({CATEGORIES[cid]})가 일치하지 않습니다")

    # ---- 길이 ----
    for key in ("topic_label", "hook", "title", "answer", "caution", "caption"):
        n = len(data[key])
        if n > LIMITS[key]:
            err(f"{key} {n}자 — {LIMITS[key]}자를 넘었습니다")

    # ---- 표지 문구 ----
    tl = data["topic_label"]
    if " " not in tl and len(tl) >= 6:
        warn(f"topic_label '{tl}' — 6자를 넘으면 띄어쓰는 편이 읽기 좋습니다")

    if not re.search(r"\d", data["hook"]) and re.search(r"\d", data["answer"]):
        warn("hook에 숫자가 없습니다 — answer의 숫자를 표지로 끌어올리면 구체적으로 읽힙니다")

    # ---- 카드 ----
    cards = data["cards"]
    if not 4 <= len(cards) <= 6:
        err(f"cards가 {len(cards)}개입니다 — 4~6개여야 합니다")

    # 캐러셀 상한 확인: 표지 + 답 + (도식) + 본문 + 주의 + 출처
    has_viz = bool(data.get("visual", {}).get("type"))
    total_cards = len(cards) + 4 + (1 if has_viz else 0)
    if total_cards > 10:
        err(f"전체 {total_cards}장 — 인스타그램 캐러셀 상한 10장을 넘습니다"
            + (" (도식 카드 포함). 본문 카드를 줄이세요." if has_viz else ""))
    elif total_cards == 10:
        warn("전체 10장 — 캐러셀 상한에 딱 걸렸습니다. 본문 카드를 늘릴 여유가 없습니다")

    for i, c in enumerate(cards, 1):
        head, body, hl = c.get("heading", ""), c.get("body", ""), c.get("highlight", "")

        if len(head) > LIMITS["heading"]:
            err(f"카드{i} heading {len(head)}자 — {LIMITS['heading']}자 초과")
        if len(body) > LIMITS["body"]:
            err(f"카드{i} body {len(body)}자 — {LIMITS['body']}자 초과")

        if hl is None:
            # 강조할 게 정말 없을 때만 null이 허용된다.
            # body에 숫자가 있는데 null이면 강조를 놓친 것이다.
            found = re.search(r"\d+\s*(년|개월|일|세|원|만원|억|%|배|건|회)", body)
            if found:
                warn(f"카드{i} highlight가 비어 있는데 body에 '{found.group()}'이 있습니다 — 이걸 강조하세요")
            continue

        # highlight는 body에서 그대로 잘라낸 조각이어야 한다
        if hl not in body:
            err(f"카드{i} highlight '{hl}'가 body 안에 없습니다")

        # body 끝에 (highlight)를 덧붙이는 패턴 — 렌더링에 그대로 노출됨
        if re.search(r"[（(]\s*" + re.escape(hl) + r"\s*[)）]\s*$", body):
            err(f"카드{i} body 끝에 '({hl})'가 덧붙어 있습니다 — 카드에 괄호가 그대로 찍힙니다")

        # 강조값 품질: 숫자나 고유명사가 아니면 강조 효과가 약하다
        if not re.search(r"\d", hl) and len(hl.split()) > 1:
            warn(f"카드{i} highlight '{hl}' — 숫자나 고유명사 한 단어가 더 잘 읽힙니다")
        if len(hl) > 12:
            warn(f"카드{i} highlight {len(hl)}자 — 12자 이내를 권합니다")

    # 강조가 대부분 비어 있으면 카드가 밋밋해진다
    filled = sum(1 for c in cards if c.get("highlight"))
    if filled * 2 < len(cards):
        warn(f"highlight가 {filled}/{len(cards)}장에만 있습니다 — 절반 이상은 강조값을 채우세요")

    # 숫자가 들어간 카드가 절반 미만이면 밋밋해진다
    numeric = sum(1 for c in cards if re.search(r"\d", c.get("body", "")))
    if numeric * 2 < len(cards):
        warn(f"숫자가 든 카드가 {numeric}/{len(cards)}장뿐입니다 — 금액·기한·나이를 살리면 좋습니다")

    # ---- 출처 ----
    srcs = data["sources"]
    if not 1 <= len(srcs) <= 3:
        err(f"sources가 {len(srcs)}개입니다 — 1~3개여야 합니다")

    seen_urls = [s.get("url", "") for s in srcs if s.get("url")]
    for u in set(seen_urls):
        if seen_urls.count(u) > 1:
            err(f"같은 출처 URL이 {seen_urls.count(u)}번 중복됩니다: {u}")

    for s in srcs:
        name, url = s.get("name", ""), s.get("url", "")
        if not url:
            err(f"출처 '{name}'의 url이 비어 있습니다")
        elif not url.startswith("http"):
            err(f"출처 url 형식 오류: {url}")
        elif not any(d in url for d in OFFICIAL_DOMAINS):
            warn(f"출처 '{url}'가 공식 도메인(.go.kr/.or.kr)이 아닙니다 — 1차 출처인지 확인하세요")
        if len(name) > LIMITS["source_name"]:
            err(f"출처명 '{name[:14]}…' {len(name)}자 — 출처 카드에 들어가려면 {LIMITS['source_name']}자 이내여야 합니다")

    # ---- 캡션 ----
    cap = data["caption"]
    if "\n" not in cap:
        warn("caption에 줄바꿈이 없습니다 — 인스타그램에서 한 덩어리로 보입니다")
    if re.search(r"(하십시오|하시기 바랍니다|하십시요)\.?\s*$", cap.strip()):
        warn("caption이 공문 말투로 끝납니다 — '~해 보세요' 쪽이 자연스럽습니다")

    # ---- 해시태그 ----
    tags = data["hashtags"]
    if not 8 <= len(tags) <= 15:
        err(f"hashtags가 {len(tags)}개입니다 — 8~15개여야 합니다")
    for t in tags:
        if t.startswith("#"):
            err(f"해시태그 '{t}'에 #이 포함돼 있습니다 — 문자열만 넣으세요")
        if " " in t:
            err(f"해시태그 '{t}'에 공백이 있습니다")

    # ---- 날짜 ----
    try:
        v = datetime.strptime(data["verified_on"], "%Y-%m-%d").date()
        if v > date.today():
            err(f"verified_on {v}이 미래 날짜입니다")
        elif (date.today() - v).days > 90:
            warn(f"verified_on {v} — 확인한 지 {(date.today() - v).days}일 지났습니다")
    except ValueError:
        err("verified_on 형식 오류 (YYYY-MM-DD)")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 validate_cardnews.py card.json")
        sys.exit(2)

    path = sys.argv[1]
    try:
        data = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 문법 오류: {e}")
        sys.exit(1)

    check(data)

    print(f"\n검증 대상: {data.get('slug', path)}")
    print("─" * 60)

    for m in errors:
        print(f"  [ERROR] {m}")
    for m in warns:
        print(f"  [WARN ] {m}")

    if not errors and not warns:
        print("  통과 — 문제 없습니다.")

    print("─" * 60)
    if errors:
        print(f"결과: 발행 중단 (ERROR {len(errors)}건, WARN {len(warns)}건)\n")
        sys.exit(1)

    print(f"결과: 통과 (WARN {len(warns)}건)\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
