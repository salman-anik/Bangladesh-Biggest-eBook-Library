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
from pathlib import Path
from typing import Any, Iterator

API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
SHORTCUT = "application/vnd.google-apps.shortcut"
CHUNK_SIZE = 8 * 1024 * 1024

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
            raw: bool = False, headers: dict | None = None, retries: int = 10) -> Any:
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
                e.code == 403 and any(k in msg for k in ("rateLimit", "userRateLimitExceeded", "quotaExceeded", "sharingRateLimitExceeded")))
            if e.code == 401:
                global _token
                _token = None
                retryable = True
            if not retryable or attempt == retries - 1:
                raise RuntimeError(f"Drive API {method} {path} -> {e.code}: {msg}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                raise
        time.sleep(min(64, 1.5 * (2 ** attempt)) + random.uniform(0, 1.5))
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


def download_full(file_id: str) -> bytes:
    return request("GET", f"/files/{file_id}", {"alt": "media", "supportsAllDrives": "true"},
                   raw=True)


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


def move_and_rename(
    file_id: str,
    new_name: str | None = None,
    add_parent: str | None = None,
    remove_parent: str | None = None,
) -> dict:
    params: dict[str, str] = {"fields": "id,name,parents", "supportsAllDrives": "true"}
    if add_parent and remove_parent and add_parent != remove_parent:
        params["addParents"] = add_parent
        params["removeParents"] = remove_parent
    body = {"name": new_name} if new_name is not None else {}
    return request("PATCH", f"/files/{file_id}", params, body=body)


def trash(file_id: str) -> dict:
    """Reversible move-to-trash (never permanently deletes)."""
    return request("PATCH", f"/files/{file_id}", {"fields": "id,name,trashed", "supportsAllDrives": "true"},
                   body={"trashed": True})


def _resumable_put(init_method: str, init_url: str, metadata: dict, local_path: Path, mime_type: str, retries: int = 8) -> dict:
    size = local_path.stat().st_size
    for attempt in range(retries):
        try:
            init_headers = {
                "Authorization": f"Bearer {_access_token()}",
                "Content-Type": "application/json; charset=utf-8",
                "X-Upload-Content-Type": mime_type,
                "X-Upload-Content-Length": str(size),
            }
            init_req = urllib.request.Request(
                init_url,
                data=json.dumps(metadata).encode("utf-8"),
                headers=init_headers,
                method=init_method,
            )
            with urllib.request.urlopen(init_req, timeout=60) as resp:
                session_url = resp.headers["Location"]

            if size == 0:
                put_req = urllib.request.Request(
                    session_url,
                    data=b"",
                    headers={"Content-Type": mime_type, "Content-Length": "0"},
                    method="PUT",
                )
                with urllib.request.urlopen(put_req, timeout=120) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            with open(local_path, "rb") as fh:
                offset = 0
                while offset < size:
                    chunk = fh.read(CHUNK_SIZE)
                    end = offset + len(chunk) - 1
                    put_req = urllib.request.Request(
                        session_url,
                        data=chunk,
                        headers={
                            "Content-Type": mime_type,
                            "Content-Length": str(len(chunk)),
                            "Content-Range": f"bytes {offset}-{end}/{size}",
                        },
                        method="PUT",
                    )
                    try:
                        with urllib.request.urlopen(put_req, timeout=300) as resp:
                            return json.loads(resp.read().decode("utf-8"))
                    except urllib.error.HTTPError as ce:
                        if ce.code == 308:
                            offset += len(chunk)
                            continue
                        raise
            raise RuntimeError("upload ended without completion response")
        except urllib.error.HTTPError as e:
            msg = e.read()[:400].decode("utf-8", "replace")
            retryable = e.code in (408, 429, 500, 502, 503, 504) or (
                e.code == 403 and any(k in msg for k in ("rateLimit", "userRateLimitExceeded", "quotaExceeded")))
            if e.code == 401:
                global _token
                _token = None
                retryable = True
            if not retryable or attempt == retries - 1:
                raise RuntimeError(f"Drive upload {init_method} {local_path.name} -> {e.code}: {msg}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                raise
        time.sleep(min(64, 1.5 * (2 ** attempt)) + random.uniform(0, 1.5))
    raise RuntimeError("unreachable")


def upload_resumable(local_path: Path, name: str, parent_id: str, mime_type: str = "application/pdf") -> dict:
    init_url = f"{UPLOAD_API}/files?uploadType=resumable&supportsAllDrives=true&fields=id,name,size,md5Checksum,parents"
    return _resumable_put("POST", init_url, {"name": name, "parents": [parent_id]}, local_path, mime_type)


def update_media(file_id: str, local_path: Path, mime_type: str = "application/pdf") -> dict:
    init_url = f"{UPLOAD_API}/files/{file_id}?uploadType=resumable&supportsAllDrives=true&fields=id,name,size,md5Checksum,parents"
    return _resumable_put("PATCH", init_url, {}, local_path, mime_type)
