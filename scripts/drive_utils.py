#!/usr/bin/env python3
"""
Lightweight, zero-external-dependency Google Drive v3 helpers & rollback-capable
changelog writers shared by AnaBook organization scripts.
"""
from __future__ import annotations

import collections
import concurrent.futures
import csv
import datetime as dt
import io
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT_ID = os.environ.get("LIBRARY_ROOT_ID", "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq")
DRIVE_REPORTS_FOLDER_ID = os.environ.get("DRIVE_REPORTS_FOLDER_ID", "1jdKRqfUfxyv78EfCZnv8A_CTQnDN_Lp_")
DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
FOLDER_MIME = "application/vnd.google-apps.folder"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"
SKIP_TOP_FOLDERS = {"Library Management"}
BOOK_EXTS = {".pdf", ".epub", ".mobi", ".azw", ".azw3", ".djvu", ".txt", ".doc", ".docx", ".rtf"}
INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

_tok_lock = threading.Lock()
_tok_val: str | None = None
_tok_exp = 0.0


def get_access_token() -> str:
    global _tok_val, _tok_exp
    with _tok_lock:
        if _tok_val and time.time() < _tok_exp - 120:
            return _tok_val
        raw = os.environ.get("GDRIVE_OAUTH_JSON", "").strip()
        if not raw:
            raise RuntimeError("GDRIVE_OAUTH_JSON environment variable is not set.")
        creds = json.loads(raw)
        if "installed" in creds:
            creds = {**creds["installed"], **{k: v for k, v in creds.items() if k != "installed"}}
        body = urllib.parse.urlencode(
            {
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type": "refresh_token",
            }
        ).encode()
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        _tok_val = data["access_token"]
        _tok_exp = time.time() + float(data.get("expires_in", 3600))
        return _tok_val


def drive_request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    raw_bytes: bytes | None = None,
    content_type: str = "application/json; charset=utf-8",
    raw: bool = False,
    timeout: int = 90,
    retries: int = 8,
) -> Any:
    url = path if path.startswith("http") else f"{DRIVE_API}{path}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    payload = raw_bytes if raw_bytes is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    for attempt in range(retries):
        headers = {"Authorization": f"Bearer {get_access_token()}"}
        if payload is not None:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                return data if raw else (json.loads(data) if data else {})
        except urllib.error.HTTPError as e:
            msg = e.read()[:400].decode("utf-8", "replace")
            if e.code == 401:
                global _tok_val
                with _tok_lock:
                    _tok_val = None
            retryable = e.code in (401, 408, 429, 500, 502, 503, 504) or (
                e.code == 403 and any(k in msg for k in ("rateLimit", "userRateLimitExceeded", "quotaExceeded"))
            )
            if not retryable or attempt == retries - 1:
                raise RuntimeError(f"Drive API {method} {path} -> {e.code}: {msg}") from None
            time.sleep(min(1.5 * (2**attempt), 24))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(min(2**attempt, 12))


def list_children(folder_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(id, name, mimeType, size, md5Checksum, parents, thumbnailLink, modifiedTime, shortcutDetails)",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token
        res = drive_request("GET", "/files", params=params)
        items.extend(res.get("files", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return items


def resolve_folder_path(target_path: str, root_id: str = ROOT_ID) -> tuple[str, str]:
    cleaned = target_path.strip().strip("/")
    if not cleaned or cleaned.upper() == "ALL":
        return root_id, ""
    cur_id = root_id
    parts = [p.strip() for p in cleaned.split("/") if p.strip()]
    resolved: list[str] = []
    for part in parts:
        children = list_children(cur_id)
        match = next(
            (c for c in children if c.get("mimeType") == FOLDER_MIME and c.get("name", "").lower() == part.lower()),
            None,
        )
        if not match:
            raise RuntimeError(f"Subfolder '{part}' not found inside '{'/'.join(resolved) or 'ROOT'}'.")
        cur_id = match["id"]
        resolved.append(match["name"])
    return cur_id, "/".join(resolved)


def walk_drive_tree(
    root_id: str = ROOT_ID,
    base_prefix: str = "",
    skip_top_folders: set[str] | None = None,
    max_workers: int = 8,
) -> dict[str, Any]:
    """
    Fast parallel BFS across Google Drive folders.
    Returns folders_by_id, folders_by_path, children_by_folder, files (real non-folder, non-shortcut),
    shortcuts (existing Drive shortcuts with shortcutDetails), and book_files.
    """
    skip = SKIP_TOP_FOLDERS if skip_top_folders is None else skip_top_folders
    folders_by_id: dict[str, dict[str, Any]] = {
        root_id: {"id": root_id, "name": base_prefix or "ROOT", "path": base_prefix, "parent_id": ""}
    }
    folders_by_path: dict[str, str] = {base_prefix: root_id}
    children_by_folder: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    files: list[dict[str, Any]] = []
    shortcuts: list[dict[str, Any]] = []

    frontier: list[tuple[str, str]] = [(root_id, base_prefix)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        while frontier:
            fut_map = {pool.submit(list_children, fid): (fid, path) for fid, path in frontier}
            next_frontier: list[tuple[str, str]] = []
            for fut in concurrent.futures.as_completed(fut_map):
                fid, fpath = fut_map[fut]
                items = fut.result()
                children_by_folder[fid] = items
                for it in items:
                    name = it.get("name", "")
                    mime = it.get("mimeType", "")
                    sub_path = f"{fpath}/{name}" if fpath else name
                    if mime == FOLDER_MIME:
                        if not fpath and name in skip:
                            continue
                        folders_by_id[it["id"]] = {
                            "id": it["id"],
                            "name": name,
                            "path": sub_path,
                            "parent_id": fid,
                        }
                        folders_by_path[sub_path] = it["id"]
                        next_frontier.append((it["id"], sub_path))
                    elif mime == SHORTCUT_MIME:
                        sd = it.get("shortcutDetails") or {}
                        shortcuts.append(
                            {
                                "id": it["id"],
                                "name": name,
                                "parent_id": fid,
                                "folder": fpath,
                                "target_id": sd.get("targetId", ""),
                                "target_mime": sd.get("targetMimeType", ""),
                            }
                        )
                    else:
                        ext = os.path.splitext(name)[1].lower()
                        files.append(
                            {
                                "id": it["id"],
                                "name": name,
                                "ext": ext,
                                "mimeType": mime,
                                "size": int(it.get("size") or 0),
                                "md5": it.get("md5Checksum", ""),
                                "parent_id": fid,
                                "folder": fpath,
                                "thumbnailLink": it.get("thumbnailLink", ""),
                            }
                        )
            frontier = next_frontier

    return {
        "folders_by_id": folders_by_id,
        "folders_by_path": folders_by_path,
        "children_by_folder": dict(children_by_folder),
        "files": files,
        "shortcuts": shortcuts,
    }


def upsert_drive_text_file(parent_id: str, filename: str, content_bytes: bytes, mime_type: str) -> str:
    existing = list_children(parent_id)
    match = next(
        (c for c in existing if c.get("mimeType") != FOLDER_MIME and c.get("name", "").lower() == filename.lower()),
        None,
    )
    if match:
        res = drive_request(
            "PATCH",
            f"{DRIVE_UPLOAD_API}/files/{match['id']}",
            params={"uploadType": "media", "supportsAllDrives": "true", "fields": "id,name"},
            raw_bytes=content_bytes,
            content_type=mime_type,
        )
        return res["id"]

    boundary = f"----AnaBookBoundary{int(time.time() * 1000)}"
    meta_bytes = json.dumps({"name": filename, "parents": [parent_id]}).encode("utf-8")
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode("utf-8")
        + meta_bytes
        + f"\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n".encode("utf-8")
        + content_bytes
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )
    res = drive_request(
        "POST",
        f"{DRIVE_UPLOAD_API}/files",
        params={"uploadType": "multipart", "supportsAllDrives": "true", "fields": "id,name"},
        raw_bytes=body,
        content_type=f"multipart/related; boundary={boundary}",
    )
    return res["id"]


def make_batch_id(applied_at: str, prefix: str = "batch") -> str:
    try:
        parsed = dt.datetime.fromisoformat(applied_at.replace("Z", "+00:00"))
        stamp = parsed.strftime("%Y%m%d_%H%M%S")
    except Exception:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}"


def update_rename_changelog(
    repo_dir: Path,
    new_entries: list[dict[str, Any]],
    applied_at: str,
    sync_drive: bool = True,
    batch_id: str | None = None,
    default_action: str = "rename",
) -> dict[str, Any]:
    reports_dir = repo_dir / "Library Management" / "Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "rename_changelog.json"
    csv_path = reports_dir / "rename_changelog.csv"
    md_path = reports_dir / "RENAME_CHANGELOG.md"

    existing: list[dict[str, Any]] = []
    if json_path.exists():
        try:
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        except Exception:
            existing = []

    batch_tag = batch_id or make_batch_id(applied_at)

    def _norm_key(item: dict[str, Any]) -> tuple[str, ...]:
        return (
            str(item.get("batch_id") or ""),
            str(item.get("action") or "rename"),
            str(item.get("id") or ""),
            str(item.get("old_parent_id") or ""),
            str(item.get("new_parent_id") or ""),
            str(item.get("old_name") or ""),
            str(item.get("new_name") or ""),
        )

    seen = {_norm_key(item) for item in existing}
    added = 0
    for e in new_entries:
        act = e.get("action") or default_action
        old_p = e.get("old_parent_id") or e.get("parentId") or ""
        new_p = e.get("new_parent_id") or e.get("parentId") or old_p
        url = e.get("drive_url") or (
            f"https://drive.google.com/drive/folders/{e['id']}"
            if act == "create_folder"
            else f"https://drive.google.com/file/d/{e['id']}/view"
        )
        record = {
            "batch_id": e.get("batch_id") or batch_tag,
            "timestamp": e.get("timestamp") or applied_at,
            "action": act,
            "id": e["id"],
            "folder": e.get("folder", ""),
            "old_parent_id": old_p,
            "new_parent_id": new_p,
            "old_name": e.get("old_name", ""),
            "new_name": e.get("new_name", ""),
            "category": e.get("category", ""),
            "drive_url": url,
        }
        key = _norm_key(record)
        if key in seen:
            continue
        seen.add(key)
        existing.append(record)
        added += 1

    json_text = json.dumps(existing, ensure_ascii=False, indent=2) + "\n"
    json_path.write_text(json_text, encoding="utf-8")

    csv_buf = io.StringIO()
    w = csv.writer(csv_buf)
    w.writerow(
        [
            "Batch ID",
            "Timestamp (UTC)",
            "Action",
            "File ID",
            "Folder",
            "Old Parent ID",
            "New Parent ID",
            "Previous Filename",
            "New Filename",
            "Category",
            "Drive Link",
        ]
    )
    for item in existing:
        w.writerow(
            [
                item.get("batch_id", ""),
                item.get("timestamp", ""),
                item.get("action", "rename"),
                item.get("id", ""),
                item.get("folder", ""),
                item.get("old_parent_id", ""),
                item.get("new_parent_id", ""),
                item.get("old_name", ""),
                item.get("new_name", ""),
                item.get("category", ""),
                item.get("drive_url", ""),
            ]
        )
    csv_bytes = csv_buf.getvalue().encode("utf-8-sig")
    csv_path.write_bytes(csv_bytes)

    def _esc(s: str) -> str:
        return (s or "").replace("|", "\\|").replace("\n", " ")

    md_lines = [
        "# Library Drive Change & Rename Changelog",
        "",
        "[🏠 Library Home](../../README.md) / [Library Management](../README.md) / [Reports](README.md) / **Rename Changelog**",
        "",
        f"> Versioned, rollback-capable audit log preserving every original filename & folder parent ID before changes on Google Drive. Revert any batch with `python scripts/rollback_drive_changes.py --batch <BATCH_ID> --apply`. Machine-readable copies: [rename_changelog.csv](rename_changelog.csv) · [rename_changelog.json](rename_changelog.json)",
        "",
        f"- **Last Updated (UTC):** `{applied_at}`",
        f"- **Total Drive Changes Recorded:** `{len(existing)}`",
        "",
        "| Batch ID | Timestamp (UTC) | Action | Folder | Previous Filename | New Filename | Category | File Link |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in existing:
        fid = item.get("id", "")
        url = item.get("drive_url") or f"https://drive.google.com/file/d/{fid}/view"
        md_lines.append(
            f"| `{_esc(item.get('batch_id', ''))}` | `{_esc(item.get('timestamp', ''))}` | `{_esc(item.get('action', 'rename'))}` | `{_esc(item.get('folder', ''))}` | {_esc(item.get('old_name', ''))} | {_esc(item.get('new_name', ''))} | {_esc(item.get('category', ''))} | [Open on Drive]({url}) |"
        )
    md_text = "\n".join(md_lines) + "\n"
    md_path.write_text(md_text, encoding="utf-8")

    drive_ids: dict[str, str] = {}
    if sync_drive and DRIVE_REPORTS_FOLDER_ID:
        for fname, data_bytes, mime in (
            ("rename_changelog.json", json_text.encode("utf-8"), "application/json; charset=utf-8"),
            ("rename_changelog.csv", csv_bytes, "text/csv; charset=utf-8"),
            ("RENAME_CHANGELOG.md", md_text.encode("utf-8"), "text/markdown; charset=utf-8"),
        ):
            try:
                drive_ids[fname] = upsert_drive_text_file(DRIVE_REPORTS_FOLDER_ID, fname, data_bytes, mime)
            except Exception as exc:
                print(f"[Changelog] Warning: failed to sync {fname} to Drive: {exc}", flush=True)

    return {
        "batch_id": batch_tag,
        "total_entries": len(existing),
        "added_entries": added,
        "drive_synced_files": drive_ids,
    }


def sanitize_filename(stem: str, ext: str) -> str:
    clean = INVALID_FS_CHARS.sub(" ", stem)
    clean = re.sub(r"\s+", " ", clean).strip(" ._-")
    if not clean:
        clean = "Untitled Book"
    if len(clean) > 165:
        clean = clean[:165].rsplit(" ", 1)[0].strip()
    return f"{clean}{ext}"


def find_or_create_folder(
    parent_id: str,
    name: str,
    existing_children: list[dict[str, Any]] | None = None,
    parent_path: str = "",
) -> tuple[dict[str, Any], bool]:
    """Return (folder_meta, created_bool). Never creates duplicate folders."""
    children = existing_children if existing_children is not None else list_children(parent_id)
    match = next(
        (c for c in children if c.get("mimeType") == FOLDER_MIME and c.get("name", "").strip().lower() == name.strip().lower()),
        None,
    )
    if match:
        return match, False
    created = drive_request(
        "POST",
        "/files",
        params={"supportsAllDrives": "true", "fields": "id,name,mimeType,parents"},
        body={"name": name.strip(), "mimeType": FOLDER_MIME, "parents": [parent_id]},
    )
    if existing_children is not None:
        existing_children.append(created)
    return created, True
