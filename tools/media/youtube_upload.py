#!/usr/bin/env python3
"""Upload a finished piece to the project's YouTube channel (resumable upload, no SDK).

Credentials come only from the environment, never from files in the repository:

    YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN

The operator creates them once (coordination/MEDIA_PRODUCTION.md, "YouTube channel"):
a Google Cloud project with the YouTube Data API v3 enabled, an OAuth client of type
"Desktop app", and one consent for the scope youtube.upload on the channel's Google
account; the refresh token from that consent goes in the environment as a secret.
Until Google verifies the OAuth app, every video uploaded through the API is locked
to private; the operator can flip it to public in YouTube Studio, which is the
expected route for the first pieces anyway.

    python3 tools/media/youtube_upload.py build/<slug>/<slug>.mp4 --meta build/<slug>/youtube.json [--publish]

--meta is a JSON file with title, description, tags and optional playlist_id;
`make.py` writes a draft of it. Without --publish the video is uploaded as
private (the only state an unverified app can set). Exit 2 when credentials are
missing, so a scheduled run reports the gap instead of pretending.
"""
import argparse
import json
import os
from pathlib import Path
import sys

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
CAPTIONS_URL = "https://www.googleapis.com/upload/youtube/v3/captions"
CA = os.environ.get("SSL_CERT_FILE") or ("/root/.ccr/ca-bundle.crt" if Path("/root/.ccr/ca-bundle.crt").exists() else True)


def access_token():
    need = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        print(json.dumps({"uploaded": False, "reason": "credentials missing", "missing": missing}))
        sys.exit(2)
    r = requests.post(TOKEN_URL, data={
        "client_id": os.environ["YOUTUBE_CLIENT_ID"], "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30, verify=CA)
    r.raise_for_status()
    return r.json()["access_token"]


def upload(video, meta, publish, token):
    body = {
        "snippet": {"title": meta["title"][:100], "description": meta["description"][:5000],
                    "tags": meta.get("tags", [])[:30], "categoryId": meta.get("category_id", "27"),  # 27 = Education
                    "defaultLanguage": "en"},
        "status": {"privacyStatus": "public" if publish else "private", "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(video.stat().st_size)}
    start = requests.post(f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status", headers=headers,
                          data=json.dumps(body), timeout=60, verify=CA)
    start.raise_for_status()
    session = start.headers["Location"]
    with video.open("rb") as f:
        put = requests.put(session, headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"},
                           data=f, timeout=600, verify=CA)
    put.raise_for_status()
    return put.json()


def add_captions(video_id, vtt, token):
    meta = {"snippet": {"videoId": video_id, "language": "en", "name": "English", "isDraft": False}}
    files = {"snippet": (None, json.dumps(meta), "application/json"), "file": (vtt.name, vtt.read_bytes(), "text/vtt")}
    r = requests.post(f"{CAPTIONS_URL}?uploadType=multipart&part=snippet", headers={"Authorization": f"Bearer {token}"},
                      files=files, timeout=120, verify=CA)
    r.raise_for_status()
    return r.json().get("id")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--meta", required=True)
    ap.add_argument("--vtt")
    ap.add_argument("--publish", action="store_true", help="request public; an unverified app is still forced to private")
    a = ap.parse_args()
    video = Path(a.video)
    meta = json.loads(Path(a.meta).read_text())
    token = access_token()
    result = upload(video, meta, a.publish, token)
    out = {"uploaded": True, "video_id": result["id"], "url": f"https://youtu.be/{result['id']}",
           "privacy": result.get("status", {}).get("privacyStatus")}
    vtt = Path(a.vtt) if a.vtt else video.with_suffix(".vtt")
    if vtt.exists():
        try:
            out["caption_id"] = add_captions(result["id"], vtt, token)
        except requests.HTTPError as exc:  # captions are not worth failing the upload
            out["caption_error"] = str(exc)[:200]
    print(json.dumps(out))


if __name__ == "__main__":
    main()
