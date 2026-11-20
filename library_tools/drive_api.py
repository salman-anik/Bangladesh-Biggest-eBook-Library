"""Minimal, dependency-free Google Drive v3 client used by the library tools.

Auth: reads the OAuth JSON (client_id, client_secret, refresh_token) from the
GDRIVE_OAUTH_JSON environment variable (a GitHub Actions secret). Nothing is
ever written to disk or logged.
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

API = "https://www.googleapis.com/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
SHORTCUT = "application/vnd.google-apps.shortcut"

_lock = threading.Lock()
_token: str | None = None
_expiry = 0.0


def _access_token() -> str:
    global _token, _expiry
    with _lock:
        if _token and time.time() < _expiry - 120:
            return _token
        raw = os.environ.get("GDRIVE_OAUTH_JSON", "").strip()
        if not raw:
            raise RuntimeError("GDRIVE_OAUTH_JSON is not set")
        creds = json.loads(raw)
        if "installed" in creds:  # tolerate client-secret style wrappers
            creds = {**creds["installed"], **{k: v for k, v in creds.items() if k != "installed"}}
        body = urllib.parse.urlencode({
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
        }).encode()
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read())
        _token = tok["access_token"]
        _expiry = time.time() + float(tok.get("expires_in", 3600))
        return _token


def request(method: str, path: str, params: dict | None = None, body: dict | None = None,
            raw: bool = False, headers: dict | None = None, retries: int = 8) -> Any:
    url = path if path.startswith("http") else API + path
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        h = {"Authorization": f"Bearer {_access_token()}"}
        if data is not None:
            h["Content-Type"] = "application/json; charset=utf-8"
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = r.read()
                if raw:
                    return payload
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            msg = e.read()[:500].decode("utf-8", "replace")
            retryable = e.code in (408, 429, 500, 502, 503, 504) or (
                e.code == 403 and ("rateLimit" in msg or "userRateLimitExceeded" in msg))
            if e.code == 401:
                global _token
                _token = None
                retryable = True
            if not retryable or attempt == retries - 1:
                raise RuntimeError(f"Drive API {method} {path} -> {e.code}: {msg}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                raise
        time.sleep(min(64, 2 ** attempt) + random.random())
    raise RuntimeError("unreachable")


FILE_FIELDS = ("id,name,mimeType,parents,size,md5Checksum,createdTime,modifiedTime,"
               "description,appProperties,shortcutDetails,trashed,ownedByMe,webViewLink")


def list_all(q: str = "trashed = false", fields: str = FILE_FIELDS) -> Iterator[dict]:
    token = None
    while True:
        params = {"q": q, "pageSize": 1000, "fields": f"nextPageToken,files({fields})",
                  "includeItemsFromAllDrives": "true", "supportsAllDrives": "true",
                  "spaces": "drive"}
        if token:
            params["pageToken"] = token
        res = request("GET", "/files", params)
        yield from res.get("files", [])
        token = res.get("nextPageToken")
        if not token:
            return


def get(file_id: str, fields: str = FILE_FIELDS) -> dict:
    return request("GET", f"/files/{file_id}", {"fields": fields, "supportsAllDrives": "true"})


def download_range(file_id: str, start: int = 0, end: int | None = None) -> bytes:
    rng = f"bytes={start}-{'' if end is None else end}"
    return request("GET", f"/files/{file_id}", {"alt": "media", "supportsAllDrives": "true"},
                   raw=True, headers={"Range": rng})


# ---- mutations (only used by apply-mode tools, never by the audit) ----

def rename(file_id: str, new_name: str) -> dict:
    return request("PATCH", f"/files/{file_id}", {"fields": "id,name,parents", "supportsAllDrives": "true"},
                   body={"name": new_name})


def move(file_id: str, add_parent: str, remove_parent: str) -> dict:
    return request("PATCH", f"/files/{file_id}", {"addParents": add_parent, "removeParents": remove_parent,
                                                  "fields": "id,name,parents", "supportsAllDrives": "true"},
                   body={})


def mkdir(name: str, parent: str) -> dict:
    return request("POST", "/files", {"fields": "id,name,parents", "supportsAllDrives": "true"},
                   body={"name": name, "mimeType": FOLDER, "parents": [parent]})


def shortcut(target_id: str, parent: str, name: str) -> dict:
    return request("POST", "/files", {"fields": "id,name,parents", "supportsAllDrives": "true"},
                   body={"name": name, "mimeType": SHORTCUT, "parents": [parent],
                         "shortcutDetails": {"targetId": target_id}})
