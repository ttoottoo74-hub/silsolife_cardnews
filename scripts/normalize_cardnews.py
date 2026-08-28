#!/usr/bin/env python3
"""
실소 카드뉴스 JSON 자동 교정 (파이프라인 3단계 앞)

GPT를 완벽하게 훈련시키는 대신, 기계가 고칠 수 있는 것은 기계가 고칩니다.
사람의 판단이 필요한 것(hook 문구, 어떤 출처를 쓸지)만 검증기가 남깁니다.

사용법:
    python3 normalize_cardnews.py card.json > card.clean.json
    python3 validate_cardnews.py card.clean.json
"""

import json
import re
import sys

# 강조값으로 뽑을 만한 패턴 — 앞쪽일수록 우선
HIGHLIGHT_PATTERNS = [
    r"\d[\d,]*\s*(?:억|만)?\s*원",        # 247만원, 1억원
    r"만\s*\d+\s*세",                      # 만 65세
    r"\d+\s*(?:년|개월|일|세|%|배|회|건)",  # 3년, 6개월, 65세
]

# 고유명사 사전 — 제도·기관·서비스 이름
PROPER_NOUNS = [
    "실손24", "내보험찾아줌", "정부보장사업", "에너지바우처", "기초연금",
    "국민연금", "예금자보호", "안심상속 원스톱", "건강보험", "K-apt",
    "자동차손해배상진흥원", "금융감독원", "국가법령정보센터",
]

fixes = []


def pick_highlight(body):
    """body 안에서 강조할 조각 하나를 고른다. 없으면 None."""
    for pat in HIGHLIGHT_PATTERNS:
        m = re.search(pat, body)
        if m:
            return re.sub(r"\s+", "", m.group())
    for noun in PROPER_NOUNS:
        if noun in body:
            return noun
    return None


def normalize(d):
    # 1) 카드 본문 끝에 덧붙은 (강조어) 제거
    for i, c in enumerate(d.get("cards", []), 1):
        body = c.get("body", "")
        cleaned = re.sub(r"\s*[（(][^()（）]{1,14}[)）]\s*$", "", body).strip()
        if cleaned != body:
            c["body"] = cleaned
            fixes.append(f"카드{i} 본문 끝 괄호 제거 ({len(body)}자 → {len(cleaned)}자)")

    # 2) highlight가 비어 있으면 body에서 자동 추출
    for i, c in enumerate(d.get("cards", []), 1):
        if not c.get("highlight"):
            picked = pick_highlight(c.get("body", ""))
            if picked:
                c["highlight"] = picked
                fixes.append(f"카드{i} highlight 자동 추출 → '{picked}'")

    # 3) highlight가 body에 없으면 버린다 (억지 강조 방지)
    for i, c in enumerate(d.get("cards", []), 1):
        hl = c.get("highlight")
        if hl and hl not in c.get("body", ""):
            c["highlight"] = None
            fixes.append(f"카드{i} highlight '{hl}'가 본문에 없어 제거")

    # 4) 중복 출처 제거 (URL 기준, 순서 유지)
    seen, uniq = set(), []
    for s in d.get("sources", []):
        u = s.get("url", "")
        if u and u in seen:
            fixes.append(f"중복 출처 제거: {s.get('name', '')}")
            continue
        seen.add(u)
        uniq.append(s)
    d["sources"] = uniq

    # 5) 해시태그 정리 — # 제거, 공백 제거, 중복 제거
    tags, seen_t = [], set()
    for t in d.get("hashtags", []):
        t2 = t.lstrip("#").replace(" ", "")
        if t2 and t2 not in seen_t:
            seen_t.add(t2)
            tags.append(t2)
        elif t2 in seen_t:
            fixes.append(f"중복 해시태그 제거: {t2}")
    if tags != d.get("hashtags"):
        d["hashtags"] = tags

    return d


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 normalize_cardnews.py card.json > card.clean.json", file=sys.stderr)
        sys.exit(2)

    d = json.load(open(sys.argv[1], encoding="utf-8"))
    d = normalize(d)

    for f in fixes:
        print(f"  [FIX] {f}", file=sys.stderr)
    if not fixes:
        print("  고칠 것이 없습니다.", file=sys.stderr)

    print(json.dumps(d, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
