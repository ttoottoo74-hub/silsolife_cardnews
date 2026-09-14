#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

GRAPH = "https://graph.instagram.com/" + os.environ.get("GRAPH_VERSION", "v26.0")


def api(path, params=None, method="POST"):
    params = params or {}
    url = f"{GRAPH}/{path}"
    data = None
    if method == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        print(f"[Instagram API {exc.code}] {detail}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    payload = json.load(open(args.payload, encoding="utf-8"))
    user_id = os.environ.get("IG_USER_ID", "")
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    if not user_id or not token:
        raise SystemExit("IG_USER_ID / IG_ACCESS_TOKEN이 필요합니다.")

    video_url = str(payload.get("video_url") or "")
    caption = str(payload.get("caption") or payload.get("description") or "")[:2200]
    if not video_url.startswith("https://"):
        raise SystemExit("HTTPS video_url이 필요합니다.")

    container = api(f"{user_id}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": token,
    })
    creation_id = container["id"]
    print(f"Reels container {creation_id} 생성", file=sys.stderr)

    deadline = time.time() + 600
    while time.time() < deadline:
        status = api(creation_id, {"fields": "status_code,status", "access_token": token}, method="GET")
        code = str(status.get("status_code") or "")
        if code == "FINISHED":
            break
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Reels container failed: {status}")
        time.sleep(5)
    else:
        raise TimeoutError("Reels container processing timed out.")

    published = api(f"{user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    print(json.dumps({"platform": "instagram", "media_id": published["id"], "creation_id": creation_id}, ensure_ascii=False))


if __name__ == "__main__":
    main()
