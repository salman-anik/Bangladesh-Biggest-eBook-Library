#!/usr/bin/env python3
"""Collect books from user-provided Google Drive folders, shortlinks, and Bangla/English
book websites, copy/upload to Google Drive using GDRIVE_OAUTH_JSON, and register in
data/merged_books.json for GitHub repo rebuild.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html as html_lib
import json
import os
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TMP_DIR = ROOT / "tmp_extra_sources"
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import clean_classifier as cc  # noqa: E402

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

BOOK_EXTS = (".pdf", ".epub", ".djvu", ".mobi", ".azw3")

SEED_DRIVE_FOLDERS: list[tuple[str, str]] = [
    ("14TJVDcNMQVyVGcQNsmTB3cI0V2XFCMqV", "Islamic"),
    ("1dgkfYgaG9HksnFL1MWyTH8ivwPb8CFev", "Islamic Collection 2"),
    ("1UKFuuVN8bJ92gpHov_ZbKPOASJUEmHj6", "Kindle Books"),
    ("1-6tRHRU79tAH2_n-h6TrqJwLdkTs07P3", "BD Public e-Library"),
    ("1pHTZqxaYvsjgU2YsI6MrRIKHooziCUCP", "Kindle & Bangla Collection"),
    ("1FAukxq7IzhUgqKA9VRxShObg_Nip_V2G", "Pinu's Kindle"),
]

SHORTLINKS_TO_RESOLVE: list[str] = [
    "https://bit.ly/2G38CT4",
    "https://bit.ly/2Soy6QP",
    "https://bit.ly/2ThxRoE",
    "https://bit.ly/2lnf3Vq",
    "https://bit.ly/2B4VGZG",
    "https://bit.ly/2wgsSLh",
    "https://bit.ly/2FUGXVm",
    "https://bit.ly/2DFBKON",
    "https://is.gd/4rGKYj",
    "https://cutt.ly/8zH0G6s",
    "https://cutt.ly/lzH1pPr",
    "https://cutt.ly/3zH03i2",
    "https://cutt.ly/xzHM0Jv",
]

WEB_SEED_PAGES: list[str] = [
    "https://justpaste.it/collectionislamicbd",
    "https://justpaste.it/islamiclinks",
    "https://collectionislamicbd.blogspot.com/2018/09/pdf.html",
    "https://collectionislamicbd.blogspot.com/2018/09/blog-post_46.html",
    "https://bangla-booksdownload.blogspot.com/",
    "https://islamiboi.wordpress.com/",
    "https://islamicbookhouse.wordpress.com/",
    "https://banglakitab.wordpress.com/islamic-book/",
    "https://islamiboipdf.blogspot.com/",
    "https://islamfind.wordpress.com/",
    "http://www.islamicbook.ws/bengali/",
    "http://www.islamicbook.ws/english/",
    "https://www.australianislamiclibrary.org/",
    "http://kalamullah.com/",
    "https://www.muslim-library.com/",
    "https://www.quraneralo.com/category/bangla-islamic-books/",
    "https://i-onlinemedia.net/category/downloads/ebooks",
    "https://sites.google.com/site/almunirabdullah/bangla-books",
]

PROGRESS_FILE = DATA_DIR / "extra_sources_progress.json"
CATALOG_FILE = DATA_DIR / "extra_sources_catalog.json"
MERGED_FILE = DATA_DIR / "merged_books.json"
FOLDERS_FILE = DATA_DIR / "clean_folders.json"

LOCK = threading.Lock()
_TOKEN_LOCK = threading.Lock()
_ACCESS_TOKEN: str | None = None
_TOKEN_EXPIRY: float = 0.0


def _get_drive_access_token() -> str:
    global _ACCESS_TOKEN, _TOKEN_EXPIRY
    oauth_raw = os.environ.get("GDRIVE_OAUTH_JSON", "").strip()
    if not oauth_raw:
        raise RuntimeError("Missing GDRIVE_OAUTH_JSON secret")

    with _TOKEN_LOCK:
        if _ACCESS_TOKEN and time.time() < _TOKEN_EXPIRY - 60:
            return _ACCESS_TOKEN

        creds = json.loads(oauth_raw)
        body = urllib.parse.urlencode(
            {
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            tok = json.loads(resp.read().decode("utf-8"))
        _ACCESS_TOKEN = tok["access_token"]
        _TOKEN_EXPIRY = time.time() + float(tok.get("expires_in", 3600))
        return _ACCESS_TOKEN


def _drive_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    for attempt in range(5):
        try:
            token = _get_drive_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            data = None
            if payload is not None:
                headers["Content-Type"] = "application/json"
                data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception:
            if attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError(f"Drive API failed: {url}")


def drive_list_folder(folder_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token = ""
    while True:
        q = urllib.parse.quote(f"'{folder_id}' in parents and trashed = false")
        fields = urllib.parse.quote("nextPageToken, files(id, name, mimeType, size)")
        url = (
            f"https://www.googleapis.com/drive/v3/files?q={q}&fields={fields}"
            f"&pageSize=1000&supportsAllDrives=true&includeItemsFromAllDrives=true"
        )
        if page_token:
            url += f"&pageToken={urllib.parse.quote(page_token)}"
        res = _drive_json(url)
        items.extend(res.get("files", []))
        page_token = res.get("nextPageToken", "")
        if not page_token:
            break
    return items


def drive_mkdir(name: str, parent_id: str) -> str:
    res = _drive_json(
        "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id",
        method="POST",
        payload={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
    )
    return res["id"]


def drive_copy(source_id: str, name: str, parent_id: str) -> str:
    res = _drive_json(
        f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(source_id)}/copy?supportsAllDrives=true&fields=id",
        method="POST",
        payload={"name": name, "parents": [parent_id]},
    )
    return res["id"]


def drive_upload_pdf(local_path: Path, parent_id: str) -> str:
    size = local_path.stat().st_size
    for attempt in range(4):
        try:
            token = _get_drive_access_token()
            init_req = urllib.request.Request(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true&fields=id",
                data=json.dumps({"name": local_path.name, "parents": [parent_id]}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "application/pdf",
                    "X-Upload-Content-Length": str(size),
                },
                method="POST",
            )
            with urllib.request.urlopen(init_req, timeout=30) as resp:
                upload_url = resp.headers["Location"]
            data = local_path.read_bytes()
            put_req = urllib.request.Request(
                upload_url,
                data=data,
                headers={"Content-Type": "application/pdf", "Content-Length": str(len(data))},
                method="PUT",
            )
            with urllib.request.urlopen(put_req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))["id"]
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Upload failed: {local_path.name}")


def http_get_lenient(url: str, timeout: int = 25) -> tuple[str, str]:
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.geturl(), resp.read().decode("utf-8", "ignore")


def norm_title(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\.(pdf|epub|djvu|mobi|azw3)$", "", s)
    s = re.sub(r"\b(pdf|download|free|ebook|book)\b", " ", s)
    s = re.sub(r"[^a-z0-9\u0980-\u09ff]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_book_name(raw: str) -> str:
    s = html_lib.unescape(urllib.parse.unquote(raw or "")).strip()
    s = re.sub(r"\.(pdf|epub|djvu|mobi|azw3)$", "", s, flags=re.I)
    s = re.sub(r'[<>:"/\\|?*\r\n\t]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    return (s[:120].strip() if len(s) > 120 else s) or "Untitled Book"


def classify_book(title: str, source_path: str, clean_folders: dict[str, str]) -> str:
    leaf = cc.classify_clean_leaf(title=title, source_path=source_path)
    if leaf in clean_folders:
        return leaf
    top = leaf.split("/")[0]
    if top in clean_folders:
        return top
    return "Religion/Islam/Islamic Lifestyle" if "Religion/Islam/Islamic Lifestyle" in clean_folders else "Reference Books/Encyclopedia"


def build_catalog() -> list[dict[str, Any]]:
    if CATALOG_FILE.exists():
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        if data:
            return data

    discovered_folders: dict[str, str] = {fid: label for fid, label in SEED_DRIVE_FOLDERS}
    discovered_drive_files: dict[str, dict[str, Any]] = {}
    discovered_web_pdfs: dict[str, dict[str, Any]] = {}

    # 1. Resolve shortlinks
    for u in SHORTLINKS_TO_RESOLVE:
        try:
            final_url, body = http_get_lenient(u, timeout=15)
            for m in re.finditer(r"drive\.google\.com/(?:drive/folders/|folderview\?id=)([A-Za-z0-9_-]{15,})", final_url + "\n" + body):
                discovered_folders.setdefault(m.group(1), u)
            for m in re.finditer(r"drive\.google\.com/(?:file/d/|open\?id=)([A-Za-z0-9_-]{15,})", final_url + "\n" + body):
                discovered_drive_files.setdefault(m.group(1), {"kind": "drive_file", "id": m.group(1), "name": m.group(1), "source": u})
        except Exception:
            pass

    # 2. Crawl web seed pages for PDFs and Drive links
    for page_url in WEB_SEED_PAGES:
        try:
            final_url, body = http_get_lenient(page_url, timeout=20)
            for m in re.finditer(r"drive\.google\.com/(?:drive/folders/|folderview\?id=)([A-Za-z0-9_-]{15,})", body):
                discovered_folders.setdefault(m.group(1), final_url)
            for m in re.finditer(r"drive\.google\.com/(?:file/d/|open\?id=)([A-Za-z0-9_-]{15,})", body):
                discovered_drive_files.setdefault(m.group(1), {"kind": "drive_file", "id": m.group(1), "name": m.group(1), "source": final_url})
            for href in re.findall(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', body, re.I):
                full = urllib.parse.urljoin(final_url, href)
                fname = clean_book_name(Path(urllib.parse.urlparse(full).path).name)
                discovered_web_pdfs.setdefault(full, {"kind": "web_pdf", "id": full, "url": full, "name": fname, "source": final_url})
        except Exception:
            pass

    # 3. Recursively walk all discovered Google Drive folders
    visited_folders: set[str] = set()
    queue: list[tuple[str, str]] = list(discovered_folders.items())
    while queue:
        fid, path_hint = queue.pop(0)
        if fid in visited_folders:
            continue
        visited_folders.add(fid)
        try:
            children = drive_list_folder(fid)
        except Exception as e:
            print(f"Skipping inaccessible folder {fid} ({path_hint}): {e}", flush=True)
            continue
        for ch in children:
            mime = ch.get("mimeType", "")
            name = ch.get("name", "")
            if mime == "application/vnd.google-apps.folder":
                queue.append((ch["id"], f"{path_hint}/{name}"))
            elif name.lower().endswith(BOOK_EXTS) or "pdf" in mime.lower() or "epub" in mime.lower():
                discovered_drive_files[ch["id"]] = {
                    "kind": "drive_file",
                    "id": ch["id"],
                    "name": name,
                    "size": int(ch.get("size") or 0),
                    "mimeType": mime or "application/pdf",
                    "source": path_hint,
                }

    catalog = list(discovered_drive_files.values()) + list(discovered_web_pdfs.values())
    CATALOG_FILE.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Catalog built: {len(discovered_drive_files)} Drive files + {len(discovered_web_pdfs)} Web PDFs = {len(catalog)} total", flush=True)
    return catalog


def process_one(item: dict[str, Any], clean_folders: dict[str, str], existing_norms: set[str], existing_fids: set[str], deadline: float | None) -> tuple[str, str]:
    if deadline and time.time() > deadline:
        return "time_limit", item["id"]

    key = item["id"]
    if item["kind"] == "drive_file" and key in existing_fids:
        return "skipped_dup", key

    clean_name = clean_book_name(item.get("name") or key)
    if norm_title(clean_name) in existing_norms:
        return "skipped_dup", key

    leaf_path = classify_book(clean_name, item.get("source", ""), clean_folders)
    parent_folder_id = clean_folders[leaf_path]
    top_cat, leaf_cat = leaf_path.split("/", 1)[0], leaf_path.split("/")[-1]

    if item["kind"] == "drive_file":
        orig_name = item.get("name") or f"{clean_name}.pdf"
        ext = os.path.splitext(orig_name)[1] or ".pdf"
        book_folder_id = drive_mkdir(clean_name, parent_folder_id)
        copied_id = drive_copy(key, f"{clean_name}{ext}", book_folder_id)
        size_bytes = int(item.get("size") or 0)
        mime = item.get("mimeType") or "application/pdf"
    else:
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        tmp_pdf = TMP_DIR / f"{clean_name}.pdf"
        try:
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(item["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180, context=ctx) as resp, open(tmp_pdf, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
            size_bytes = tmp_pdf.stat().st_size
            if size_bytes < 1024:
                return "error_small", key
            book_folder_id = drive_mkdir(clean_name, parent_folder_id)
            copied_id = drive_upload_pdf(tmp_pdf, book_folder_id)
            ext = ".pdf"
            mime = "application/pdf"
        finally:
            if tmp_pdf.exists():
                try:
                    tmp_pdf.unlink()
                except Exception:
                    pass

    fmt = ext.lstrip(".").upper() or "PDF"
    rec = {
        "folder_id": book_folder_id,
        "folder_link": f"https://drive.google.com/drive/folders/{book_folder_id}",
        "file_id": copied_id,
        "link": f"https://drive.google.com/drive/folders/{book_folder_id}",
        "name": clean_name,
        "title": clean_name,
        "author": "Various / Unknown",
        "publication": item.get("source", "Extra Collection"),
        "top_category": top_cat,
        "leaf_path": leaf_path,
        "leaf_category": leaf_cat,
        "size": size_bytes,
        "pdf_file_id": copied_id if fmt == "PDF" else "",
        "epub_file_id": copied_id if fmt == "EPUB" else "",
        "text_file_id": "",
        "cover_file_id": "",
        "cover_url": "",
        "thumbnail_url": "",
        "book_url": item.get("url", ""),
        "formats": [fmt],
        "files": [{"id": copied_id, "name": f"{clean_name}{ext}", "size": size_bytes, "mimeType": mime}],
        "subfolder": None,
        "source": "extra_sources",
    }

    with LOCK:
        prog = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
        prog[key] = rec
        PROGRESS_FILE.write_text(json.dumps(prog, ensure_ascii=False, indent=2), encoding="utf-8")

    return "added", clean_name


def merge_into_catalog() -> int:
    if not PROGRESS_FILE.exists():
        return 0
    prog = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    merged = json.loads(MERGED_FILE.read_text(encoding="utf-8"))
    existing_fids = {b["folder_id"] for b in merged if b.get("folder_id")}
    added = 0
    for rec in prog.values():
        if isinstance(rec, dict) and rec.get("folder_id") and rec["folder_id"] not in existing_fids:
            merged.append(rec)
            existing_fids.add(rec["folder_id"])
            added += 1
    if added:
        MERGED_FILE.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    return added


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--max-minutes", type=int, default=300)
    parser.add_argument("--merge-only", action="store_true")
    args = parser.parse_args()

    if args.merge_only:
        print(f"Merged {merge_into_catalog()} new books into merged_books.json")
        return

    clean_folders = json.loads(FOLDERS_FILE.read_text(encoding="utf-8"))
    merged = json.loads(MERGED_FILE.read_text(encoding="utf-8"))
    existing_norms = {norm_title(b[k]) for b in merged for k in ("name", "title", "english_name") if b.get(k)}
    existing_fids = {b["file_id"] for b in merged if b.get("file_id")}

    progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
    catalog = build_catalog()
    todo = [it for it in catalog if it["id"] not in progress]
    if args.limit > 0:
        todo = todo[: args.limit]

    print(f"Extra Catalog: {len(catalog)} | Processed: {len(progress)} | Todo: {len(todo)}", flush=True)
    if not todo:
        print(f"Nothing left. Merged {merge_into_catalog()} books.")
        return

    deadline = (time.time() + args.max_minutes * 60) if args.max_minutes > 0 else None
    stats = {"added": 0, "skipped_dup": 0, "error": 0, "time_limit": 0}
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_one, it, clean_folders, existing_norms, existing_fids, deadline): it for it in todo}
        for f in concurrent.futures.as_completed(futs):
            it = futs[f]
            done += 1
            try:
                status, info = f.result()
                if status == "added":
                    stats["added"] += 1
                elif status == "skipped_dup":
                    stats["skipped_dup"] += 1
                    with LOCK:
                        prog = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
                        prog[it["id"]] = {"status": "skipped_dup"}
                        PROGRESS_FILE.write_text(json.dumps(prog, ensure_ascii=False, indent=2), encoding="utf-8")
                elif status == "time_limit":
                    stats["time_limit"] += 1
                else:
                    stats["error"] += 1
            except Exception as e:
                stats["error"] += 1
                print(f"[{done}/{len(todo)}] EXCEPTION {it['id']}: {e}", flush=True)
            if done % 25 == 0 or done == len(todo):
                print(f"Progress: {done}/{len(todo)} | {stats}", flush=True)

    print(f"Done! {stats} | Merged {merge_into_catalog()} new books into merged_books.json")


if __name__ == "__main__":
    main()
