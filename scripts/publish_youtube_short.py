#!/usr/bin/env python3
import argparse
import json
import os
import tempfile
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"


def form_post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={"content-type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def access_token():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError("YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN이 필요합니다.")
    result = form_post(TOKEN_URL, {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    return result["access_token"]


def download(url):
    if not url.startswith("https://"):
        raise RuntimeError("HTTPS video_url이 필요합니다.")
    handle = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    with urllib.request.urlopen(url, timeout=180) as response:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    handle.close()
    return handle.name


def upload(path, payload):
    token = access_token()
    size = os.path.getsize(path)
    tags = [str(item)[:100] for item in payload.get("tags", []) if str(item).strip()][:20]
    metadata = json.dumps({
        "snippet": {
            "title": str(payload.get("title") or "실소라이프 숏폼")[:100],
            "description": str(payload.get("description") or "")[:5000],
            "tags": tags,
            "categoryId": os.environ.get("YOUTUBE_CATEGORY_ID", "22"),
        },
        "status": {
            "privacyStatus": os.environ.get("YOUTUBE_PRIVACY_STATUS", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(UPLOAD_URL, data=metadata, method="POST", headers={
        "authorization": f"Bearer {token}",
        "content-type": "application/json; charset=UTF-8",
        "content-length": str(len(metadata)),
        "x-upload-content-length": str(size),
        "x-upload-content-type": "video/mp4",
    })
    with urllib.request.urlopen(request, timeout=90) as response:
        session = response.headers.get("Location")
    if not session:
        raise RuntimeError("YouTube resumable upload session URL이 없습니다.")
    with open(path, "rb") as source:
        data = source.read()
    request = urllib.request.Request(session, data=data, method="PUT", headers={
        "authorization": f"Bearer {token}",
        "content-type": "video/mp4",
        "content-length": str(len(data)),
    })
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    payload = json.load(open(args.payload, encoding="utf-8"))
    path = download(str(payload.get("video_url") or ""))
    try:
        result = upload(path, payload)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    print(json.dumps({"platform": "youtube", "video_id": result.get("id", "")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
