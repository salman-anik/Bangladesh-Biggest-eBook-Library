#!/usr/bin/env python3
"""Collect books from https://students.bd/books, upload to Google Drive,
and register them in data/merged_books.json for GitHub repo rebuild.

Supports both:
- GitHub Actions / headless mode via GDRIVE_OAUTH_JSON or GDRIVE_SERVICE_ACCOUNT_JSON
- Local mode via `gdrive` CLI
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html as html_lib
import json
import os
import re
import shutil
import subprocess
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
TMP_DIR = ROOT / "tmp_students_bd"
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import clean_classifier as cc  # noqa: E402

GDRIVE = shutil.which("gdrive") or "gdrive"
BASE_URL = "https://students.bd"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

PROGRESS_FILE = DATA_DIR / "students_bd_progress.json"
CATALOG_FILE = DATA_DIR / "students_bd_catalog.json"
MERGED_FILE = DATA_DIR / "merged_books.json"
FOLDERS_FILE = DATA_DIR / "clean_folders.json"

LOCK = threading.Lock()
_TOKEN_LOCK = threading.Lock()
_ACCESS_TOKEN: str | None = None
_TOKEN_EXPIRY: float = 0.0


def _get_drive_access_token() -> str | None:
    """Return a Google Drive OAuth2 access token from env secrets if configured."""
    global _ACCESS_TOKEN, _TOKEN_EXPIRY
    oauth_raw = os.environ.get("GDRIVE_OAUTH_JSON", "").strip()
    sa_raw = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON", "").strip()
    if not oauth_raw and not sa_raw:
        return None

    with _TOKEN_LOCK:
        if _ACCESS_TOKEN and time.time() < _TOKEN_EXPIRY - 60:
            return _ACCESS_TOKEN

        if oauth_raw:
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

        if sa_raw:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request as GoogleAuthRequest

            sa_info = json.loads(sa_raw)
            creds = service_account.Credentials.from_service_account_info(
                sa_info, scopes=["https://www.googleapis.com/auth/drive"]
            )
            creds.refresh(GoogleAuthRequest())
            _ACCESS_TOKEN = creds.token
            _TOKEN_EXPIRY = time.time() + 3000
            return _ACCESS_TOKEN
    return None


def http_get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def http_post_json(url: str, payload: dict[str, Any], referer: str, timeout: int = 25) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": UA,
            "Referer": referer,
            "Origin": BASE_URL,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, dest: Path, referer: str, timeout: int = 180) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
        total = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
    return total


def norm_title(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\.(pdf|epub|djvu|mobi)$", "", s)
    s = re.sub(r"\b(pdf|download|free|review|bangla|ebook|book)\b", " ", s)
    s = re.sub(r"[^a-z0-9\u0980-\u09ff]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_book_name(raw: str) -> str:
    s = html_lib.unescape(raw or "").strip()
    s = re.sub(r"\s*PDF\s*Download\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*Download\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*PDF\s*$", "", s, flags=re.I)
    s = re.sub(r'[<>:"/\\|?*\r\n\t]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    if len(s) > 120:
        s = s[:120].strip()
    return s or "Untitled Book"


def parse_gdrive_id(output: str) -> str | None:
    txt = (output or "").strip()
    if txt.startswith("{"):
        try:
            obj = json.loads(txt)
            if obj.get("id"):
                return obj["id"]
        except Exception:
            pass
    m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", txt)
    if m:
        return m.group(1)
    m2 = re.search(r'"id"\s*:\s*"([A-Za-z0-9_-]+)"', txt)
    if m2:
        return m2.group(1)
    return None


def _rest_mkdir(name: str, parent_id: str) -> str:
    for attempt in range(4):
        try:
            token = _get_drive_access_token()
            if not token:
                raise RuntimeError("No Drive API token")
            req = urllib.request.Request(
                "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id",
                data=json.dumps({
                    "name": name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [parent_id],
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))["id"]
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"REST mkdir failed for {name}")


def _rest_upload(local_path: Path, parent_id: str) -> str:
    size = local_path.stat().st_size
    for attempt in range(4):
        try:
            token = _get_drive_access_token()
            if not token:
                raise RuntimeError("No Drive API token")
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
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Length": str(len(data)),
                },
                method="PUT",
            )
            with urllib.request.urlopen(put_req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))["id"]
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"REST upload failed for {local_path.name}")


def gdrive_mkdir(name: str, parent_id: str) -> str:
    if os.environ.get("GDRIVE_OAUTH_JSON") or os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON"):
        return _rest_mkdir(name, parent_id)
    for attempt in range(4):
        res = subprocess.run(
            [GDRIVE, "mutate", "mkdir", name, "--parent", parent_id],
            capture_output=True, text=True, encoding="utf-8",
        )
        if res.returncode == 0:
            fid = parse_gdrive_id(res.stdout)
            if fid:
                return fid
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"gdrive mkdir failed for {name}: {res.stderr or res.stdout}")


def gdrive_upload(local_path: Path, parent_id: str) -> str:
    if os.environ.get("GDRIVE_OAUTH_JSON") or os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON"):
        return _rest_upload(local_path, parent_id)
    for attempt in range(4):
        res = subprocess.run(
            [GDRIVE, "mutate", "upload", str(local_path), "--parent", parent_id],
            capture_output=True, text=True, encoding="utf-8",
        )
        if res.returncode == 0:
            fid = parse_gdrive_id(res.stdout)
            if fid:
                return fid
        time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"gdrive upload failed for {local_path.name}: {res.stderr or res.stdout}")


def crawl_catalog() -> list[dict[str, str]]:
    if CATALOG_FILE.exists():
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        if len(data) >= 1000:
            return data

    first_html = http_get(f"{BASE_URL}/books")
    m_pages = re.search(r"Page\s+1\s+of\s+(\d+)", first_html)
    total_pages = int(m_pages.group(1)) if m_pages else 44

    skip = {
        "/books/academic", "/books/admission", "/books/job", "/books/general",
        "/books/hsc", "/books/ssc", "/books/alim", "/books/jsc", "/books/general-knowledge",
    }

    def fetch_page(p: int) -> list[dict[str, str]]:
        url = f"{BASE_URL}/books?page={p}" if p > 1 else f"{BASE_URL}/books"
        body = first_html if p == 1 else http_get(url)
        cards = re.findall(r'<a[^>]+href="(/books/[^"?]+)"[^>]*>(.*?)</a>', body, re.S)
        out = []
        seen = set()
        for href, inner in cards:
            if href in skip or href in seen:
                continue
            text = html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner))).strip()
            if not text or len(text) < 15:
                continue
            seen.add(href)
            out.append({"slug": href.split("/books/")[-1], "url": BASE_URL + href, "card_text": text})
        return out

    all_items: dict[str, dict[str, str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for items in ex.map(fetch_page, range(1, total_pages + 1)):
            for it in items:
                all_items[it["slug"]] = it

    catalog = list(all_items.values())
    CATALOG_FILE.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog


def fetch_book_metadata(slug: str) -> dict[str, Any]:
    url = f"{BASE_URL}/books/{slug}"
    bhtml = http_get(url)
    meta: dict[str, Any] = {
        "slug": slug,
        "book_url": url,
        "title": "",
        "author": "Various / Unknown",
        "publisher": "students.bd",
        "category": "",
        "cover_url": "",
    }
    for jraw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', bhtml, re.S):
        try:
            obj = json.loads(jraw)
        except Exception:
            continue
        if obj.get("@type") == "Book":
            meta["title"] = obj.get("name") or ""
            auth = obj.get("author")
            if isinstance(auth, dict) and auth.get("name"):
                meta["author"] = auth["name"]
            pub = obj.get("publisher")
            if isinstance(pub, dict) and pub.get("name"):
                meta["publisher"] = pub["name"]
            img = obj.get("image") or ""
            if img.startswith("/"):
                img = BASE_URL + img
            meta["cover_url"] = img
        elif obj.get("@type") == "BreadcrumbList":
            elems = obj.get("itemListElement") or []
            if len(elems) >= 3:
                meta["category"] = elems[2].get("name") or ""
    return meta


def classify_book(title: str, author: str, category: str, publisher: str, slug: str, clean_folders: dict[str, str]) -> str:
    low = f"{title} {slug}".lower()
    m_cls = re.search(r"\bclass[-_\s]*(10|9|8|7|6|5|4|3|2|1)\b", low)
    if m_cls:
        leaf = f"Education and Academics/Class {m_cls.group(1)}"
        if leaf in clean_folders:
            return leaf
    if "class 9-10" in low or "class-9-10" in low or "ssc" in low:
        return "Education and Academics/Class 9"
    if "hsc" in low or "alim" in low:
        return "Education and Academics/Higher Secondary"

    leaf = cc.classify_clean_leaf(
        title=title,
        author=author,
        genres=[category] if category else [],
        publication=publisher,
        source_path=f"{category}/{slug}",
    )
    if leaf in clean_folders:
        return leaf
    if category.lower() in ("admission", "academic"):
        return "Education and Academics/Higher Secondary"
    if category.lower() in ("job", "job prep"):
        return "Reference Books/General Knowledge"
    return "Reference Books/General Knowledge"


def process_one(
    item: dict[str, str],
    clean_folders: dict[str, str],
    existing_norms: set[str],
    deadline: float | None,
) -> tuple[str, str]:
    if deadline and time.time() > deadline:
        return "time_limit", item["slug"]

    slug = item["slug"]
    meta = fetch_book_metadata(slug)
    raw_title = meta["title"] or item["card_text"]
    clean_name = clean_book_name(raw_title)

    if norm_title(clean_name) in existing_norms or norm_title(slug.replace("-", " ")) in existing_norms:
        return "skipped_dup", slug

    leaf_path = classify_book(
        clean_name, meta["author"], meta["category"], meta["publisher"], slug, clean_folders
    )
    parent_folder_id = clean_folders[leaf_path]

    dl_page_url = f"{BASE_URL}/download/{slug}"
    dhtml = http_get(dl_page_url)
    m_fid = re.search(r'const driveFileId\s*=\s*"([^"]+)"', dhtml)
    m_tok = re.search(r'const downloadSessionToken\s*=\s*"([^"]+)"', dhtml)
    m_wait = re.search(r'const requiredWaitSeconds\s*=\s*(\d+)', dhtml)
    if not (m_fid and m_tok and m_wait):
        return "error_no_token", slug

    file_id = m_fid.group(1)
    token = m_tok.group(1)
    wait_sec = int(m_wait.group(1))
    time.sleep(wait_sec + 1)

    verify_data = http_post_json(
        f"{BASE_URL}/api/verify-download-wait",
        {"token": token, "fileId": file_id},
        referer=dl_page_url,
    )
    if not verify_data.get("verified") or not verify_data.get("downloadUrl"):
        return "error_verify", slug

    dl_url = verify_data["downloadUrl"]
    if dl_url.startswith("/"):
        dl_url = BASE_URL + dl_url

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_pdf = TMP_DIR / f"{slug}.pdf"
    try:
        size_bytes = download_file(dl_url, tmp_pdf, referer=dl_page_url)
        if size_bytes < 1024:
            return "error_small_file", slug

        book_folder_id = gdrive_mkdir(clean_name, parent_folder_id)
        # Rename before upload so Drive filename is clean_name.pdf
        clean_pdf = TMP_DIR / f"{clean_name}.pdf"
        if tmp_pdf != clean_pdf:
            if clean_pdf.exists():
                clean_pdf.unlink()
            tmp_pdf.rename(clean_pdf)
            tmp_pdf = clean_pdf
        uploaded_pdf_id = gdrive_upload(tmp_pdf, book_folder_id)
    finally:
        if tmp_pdf.exists():
            tmp_pdf.unlink()

    top_cat, leaf_cat = leaf_path.split("/", 1)[0], leaf_path.split("/")[-1]
    record = {
        "folder_id": book_folder_id,
        "folder_link": f"https://drive.google.com/drive/folders/{book_folder_id}",
        "file_id": uploaded_pdf_id,
        "link": f"https://drive.google.com/drive/folders/{book_folder_id}",
        "name": clean_name,
        "title": clean_name,
        "author": meta["author"],
        "publication": meta["publisher"] or "students.bd",
        "top_category": top_cat,
        "leaf_path": leaf_path,
        "leaf_category": leaf_cat,
        "size": size_bytes,
        "pdf_file_id": uploaded_pdf_id,
        "epub_file_id": "",
        "text_file_id": "",
        "cover_file_id": "",
        "cover_url": meta["cover_url"],
        "thumbnail_url": meta["cover_url"],
        "book_url": meta["book_url"],
        "formats": ["PDF"],
        "files": [
            {
                "id": uploaded_pdf_id,
                "name": f"{clean_name}.pdf",
                "size": size_bytes,
                "mimeType": "application/pdf",
            }
        ],
        "subfolder": None,
        "source": "students.bd",
        "slug": slug,
    }

    with LOCK:
        prog = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
        prog[slug] = record
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
    parser.add_argument("--limit", type=int, default=0, help="Max books to process (0 = all)")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent workers")
    parser.add_argument("--max-minutes", type=int, default=0, help="Graceful stop after N minutes (0 = no limit)")
    parser.add_argument("--merge-only", action="store_true", help="Only merge progress into merged_books.json")
    args = parser.parse_args()

    if args.merge_only:
        added = merge_into_catalog()
        print(f"Merged {added} new books into merged_books.json")
        return

    clean_folders = json.loads(FOLDERS_FILE.read_text(encoding="utf-8"))
    merged = json.loads(MERGED_FILE.read_text(encoding="utf-8"))
    existing_norms = set()
    for b in merged:
        for k in ("name", "title", "english_name"):
            if b.get(k):
                existing_norms.add(norm_title(b[k]))

    progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
    catalog = crawl_catalog()
    todo = [it for it in catalog if it["slug"] not in progress]
    if args.limit > 0:
        todo = todo[: args.limit]

    print(f"Catalog: {len(catalog)} | Already processed: {len(progress)} | Todo: {len(todo)}")
    if not todo:
        added = merge_into_catalog()
        print(f"Nothing to download. Merged {added} books into merged_books.json")
        return

    deadline = (time.time() + args.max_minutes * 60) if args.max_minutes > 0 else None
    stats = {"added": 0, "skipped_dup": 0, "error": 0, "time_limit": 0}
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_one, it, clean_folders, existing_norms, deadline): it for it in todo}
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
                        prog[it["slug"]] = {"status": "skipped_dup"}
                        PROGRESS_FILE.write_text(json.dumps(prog, ensure_ascii=False, indent=2), encoding="utf-8")
                elif status == "time_limit":
                    stats["time_limit"] += 1
                else:
                    stats["error"] += 1
                    print(f"[{done}/{len(todo)}] {status}: {info}", flush=True)
            except Exception as e:
                stats["error"] += 1
                print(f"[{done}/{len(todo)}] EXCEPTION {it['slug']}: {e}", flush=True)

            if done % 20 == 0 or done == len(todo):
                print(
                    f"Progress: {done}/{len(todo)} | added={stats['added']} skipped={stats['skipped_dup']} errors={stats['error']}",
                    flush=True,
                )

    added_to_merged = merge_into_catalog()
    remaining = len(catalog) - len(json.loads(PROGRESS_FILE.read_text(encoding="utf-8")))
    print(f"Done! Run stats={stats} | Merged {added_to_merged} new books | Remaining={remaining}")


if __name__ == "__main__":
    main()
