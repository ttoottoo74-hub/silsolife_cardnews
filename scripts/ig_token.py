#!/usr/bin/env python3
"""
인스타그램 토큰 도우미 — 내 컴퓨터에서 실행합니다.

토큰은 이 스크립트와 GitHub Secrets 밖으로 나가지 않습니다.
채팅창이나 문서에 붙여넣지 마세요.

    # 1) 계정 ID 확인 — IG_USER_ID에 넣을 값
    python3 ig_token.py whoami --token EAAG...

    # 2) 토큰 60일 연장 — 만료 전에 실행하고 새 토큰을 Secrets에 갱신
    python3 ig_token.py refresh --token EAAG...

토큰을 명령줄에 쓰기 싫으면 환경변수로 주세요.
    IG_ACCESS_TOKEN=EAAG... python3 ig_token.py whoami
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

GRAPH = "https://graph.instagram.com"
VERSION = os.environ.get("GRAPH_VERSION", "v26.0")


def get(path, **params):
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"[오류 {e.code}] {body}", file=sys.stderr)
        sys.exit(1)


def whoami(token):
    res = get(f"{VERSION}/me", fields="user_id,username,account_type", access_token=token)
    data = res.get("data", [res])[0] if isinstance(res.get("data"), list) else res

    uid = data.get("user_id")
    print()
    print(f"  사용자명   @{data.get('username', '?')}")
    print(f"  계정 유형  {data.get('account_type', '?')}")
    print(f"  IG_USER_ID {uid}")
    print()
    print("  ↑ IG_USER_ID 값을 GitHub Secrets에 넣으세요.")
    print("     주의: 'id'가 아니라 'user_id'입니다. 둘은 다른 값입니다.")
    print()


def refresh(token):
    res = get("refresh_access_token", grant_type="ig_refresh_token", access_token=token)
    new_token = res.get("access_token", "")
    secs = int(res.get("expires_in", 0))
    days = secs // 86400
    expires = date.today() + timedelta(days=days)

    print()
    print(f"  연장 완료 — {days}일 ({expires.isoformat()}까지)")
    print()
    print("  새 토큰:")
    print(f"  {new_token}")
    print()
    print("  다음 두 가지를 갱신하세요.")
    print("    Secrets   IG_ACCESS_TOKEN     ← 위 새 토큰")
    print(f"    Variables IG_TOKEN_EXPIRES    ← {expires.isoformat()}")
    print()
    print("  그리고 캘린더 알림을 다음 날짜로 옮겨두세요:")
    print(f"    {(expires - timedelta(days=14)).isoformat()}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["whoami", "refresh"])
    ap.add_argument("--token", default=os.environ.get("IG_ACCESS_TOKEN", ""))
    args = ap.parse_args()

    if not args.token:
        print("토큰이 없습니다. --token 또는 IG_ACCESS_TOKEN 환경변수로 주세요.", file=sys.stderr)
        sys.exit(2)

    if args.command == "whoami":
        whoami(args.token)
    else:
        refresh(args.token)


if __name__ == "__main__":
    main()
