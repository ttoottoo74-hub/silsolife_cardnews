# 실소 카드뉴스 자동화

silsolife.kr에 매일 올라가는 글을 인스타그램 카드뉴스로 만들어 발행합니다.

카드 JSON이 들어오면 → 카드 PNG 8~10장을 만들어 공개 주소에 올리고 → 인스타그램 캐러셀로 발행합니다.

```
앱(실소 콘텐츠 랩)                    이 저장소                        인스타그램
──────────────────────────────────────────────────────────────────────────────
글 발행 + 카드 JSON 생성
        │
        ├─ dispatch "cardnews" ──▶  자동 교정 → 검증 → 렌더 → 커밋
        │                            (약 50초, docs/cards/<slug>/)
        │                                    │
        │◀──── 카드 PNG 공개 주소 ────────────┘
        │
   텔레그램으로 승인 요청
        │
        └─ dispatch "publish-instagram" ──▶  캐러셀 발행 ──────────▶  게시
```

## 카드 JSON을 넣는 세 가지 방법

| 방법 | 언제 쓰나 |
|---|---|
| **① 앱이 보낸다** (`repository_dispatch`) | 정식 경로. 앱이 글을 발행한 직후 자동으로 보냅니다 |
| **② 손으로 붙여넣는다** (`workflow_dispatch`) | 앱 연동 전이거나 한 건만 다시 만들고 싶을 때 |
| ~~③ 블로그에서 읽어온다~~ | **지금은 쓸 수 없습니다.** 아래 참조 |

> ⚠️ **③은 죽어 있습니다.** 카페24 스팸SHIELD가 해외 IP를 막고 있어 GitHub 서버가 블로그를 읽지 못합니다.
> 게다가 워드프레스 글의 `meta`에 `silso_cardnews` 필드가 없어서, 읽을 수 있다 해도 가져올 것이 없습니다.
> 방화벽은 실제 공격 트래픽을 막고 있으므로 끄지 않습니다. `fetch_post.py`와 `wp-cardnews-meta.php`는
> 나중을 위해 남겨뒀을 뿐, 지금은 쓰지 마세요.

### ① 앱이 보내는 방법

```http
POST https://api.github.com/repos/ttoottoo74-hub/silsolife_cardnews/dispatches
Authorization: Bearer {GITHUB_CARDNEWS_TOKEN}
Accept: application/vnd.github+json

{ "event_type": "cardnews", "client_payload": { "card": { …카드 JSON 전체… } } }
```

**`card` 한 겹으로 감싸야 합니다.** GitHub는 `client_payload`의 최상위 항목을 10개까지만 받는데
카드 JSON은 항목이 16개라 그대로 넣으면 422로 거부됩니다.

성공은 **HTTP 204**이고 응답 본문이 비어 있습니다. 본문이 없다고 실패로 처리하지 마세요.

발행 신호도 같은 방식입니다.

```json
{ "event_type": "publish-instagram", "client_payload": { "slug": "…" } }
```

앱이 구현해야 할 것은 `작업지시서-v2-카드뉴스-텔레그램승인.md`에 전부 적혀 있습니다.

### ② 손으로 붙여넣는 방법

Actions → **카드뉴스 생성** → Run workflow → **카드 JSON 통째로 붙여넣기** 칸에
`{` 부터 `}` 까지 통째로 넣고 실행합니다. 토큰도 설정도 필요 없습니다.

## 파이프라인

| 단계 | 하는 일 | 파일 |
|---|---|---|
| 1 | 카드 JSON 받기 (①/②) | `daily-cards.yml` |
| 2 | 자동 교정 — 글자 수, highlight 추출, 출처 중복 제거 | `normalize_cardnews.py` |
| 3 | 검증 — 어기면 이미지를 만들지 않고 멈춘다 | `validate_cardnews.py` |
| 4 | 카드 PNG 렌더 (1080×1350) | `render_cards.py` · `visuals.py` |
| 5 | 검수 페이지 생성 · 커밋 → 공개 주소 확보 | `build_preview.py` |
| 6 | 인스타그램 캐러셀 발행 | `publish_instagram.py` |

1~5는 자동입니다. 6은 앱의 텔레그램 승인이나 사람이 누르는 버튼으로 시작합니다.

## 카드 디자인

표지 → 한 줄 답 → (도식) → 본문 4~6장 → 주의 → 출처. 전부 1080×1350.

- **표제 서체는 명조**(Noto Serif CJK KR), 본문은 고딕. 되돌리려면 Variables에 `CARD_FONT` = `sans`.
- **색은 카테고리로 갈립니다.** 여백·서체·배치는 같고 색만 바뀝니다.

  | `category_id` | 카테고리 | 색 |
  |---|---|---|
  | 3 | 돈·절약 | 숲초록 `#2F5B4B` |
  | 4 | 정부·제도 | 감청 `#2A4A73` |
  | 5 | 건강생활 | 청록 `#1D6A66` |
  | 6 | 생활 | 테라코타 `#9A5426` |
  | 7 | 가족·노후 | 플럼 `#6E3B5A` |

  값이 비면 전부 초록으로 나옵니다. 주의 카드만 어느 색에서든 눈에 띄게 호박색으로 고정돼 있습니다.
- **표지의 가장 큰 글씨는 `hook` 안의 첫 숫자**입니다. 렌더러가 자동으로 찾아 1.34배로 키웁니다.
  `3년 지나면 못 받습니다`는 잘 나오고, 숫자가 없는 `놓치면 받을 돈이 사라집니다`는 밋밋해집니다.

## 처음 한 번 해야 할 설정

### 1. GitHub Pages
Settings → Pages → Source를 `main` 브랜치의 `/docs` 폴더로.
**인스타그램 API는 이미지를 공개 URL로만 받기 때문에 건너뛸 수 없습니다.**
저장소를 비공개로 두면 Pages도 막혀 발행이 실패합니다.

Settings → Secrets and variables → Actions → **Variables**

| 이름 | 값 |
|---|---|
| `CARD_BASE_URL` | `https://ttoottoo74-hub.github.io/silsolife_cardnews` |
| `IG_TOKEN_EXPIRES` | 인스타그램 토큰 만료일 (`YYYY-MM-DD`). 14일 전부터 경고합니다 |
| `CARD_FONT` | (선택) `sans`로 두면 고딕. 비우면 명조 |

### 2. 인스타그램
프로페셔널(비즈니스/크리에이터) 계정이어야 하고, Meta 앱에서 콘텐츠 발행 권한이 필요합니다.

Settings → Secrets and variables → Actions → **Secrets**

| 이름 | 값 |
|---|---|
| `IG_USER_ID` | 인스타그램 프로페셔널 계정 ID |
| `IG_ACCESS_TOKEN` | 콘텐츠 발행 권한이 있는 장기 토큰 (60일) |

토큰은 만료됩니다. `scripts/ig_token.py refresh`로 연장하고 `IG_TOKEN_EXPIRES`도 새 날짜로 바꾸세요.

### 3. 발행 승인 게이트 (선택)
Settings → Environments → `instagram` 환경에 필수 리뷰어를 지정하면
발행 워크플로가 승인 없이는 돌지 않습니다. 앱의 텔레그램 승인과 겹치므로 보통은 비워 둡니다.

## 손으로 돌려보기

```bash
python3 scripts/normalize_cardnews.py card.raw.json > card.json
python3 scripts/validate_cardnews.py card.json
CARD_FONT=serif python3 scripts/render_cards.py card.json out/
python3 scripts/publish_instagram.py out/card.json --dry-run
```

## 알아둘 제약

- **캐러셀은 최대 10장.** 첫 장 비율로 전체가 잘리므로 카드는 전부 1080×1350입니다.
- **본문 카드가 6장이면 도식(`visual`)을 넣지 마세요.** 표지·답·주의·출처가 이미 4장을 씁니다.
- 인스타그램 발행은 24시간에 100건까지. 캐러셀 하나는 1건으로 계산됩니다.
- 카드 이미지 주소는 Pages 배포 뒤에야 열립니다. 렌더가 끝나고 1분쯤 걸립니다.
- `client_payload`는 최상위 항목 10개, 전체 64KB까지입니다.
