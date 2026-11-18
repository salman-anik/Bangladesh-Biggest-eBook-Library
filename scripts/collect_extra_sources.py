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
import shutil
import ssl
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
TMP_DIR = ROOT / "tmp_extra_sources"
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import clean_classifier as cc  # noqa: E402

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

BOOK_EXTS = (".pdf", ".epub", ".djvu", ".mobi", ".azw3")

SKIP_DOMAINS = (
    "mediafire.com",
    "banglakitab.com",
    "bnislaam.files.wordpress.com",
    "bnislamcdn.files.wordpress.com",
)


def _is_skipped_url(url: str) -> bool:
    low = (url or "").lower()
    return any(dom in low for dom in SKIP_DOMAINS)

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
    "https://justpaste.it/islamiclinks/pdf",
    "https://collectionislamicbd.blogspot.com/2018/09/pdf.html",
    "https://collectionislamicbd.blogspot.com/2018/09/blog-post_46.html",
    "https://collectionislamicbd.blogspot.com/2018/",
    "https://collectionislamicbd.blogspot.com/2019/",
    "https://collectionislamicbd.blogspot.com/2020/",
    "https://bangla-booksdownload.blogspot.com/",
    "https://hugecollectionoflinks.blogspot.com/",
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
    "http://kitabbhubon.com/",
    "http://pathagar.com/",
    "http://almodina.com/site_2.xhtml",
    "http://jamiatulasad.com/?page_id=4188",
    "http://www.banglakitab.com/kitab.htm",
    "http://waytotawheed.com/%E0%A6%A4%E0%A6%BE%E0%A6%93%E0%A6%B9%E0%A7%80%E0%A6%A6/",
    "https://islamhouse.com/bn/main/",
    "https://islamhouse.com/",
    "http://eelm.weebly.com/",
    "https://banglakitab.weebly.com/",
    "http://ohilibrary.blogspot.com/",
    "http://www.draminlibrary.com/proindex/bookcatagory/1/4",
    "https://www.muslimmedia.info/",
    "http://www.mwazed.com/",
    "http://aazeenofislam.com/",
    "http://assunnahtrust.com/wps/",
    "http://www.waytojannah.com/",
    "http://preachingauthenticislaminbangla.blogspot.com/",
    "http://alquranervasha.com/books",
    "http://islamicboisomahar.blogspot.com/2017/04/blog-post_10.html",
    "https://www.allahsword.com/",
    "https://islam4god.wordpress.com/",
    "https://justpaste.it/hasanmirza",
    "https://justpaste.it/thegreatestnation",
    "https://justpaste.it/meersalman",
    "https://justpaste.it/collected2-4",
    "https://justpaste.it/noyonchatterjee",
    "https://justpaste.it/lekhacollection",
    "https://justpaste.it/lekhacollection2",
    "https://justpaste.it/5may2013",
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


def _extract_links_from_html(
    final_url: str,
    body: str,
    source_label: str,
    discovered_folders: dict[str, str],
    discovered_drive_files: dict[str, dict[str, Any]],
    discovered_web_pdfs: dict[str, dict[str, Any]],
    collect_internal: bool = False,
) -> list[str]:
    for m in re.finditer(r"drive\.google\.com/(?:drive/folders/|folderview\?id=)([A-Za-z0-9_-]{15,})", final_url + "\n" + body):
        discovered_folders.setdefault(m.group(1), source_label)
    for m in re.finditer(r"drive\.google\.com/(?:file/d/|open\?id=)([A-Za-z0-9_-]{15,})", final_url + "\n" + body):
        discovered_drive_files.setdefault(
            m.group(1),
            {"kind": "drive_file", "id": m.group(1), "name": m.group(1), "source": source_label},
        )
    for href in re.findall(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', body, re.I):
        full = urllib.parse.urljoin(final_url, href)
        if _is_skipped_url(full):
            continue
        fname = clean_book_name(Path(urllib.parse.urlparse(full).path).name)
        discovered_web_pdfs.setdefault(
            full,
            {"kind": "web_pdf", "id": full, "url": full, "name": fname, "source": source_label},
        )

    internal_links: list[str] = []
    if collect_internal:
        parsed_base = urllib.parse.urlparse(final_url)
        host = parsed_base.netloc.lower()
        follow_domains = ("blogspot.com", "wordpress.com", "kalamullah.com", "islamicbook.ws", "allahsword.com")
        if any(d in host for d in follow_domains) and not _is_skipped_url(final_url):
            seen: set[str] = set()
            for href in re.findall(r'href=["\']([^"\'#]+)["\']', body, re.I):
                full = urllib.parse.urljoin(final_url, href)
                if _is_skipped_url(full):
                    continue
                p = urllib.parse.urlparse(full)
                if p.scheme not in ("http", "https") or p.netloc.lower() != host:
                    continue
                low = p.path.lower()
                if low.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".ico", ".xml", ".pdf")):
                    continue
                if any(skip in low for skip in ("/search/label/", "wp-login", "wp-json", "/feed", "/comment", "share=")):
                    continue
                if full not in seen and full != final_url:
                    seen.add(full)
                    internal_links.append(full)
                    if len(internal_links) >= 40:
                        break
    return internal_links


def build_catalog(refresh_web: bool = False) -> list[dict[str, Any]]:
    discovered_folders: dict[str, str] = {fid: label for fid, label in SEED_DRIVE_FOLDERS}
    discovered_drive_files: dict[str, dict[str, Any]] = {}
    discovered_web_pdfs: dict[str, dict[str, Any]] = {}

    if CATALOG_FILE.exists():
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        if data and len(data) >= 7000 and not refresh_web:
            return [it for it in data if not (it.get("kind") == "web_pdf" and _is_skipped_url(it.get("url", "")))]
        for it in data:
            if it.get("kind") == "drive_file":
                discovered_drive_files[it["id"]] = it
            elif it.get("kind") == "web_pdf" and not _is_skipped_url(it.get("url", "")):
                discovered_web_pdfs[it["id"]] = it

    # 1. Resolve shortlinks & crawl web seed pages concurrently
    crawl_lock = threading.Lock()
    internal_candidates: list[str] = []

    def crawl_one(url: str, collect_internal: bool) -> list[str]:
        try:
            final_url, body = http_get_lenient(url, timeout=20)
        except Exception:
            return []
        with crawl_lock:
            return _extract_links_from_html(
                final_url,
                body,
                final_url,
                discovered_folders,
                discovered_drive_files,
                discovered_web_pdfs,
                collect_internal=collect_internal,
            )

    print("Crawling shortlinks and web seed pages...", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(crawl_one, u, False) for u in SHORTLINKS_TO_RESOLVE]
        futs.extend(ex.submit(crawl_one, u, True) for u in WEB_SEED_PAGES)
        for fut in concurrent.futures.as_completed(futs):
            internal_candidates.extend(fut.result())

    # 2. Follow 1-level internal post/category links on blog/book sites
    unique_internal = list(dict.fromkeys(internal_candidates))
    if unique_internal:
        print(f"Following {len(unique_internal)} 1-level internal pages for nested PDFs/Drive links...", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            list(ex.map(lambda u: crawl_one(u, False), unique_internal))

    # 3. Recursively walk all discovered Google Drive folders
    visited_folders: set[str] = (
        {fid for fid, _ in SEED_DRIVE_FOLDERS}
        if (refresh_web or len(discovered_drive_files) >= 2000)
        else set()
    )
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
    if item["kind"] == "web_pdf" and _is_skipped_url(item.get("url", "")):
        return "skipped_dup", key
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
        book_tmp_dir = TMP_DIR / f"web_{abs(hash(key))}"
        book_tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_pdf = book_tmp_dir / f"{clean_name}.pdf"
        try:
            ctx = ssl._create_unverified_context()
            target_url = item["url"]
            if "mediafire.com/file/" in target_url.lower():
                try:
                    mf_req = urllib.request.Request(target_url, headers={"User-Agent": UA})
                    with urllib.request.urlopen(mf_req, timeout=10, context=ctx) as mf_resp:
                        mf_html = mf_resp.read(300_000).decode("utf-8", "ignore")
                    m_dl = re.search(
                        r'href=["\'](https?://download[^"\']+mediafire\.com/[^"\']+)["\']',
                        mf_html,
                        re.I,
                    )
                    if not m_dl:
                        return "error_mediafire_blocked", key
                    target_url = m_dl.group(1)
                except Exception:
                    return "error_mediafire_blocked", key

            req = urllib.request.Request(target_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp, open(tmp_pdf, "wb") as f:
                ct = (resp.headers.get("Content-Type") or "").lower()
                if "text/html" in ct:
                    return "error_html", key
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
            size_bytes = tmp_pdf.stat().st_size
            if size_bytes < 1024:
                return "error_small", key
            with open(tmp_pdf, "rb") as f:
                if f.read(4) != b"%PDF":
                    return "error_not_pdf", key
            book_folder_id = drive_mkdir(clean_name, parent_folder_id)
            copied_id = drive_upload_pdf(tmp_pdf, book_folder_id)
            ext = ".pdf"
            mime = "application/pdf"
        finally:
            shutil.rmtree(book_tmp_dir, ignore_errors=True)

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

    return "added", rec


def _save_progress(progress: dict[str, Any]) -> None:
    tmp = PROGRESS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(PROGRESS_FILE)


def merge_into_catalog() -> int:
    remote_prog_path = Path(r"C:\Users\USER\.gemini\antigravity\brain\6af272c0-81bd-4ce5-b026-18cf29271c9c\scratch\remote_extra_prog.json")
    prog = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
    if remote_prog_path.exists():
        try:
            rprog = json.loads(remote_prog_path.read_text(encoding="utf-8"))
            updated = False
            for k, v in rprog.items():
                if k not in prog:
                    prog[k] = v
                    updated = True
            if updated:
                PROGRESS_FILE.write_text(json.dumps(prog, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    if not prog:
        return 0
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
    parser.add_argument("--refresh-web", action="store_true")
    args = parser.parse_args()

    if args.merge_only:
        print(f"Merged {merge_into_catalog()} new books into merged_books.json")
        return

    clean_folders = json.loads(FOLDERS_FILE.read_text(encoding="utf-8"))
    merged = json.loads(MERGED_FILE.read_text(encoding="utf-8"))
    existing_norms = {norm_title(b[k]) for b in merged for k in ("name", "title", "english_name") if b.get(k)}
    existing_fids = {b["file_id"] for b in merged if b.get("file_id")}

    progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
    catalog = build_catalog(refresh_web=args.refresh_web)
    todo = [it for it in catalog if it["id"] not in progress]
    if args.limit > 0:
        todo = todo[: args.limit]

    print(f"Extra Catalog: {len(catalog)} | Processed: {len(progress)} | Todo: {len(todo)}", flush=True)
    if not todo:
        print(f"Nothing left. Merged {merge_into_catalog()} books.", flush=True)
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "rename_books_english.py"), "--workers", str(args.workers)],
            check=False,
        )
        return

    deadline = (time.time() + args.max_minutes * 60) if args.max_minutes > 0 else None
    stats = {"added": 0, "skipped_dup": 0, "error": 0, "time_limit": 0}
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_one, it, clean_folders, existing_norms, existing_fids, deadline): it for it in todo}
        for f in concurrent.futures.as_completed(futs):
            it = futs[f]
            done += 1
            status = "error"
            try:
                status, info = f.result()
                if status == "added":
                    stats["added"] += 1
                    progress[it["id"]] = info
                elif status == "skipped_dup":
                    stats["skipped_dup"] += 1
                    progress[it["id"]] = {"status": "skipped_dup"}
                elif status == "time_limit":
                    stats["time_limit"] += 1
                else:
                    stats["error"] += 1
                    progress[it["id"]] = {"status": "error", "detail": status}
            except Exception as e:
                stats["error"] += 1
                print(f"[{done}/{len(todo)}] EXCEPTION {it['id']}: {e}", flush=True)
                progress[it["id"]] = {"status": "error", "detail": str(e)}
            if done % 20 == 0 or done == len(todo):
                _save_progress(progress)
            if status == "added" or done % 5 == 0 or done == len(todo):
                print(
                    f"[Countdown] Done: {done}/{len(todo)} | Remaining: {len(todo) - done} | "
                    f"added={stats['added']} skipped={stats['skipped_dup']} errors={stats['error']}",
                    flush=True,
                )

    _save_progress(progress)
    print(f"Done! {stats} | Merged {merge_into_catalog()} new books into merged_books.json", flush=True)
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "rename_books_english.py"), "--workers", str(args.workers)],
        check=False,
    )


if __name__ == "__main__":
    main()
