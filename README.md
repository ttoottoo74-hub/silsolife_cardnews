# 실소 카드뉴스 자동화

silsolife.kr에 매일 올라가는 글을 인스타그램 카드뉴스로 만들어 발행합니다.

```
1  GPT가 글 발행 + 커스텀 필드에 카드 JSON        (GPT)
2  WordPress REST API로 수집 · 실제 발행본으로 보강  fetch_post.py
3  자동 교정 → 검증                              normalize / validate
4  카드 PNG 렌더 (1080×1350)                     render_cards.py
5  검수 페이지 생성 · 커밋 → 공개 URL 확보         build_preview.py
6  사람이 확인 → 인스타그램 캐러셀 발행            publish_instagram.py
```

1~5단계는 매일 자동으로 돕니다. 6단계만 사람이 누릅니다.

## 처음 한 번 해야 할 설정

### 1. GitHub Pages 켜기
Settings → Pages → Source를 `main` 브랜치의 `/docs` 폴더로 지정합니다.
카드 PNG가 여기로 공개됩니다. **인스타그램 API가 이미지를 공개 URL로만 받기 때문에 이 단계는 건너뛸 수 없습니다.**

공개 주소를 확인한 뒤 Settings → Secrets and variables → Actions → Variables에 등록합니다.

| 이름 | 값 |
|---|---|
| `CARD_BASE_URL` | `https://<계정>.github.io/<저장소>` |

### 2. 워드프레스 커스텀 필드
`wp-cardnews-meta.php`를 `wp-content/mu-plugins/`에 올립니다. 별도 활성화는 필요 없습니다.
그 뒤 아래 주소에서 값이 보이면 정상입니다.

```
https://silsolife.kr/wp-json/wp/v2/posts?per_page=1&_fields=slug,meta
```

### 3. 인스타그램
프로페셔널(비즈니스/크리에이터) 계정이어야 하고, Meta 앱에서 콘텐츠 발행 권한을 받아야 합니다.
개인 계정은 발행 API를 쓸 수 없습니다.

Settings → Secrets and variables → Actions → Secrets에 등록합니다.

| 이름 | 값 |
|---|---|
| `IG_USER_ID` | 인스타그램 프로페셔널 계정 ID |
| `IG_ACCESS_TOKEN` | 콘텐츠 발행 권한이 있는 장기 토큰 |

토큰은 만료됩니다. 갱신 주기를 달력에 넣어두세요.

### 4. 발행 승인 게이트 (선택)
Settings → Environments → `instagram` 환경을 만들고 필수 리뷰어를 지정하면,
발행 워크플로가 승인 없이는 돌지 않습니다.

## 매일 일어나는 일

`daily-cards.yml`이 KST 08:00에 돕니다. 블로그 발행 시각에 맞춰 cron을 조정하세요.

- 카드 JSON이 없는 날은 **조용히 건너뜁니다**(빈 카드를 지어내지 않습니다).
- 검증에서 ERROR가 나면 **이미지를 만들지 않고 멈춥니다**. Actions 로그에 사유가 남습니다.
- 성공하면 `docs/cards/<slug>/`에 PNG가 쌓이고 검수 페이지가 갱신됩니다.

## 발행하기

1. `https://<계정>.github.io/<저장소>` 에서 카드와 캡션을 확인합니다.
2. Actions → **인스타그램 발행** → Run workflow.
3. slug를 넣고 **모의 실행을 먼저 한 번** 돌려 이미지 URL이 열리는지 확인합니다.
4. 모의 실행이 깨끗하면 `dry_run`을 끄고 다시 실행합니다.

## 손으로 돌려보기

```bash
python3 scripts/fetch_post.py --out card.raw.json
python3 scripts/normalize_cardnews.py card.raw.json > card.json
python3 scripts/validate_cardnews.py card.json
python3 scripts/render_cards.py card.json out/
```

## 알아둘 제약

- 캐러셀은 최대 10장, 첫 장 비율로 전체가 잘립니다. 카드는 전부 1080×1350입니다.
- 본문 카드가 6장을 넘으면 상한에 걸립니다(표지·답·주의·출처가 4장을 씁니다).
- 인스타그램 발행은 24시간에 100건까지, 캐러셀은 1건으로 계산됩니다.
- 이미지 URL에 인증이 걸려 있으면 실패합니다. 저장소를 비공개로 두면 Pages도 막힙니다.
