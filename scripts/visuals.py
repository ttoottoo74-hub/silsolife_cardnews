#!/usr/bin/env python3
"""
카드뉴스 도식 생성기

JSON의 숫자를 인라인 SVG 도식으로 그립니다. 외부 이미지가 아니라
데이터에서 결정론적으로 만들어지므로, 엉뚱한 그림이 나갈 일이 없습니다.

지원 타입
    timeline  기한·시효   — 시간 축 위의 지점들
    compare   금액 비교   — 가로 막대
    steps     절차        — 번호가 붙은 단계
    range     구간·자격   — 기준선과 내 위치
"""

from html import escape

W = 924  # 카드 안쪽 폭 (1080 - 좌우 여백 78*2)


def _t(x, y, s, size, weight=700, fill="#1E211F", anchor="start", ls="-0.03em"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}">{escape(str(s))}</text>'
    )


def timeline(v, c):
    """기한·시효 — 가로 축 위에 지점을 찍는다."""
    steps = v["steps"][:4]
    n = len(steps)
    y = 96
    x0, x1 = 26, W - 26
    gap = (x1 - x0) / (n - 1) if n > 1 else 0

    out = [f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{c["line"]}" stroke-width="4"/>']

    # 마지막 구간을 강조색으로
    if n > 1:
        out.append(
            f'<line x1="{x0}" y1="{y}" x2="{x0 + gap}" y2="{y}" '
            f'stroke="{c["accent"]}" stroke-width="8" stroke-linecap="round"/>'
        )

    for i, s in enumerate(steps):
        x = x0 + gap * i
        last = i == n - 1
        r = 20 if (i == 0 or last) else 14
        fill = c["accent"] if (i == 0 or last) else c["paper"]
        out.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" '
            f'stroke="{c["accent"]}" stroke-width="6"/>'
        )
        anchor = "start" if i == 0 else ("end" if last else "middle")
        tx = x0 if i == 0 else (x1 if last else x)
        out.append(_t(tx, y - 46, s.get("note", ""), 34, 700, c["muted"], anchor, "0.04em"))
        out.append(_t(tx, y + 82, s["label"], 44 if n >= 4 else 54, 800, c["ink"], anchor))

    return f'<svg viewBox="0 0 {W} 196" width="{W}" height="196">' + "".join(out) + "</svg>"


def compare(v, c):
    """금액·수치 비교 — 가로 막대."""
    items = v["items"][:4]
    top = max(float(i["value"]) for i in items) or 1
    row_h, bar_h, label_w = 162, 58, 300
    h = row_h * len(items)
    out = []

    for i, it in enumerate(items):
        y = i * row_h + 20
        w = (W - label_w - 30) * (float(it["value"]) / top)
        fill = c["accent"] if i == 0 else c["accent_soft"]
        ink = c["ink"] if i == 0 else c["muted"]
        out.append(_t(0, y + 40, it["label"], 46, 700, c["ink"]))
        out.append(
            f'<rect x="{label_w}" y="{y}" width="{max(w, 8):.1f}" height="{bar_h}" '
            f'rx="6" fill="{fill}"/>'
        )
        out.append(_t(label_w, y + bar_h + 58, it["display"], 60, 900, ink))

    return f'<svg viewBox="0 0 {W} {h}" width="{W}" height="{h}">' + "".join(out) + "</svg>"


def steps(v, c):
    """절차 — 번호가 붙은 단계."""
    items = v["items"][:4]
    row_h = 148
    h = row_h * len(items)
    out = []

    for i, s in enumerate(items):
        y = i * row_h
        cy = y + 50
        if i < len(items) - 1:
            out.append(
                f'<line x1="38" y1="{cy + 40}" x2="38" y2="{cy + row_h - 40}" '
                f'stroke="{c["line"]}" stroke-width="4"/>'
            )
        out.append(f'<circle cx="38" cy="{cy}" r="37" fill="{c["accent"]}"/>')
        out.append(_t(38, cy + 14, i + 1, 46, 900, "#FFFFFF", "middle", "0"))
        out.append(_t(112, cy + 16, s, 54, 700, c["ink"]))

    return f'<svg viewBox="0 0 {W} {h}" width="{W}" height="{h}">' + "".join(out) + "</svg>"


def rng(v, c):
    """구간·자격 — 기준선 하나와 그 의미."""
    y = 74
    x0, x1 = 26, W - 26
    cut = x0 + (x1 - x0) * float(v.get("cut", 0.62))
    out = [
        f'<rect x="{x0}" y="{y}" width="{cut - x0:.1f}" height="52" rx="8" fill="{c["accent"]}"/>',
        f'<rect x="{cut:.1f}" y="{y}" width="{x1 - cut:.1f}" height="52" rx="8" fill="{c["accent_soft"]}"/>',
        f'<line x1="{cut:.1f}" y1="{y - 26}" x2="{cut:.1f}" y2="{y + 78}" '
        f'stroke="{c["ink"]}" stroke-width="4"/>',
        _t(x0, y - 36, v["low_label"], 40, 700, c["accent"]),
        _t(x1, y - 36, v["high_label"], 40, 700, c["muted"], "end"),
        _t(cut, y + 130, v["cut_label"], 56, 900, c["ink"], "middle"),
    ]
    return f'<svg viewBox="0 0 {W} 224" width="{W}" height="224">' + "".join(out) + "</svg>"


BUILDERS = {"timeline": timeline, "compare": compare, "steps": steps, "range": rng}


def build(visual, palette):
    """도식 SVG를 만든다. 타입을 모르면 None(도식 카드를 만들지 않는다)."""
    if not visual:
        return None
    fn = BUILDERS.get(visual.get("type"))
    if not fn:
        return None
    try:
        return fn(visual, palette)
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return None  # 데이터가 모자라면 조용히 건너뛴다
