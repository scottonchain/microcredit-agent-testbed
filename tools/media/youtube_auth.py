#!/usr/bin/env python3
"""One-time consent for the project's YouTube channel; run on the operator's own computer, not in the cloud.

    python3 tools/media/youtube_auth.py --client-id <id> --client-secret <secret>

It opens the browser for the channel's Google account, receives the code on a loopback port, exchanges it
for a refresh token and prints the three values to put in the cloud environment's secrets as
YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN. Nothing is written to disk. The scopes are
upload and captions only; the token cannot read mail, change the account or delete the channel.
Standard library only.
"""
import argparse
import http.server
import json
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl"
AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--client-secret", required=True)
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    state = secrets.token_urlsafe(16)
    redirect = f"http://127.0.0.1:{a.port}/"
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Consent received. You can close this tab.")

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", a.port), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    url = AUTH + "?" + urllib.parse.urlencode({
        "client_id": a.client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent", "state": state})
    print("Open this URL in the browser that is signed in to the channel's account:\n", url)
    webbrowser.open(url)
    while "code" not in got and "error" not in got:
        threading.Event().wait(0.5)
    if got.get("state") != state or "error" in got:
        raise SystemExit(f"consent failed: {got.get('error', 'state mismatch')}")
    data = urllib.parse.urlencode({"code": got["code"], "client_id": a.client_id, "client_secret": a.client_secret,
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN, data=data)) as r:
        tok = json.load(r)
    if "refresh_token" not in tok:
        raise SystemExit("no refresh token returned; revoke the app at myaccount.google.com/permissions and run again")
    print("\nPut these in the cloud environment's secrets (never in chat or a file):")
    print(f"YOUTUBE_CLIENT_ID={a.client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={a.client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={tok['refresh_token']}")


if __name__ == "__main__":
    main()
