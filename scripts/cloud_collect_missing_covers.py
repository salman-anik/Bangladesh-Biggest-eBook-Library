#!/usr/bin/env python3
"""Cloud Phase 2: Collect missing covers for all remaining catalog books via:
  Tier 1: Non-placeholder cover_url from local catalogs (bdebooks, kindlebangla, ebanglalibrary, qawmimadrasa)
  Tier 2: Rokomari.com search with strict title+author matching (260x372 CDN covers)
  Tier 3: OpenLibrary & Archive.org (for English / International / Classic titles)
  Tier 4: Direct Drive EPUB cover extraction & PDF Page-1 rendering via PyMuPDF (fitz)
Uploads directly into Library Management/Cover Images/<Category>/<Subcategory>/<Book Stem>.<ext>.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import re
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CATALOG = ROOT / "catalog"
SHARDS_DIR = DATA / "cover_shards"
sys.path.insert(0, str(ROOT / "library_tools"))
import drive_api as dapi  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", str(s or ""))
    s = s.replace("য়", "য়").replace("ড়", "ড়").replace("ঢ়", "ঢ়")
    s = re.sub(r"\.[a-z0-9]{2,4}$", "", s, flags=re.I)
    s = re.sub(r"[\W_]+", " ", s, flags=re.U).strip().casefold()
    return s


def clean_query_text(s: str) -> str:
    s = unicodedata.normalize("NFC", str(s or ""))
    s = re.sub(r"\.[a-z0-9]{2,4}$", "", s, flags=re.I)
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)
    s = re.sub(r"(?:www\.[a-z0-9.\-]+|bdniyog\.com|admissionwar\.com|almodina\.com|qawmimadrasa\.com)", " ", s, flags=re.I)
    s = re.sub(r"[—–\-:|_/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sanitize_filename(s: str, max_len: int = 180) -> str:
    s = unicodedata.normalize("NFC", str(s or "")).strip()
    s = re.sub(r'[<>:"/\\|?*\r\n\t\x00-\x1f]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    return s[:max_len].strip() if len(s) > max_len else s


def canonical_book_stem(b: dict) -> str:
    dp = b.get("drive_path") or b.get("original_filename") or b.get("title") or "Untitled"
    stem = Path(dp).stem
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4]
    return sanitize_filename(stem or b.get("title") or "Untitled")


def token_similarity(book_title: str, book_author: str, cand_title: str, cand_text: str) -> float:
    bt_clean = norm(clean_query_text(book_title))
    ct_clean = norm(clean_query_text(cand_title))
    if not bt_clean or not ct_clean:
        return 0.0
    if bt_clean == ct_clean:
        return 1.0
    bt_tokens = {w for w in bt_clean.split() if len(w) >= 2}
    ct_tokens = {w for w in ct_clean.split() if len(w) >= 2}
    if not bt_tokens or not ct_tokens:
        return 0.0
    overlap = len(bt_tokens & ct_tokens)
    jaccard = overlap / len(bt_tokens | ct_tokens)
    recall = overlap / len(bt_tokens)
    score = 0.55 * recall + 0.45 * jaccard
    # Author bonus/penalty if book has known author
    if book_author and book_author not in ("Unknown", "Various / Unknown", "NCTB", "এনসিটিবি"):
        au_tokens = {w for w in norm(book_author).split() if len(w) >= 2}
        full_cand = norm(f"{cand_title} {cand_text}")
        if au_tokens and any(a in full_cand for a in au_tokens):
            score = min(1.0, score + 0.18)
    # Reject generic 1-word author-only matches when book title has 2+ words
    if len(bt_tokens) >= 2 and overlap <= 1 and len(ct_tokens) <= 2:
        score *= 0.4
    return score


def http_get_bytes(url: str, timeout: int = 15) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ct = (r.headers.get("Content-Type") or "").lower()
        return r.status, ct, r.read()


def detect_valid_image(data: bytes, ct: str = "", url: str = "") -> tuple[str, str] | None:
    if not data or len(data) < 900:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg", "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "image/gif"
    return None


def search_rokomari_cover(book_title: str, book_author: str) -> tuple[str, bytes, str, str] | None:
    if BeautifulSoup is None:
        return None
    t_q = clean_query_text(book_title)
    if len(t_q) < 2:
        return None
    a_q = clean_query_text(book_author) if book_author and book_author not in ("Unknown", "Various / Unknown", "NCTB", "এনসিটিবি") else ""
    q = f"{t_q} {a_q}".strip() if len(t_q.split()) <= 5 else t_q
    url = "https://www.rokomari.com/search?term=" + urllib.parse.quote(q)
    _, _, raw = http_get_bytes(url, timeout=15)
    soup = BeautifulSoup(raw.decode("utf-8", "replace"), "html.parser")

    best_score = 0.0
    best_img_url = ""
    for a in soup.select("a[href^='/book/']"):
        img = a.select_one("img")
        if not img:
            continue
        src = img.get("data-src") or img.get("src") or ""
        if not src or "Product" not in src or "rokomari.io" not in src:
            continue
        href_slug = urllib.parse.unquote(a.get("href", "")).split("?")[0].rsplit("/", 1)[-1].replace("-", " ")
        txt_parts = [t.strip() for t in a.stripped_strings if t.strip() not in ("(", ")", "Product in stock")]
        cand_title = txt_parts[1] if (len(txt_parts) >= 2 and txt_parts[0].isdigit()) else (txt_parts[0] if txt_parts else href_slug)
        cand_full = " ".join(txt_parts) + " " + href_slug
        sc = max(
            token_similarity(t_q, a_q, cand_title, cand_full),
            token_similarity(t_q, a_q, href_slug, cand_full),
        )
        if sc > best_score:
            best_score = sc
            best_img_url = src

    threshold = 0.62 if len(t_q.split()) >= 2 else 0.78
    if best_score < threshold or not best_img_url:
        return None

    for candidate_url in (best_img_url.replace("/130X186/", "/260X372/"), best_img_url):
        try:
            _, ct, img_bytes = http_get_bytes(candidate_url, timeout=15)
            checked = detect_valid_image(img_bytes, ct, candidate_url)
            if checked:
                return candidate_url, img_bytes, checked[0], checked[1]
        except Exception:
            continue
    return None


def search_english_apis_cover(book_title: str, book_author: str) -> tuple[str, bytes, str, str] | None:
    t_q = clean_query_text(book_title)
    if len(t_q) < 3:
        return None
    a_q = clean_query_text(book_author) if book_author and book_author not in ("Unknown", "Various / Unknown") else ""
    # 1. OpenLibrary
    try:
        ol_url = "https://openlibrary.org/search.json?title=" + urllib.parse.quote(t_q)
        if a_q:
            ol_url += "&author=" + urllib.parse.quote(a_q)
        ol_url += "&limit=5"
        _, _, raw = http_get_bytes(ol_url, timeout=12)
        docs = json.loads(raw).get("docs") or []
        for doc in docs:
            cid = doc.get("cover_i")
            if not cid:
                continue
            ctitle = doc.get("title") or ""
            cauth = " ".join(doc.get("author_name") or [])
            if token_similarity(t_q, a_q, ctitle, cauth) >= 0.65:
                cov_u = f"https://covers.openlibrary.org/b/id/{cid}-L.jpg?default=false"
                try:
                    _, ct, ib = http_get_bytes(cov_u, timeout=12)
                    checked = detect_valid_image(ib, ct, cov_u)
                    if checked and len(ib) > 2500:
                        return cov_u, ib, checked[0], checked[1]
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Archive.org
    try:
        aq = f'title:("{t_q}")'
        ar_url = (
            "https://archive.org/advancedsearch.php?q="
            + urllib.parse.quote(aq)
            + "&fl[]=identifier,title,creator&rows=5&output=json"
        )
        _, _, raw = http_get_bytes(ar_url, timeout=12)
        docs = (json.loads(raw).get("response") or {}).get("docs") or []
        for doc in docs:
            ident = doc.get("identifier")
            if not ident:
                continue
            ctitle = doc.get("title") or ""
            cauth = str(doc.get("creator") or "")
            if token_similarity(t_q, a_q, ctitle, cauth) >= 0.68:
                cov_u = f"https://archive.org/services/img/{ident}"
                try:
                    _, ct, ib = http_get_bytes(cov_u, timeout=12)
                    checked = detect_valid_image(ib, ct, cov_u)
                    if checked and len(ib) > 2500:
                        return cov_u, ib, checked[0], checked[1]
                except Exception:
                    pass
    except Exception:
        pass
    return None


_BIG_DL_SEM = threading.Semaphore(2)


def extract_cover_from_drive_book(book: dict) -> tuple[bytes, str, str, str] | None:
    fid = book["drive_file_id"]
    fmt = (book.get("format") or "").upper()
    if fmt not in ("PDF", "EPUB"):
        return None
    size_bytes = int(book.get("file_size") or 0)
    if size_bytes > 750 * 1024 * 1024:
        return None

    is_big = size_bytes > 80 * 1024 * 1024
    if is_big:
        _BIG_DL_SEM.acquire()
    try:
        raw = dapi.download_full(fid)
    except Exception:
        return None
    finally:
        if is_big:
            _BIG_DL_SEM.release()

    if fmt == "EPUB":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                img_names = [
                    n for n in zf.namelist()
                    if Path(n).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif")
                ]
                img_names.sort(
                    key=lambda n: (
                        1 if "cover" in Path(n).name.lower() else 0,
                        zf.getinfo(n).file_size,
                    ),
                    reverse=True,
                )
                for nm in img_names[:5]:
                    ib = zf.read(nm)
                    checked = detect_valid_image(ib)
                    if checked and len(ib) > 1500:
                        return ib, checked[0], checked[1], "epub_embedded"
        except Exception:
            return None

    if fmt == "PDF" and fitz is not None:
        try:
            doc = fitz.open(stream=raw, filetype="pdf")
            if doc.page_count < 1:
                doc.close()
                return None
            page = doc.load_page(0)
            rect = page.rect
            scale = min(1.8, 720.0 / max(rect.width, 1.0))
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            ib = pix.tobytes("jpeg", jpg_quality=85)
            doc.close()
            if len(ib) > 1000:
                return ib, ".jpg", "image/jpeg", "pdf_page1"
        except Exception:
            return None
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--skip-rokomari", action="store_true")
    ap.add_argument("--only-book-ids", default="", help="Optional JSON list of drive_file_id to restrict processing")
    args = ap.parse_args()

    SHARDS_DIR.mkdir(parents=True, exist_ok=True)
    mc = json.loads((CATALOG / "master_catalog.json").read_text(encoding="utf-8"))
    plan = json.loads((DATA / "existing_covers_audit_plan.json").read_text(encoding="utf-8"))
    covered = set(plan["chosen_cover_by_book"].keys())
    folder_ids: dict[str, str] = json.loads((DATA / "cover_folder_ids.json").read_text(encoding="utf-8"))

    # Build local valid cover URL lookup
    url_by_norm: dict[str, str] = {}
    url_by_src: dict[str, str] = {}
    for fn in ["bdebooks_catalog.json", "kindlebangla_catalog.json", "ebanglalibrary_meta.json", "qawmimadrasa_catalog.json"]:
        p = DATA / fn
        if not p.exists():
            continue
        for r in json.loads(p.read_text(encoding="utf-8")):
            if not isinstance(r, dict):
                continue
            cu = r.get("cover_url") or r.get("thumbnail_url") or ""
            if not cu or "egb_logo" in cu or "drive.google.com" in cu:
                continue
            u = (r.get("url") or r.get("page_url") or "").rstrip("/")
            if u:
                url_by_src[u] = cu
            for k in (r.get("title"), r.get("raw_title"), r.get("target_stem")):
                if k:
                    url_by_norm.setdefault(norm(k), cu)
                    for sep in (" - ", " — "):
                        if sep in k:
                            url_by_norm.setdefault(norm(k.split(sep, 1)[0]), cu)

    # Group missing books by unique (target_folder, canonical_stem.casefold())
    only_ids = set(json.loads(Path(args.only_book_ids).read_text(encoding="utf-8"))) if args.only_book_ids else None
    missing = [
        b for b in mc
        if b["drive_file_id"] not in covered and (only_ids is None or b["drive_file_id"] in only_ids)
    ]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for b in missing:
        cat_folder = f"{b['category']}/{b['subcategory']}" if b.get("subcategory") else b["category"]
        stem = canonical_book_stem(b)
        groups[(cat_folder, stem.casefold())].append(b)

    sorted_keys = sorted(groups.keys())
    shard_keys = [k for i, k in enumerate(sorted_keys) if i % args.num_shards == args.shard_index]
    print(f"Shard {args.shard_index}/{args.num_shards}: {len(shard_keys)} target covers (from {len(sorted_keys)} total).", flush=True)

    # Check existing files in folders touched by this shard (idempotent resume!)
    touched_folder_ids = {folder_ids[k[0]] for k in shard_keys if k[0] in folder_ids}
    existing_in_folder: dict[str, dict[str, str]] = {}
    print(f"Indexing existing files across {len(touched_folder_ids)} target cover folders...", flush=True)

    def ls_folder(fid: str) -> tuple[str, dict[str, str]]:
        m: dict[str, str] = {}
        for it in dapi.list_all(q=f"'{fid}' in parents and mimeType != '{dapi.FOLDER}' and trashed = false", fields="id,name"):
            m[Path(it["name"]).stem.casefold()] = it["id"]
        return fid, m

    with ThreadPoolExecutor(max_workers=12) as ex:
        for fid, m in ex.map(ls_folder, touched_folder_ids):
            existing_in_folder[fid] = m

    # Test Rokomari once on runner to auto-circuit-break if blocked
    rokomari_enabled = not args.skip_rokomari
    if rokomari_enabled:
        try:
            test_hit = search_rokomari_cover("হিমু", "হুমায়ূন আহমেদ")
            print("Rokomari pre-flight test:", "OK" if test_hit else "No match parsed", flush=True)
        except Exception as e:
            print(f"Rokomari pre-flight blocked ({e}) -> disabling Rokomari on this runner.", flush=True)
            rokomari_enabled = False

    roko_fail_streak = 0
    lock = threading.Lock()
    results: list[dict] = []
    source_stats: dict[str, int] = defaultdict(int)
    done = 0

    def process_target(key: tuple[str, str]) -> dict | None:
        nonlocal roko_fail_streak, done
        cat_folder, stem_cf = key
        books = groups[key]
        # Prefer PDF > EPUB > MOBI for Page-1/cover extraction if multiple formats exist
        books_sorted = sorted(books, key=lambda b: {"PDF": 0, "EPUB": 1, "MOBI": 2}.get((b.get("format") or "").upper(), 9))
        b0 = books_sorted[0]
        stem = canonical_book_stem(b0)
        tfid = folder_ids.get(cat_folder)
        if not tfid:
            return {"status": "missing_folder", "folder": cat_folder, "book_ids": [b["drive_file_id"] for b in books]}

        if stem_cf in existing_in_folder.get(tfid, {}):
            cid = existing_in_folder[tfid][stem_cf]
            return {"status": "already_exists", "cover_id": cid, "folder": cat_folder, "stem": stem, "book_ids": [b["drive_file_id"] for b in books], "source": "existing"}

        title = b0.get("title") or stem
        author = b0.get("author") or ""
        img_bytes: bytes | None = None
        ext = ".jpg"
        mime = "image/jpeg"
        src_used = ""

        # Tier 1: Local catalog HTTP URL / direct master_catalog cover_url
        cand_urls: list[str] = []
        cu0 = b0.get("cover_url") or ""
        if cu0.startswith("http") and "drive.google.com" not in cu0 and "egb_logo" not in cu0:
            cand_urls.append(cu0)
        su = (b0.get("source_url") or "").rstrip("/")
        if su in url_by_src:
            cand_urls.append(url_by_src[su])
        for tkey in (norm(title), norm(re.split(r"\s*[-—–]\s*", title, maxsplit=1)[0])):
            if tkey in url_by_norm:
                cand_urls.append(url_by_norm[tkey])

        for cu in cand_urls:
            try:
                _, ct, ib = http_get_bytes(cu, timeout=12)
                checked = detect_valid_image(ib, ct, cu)
                if checked:
                    img_bytes, ext, mime = ib, checked[0], checked[1]
                    src_used = "local_catalog_url"
                    break
            except Exception:
                continue

        # Tier 2: Rokomari (unless blocked or pure non-Bangla/English tech paper)
        lang = (b0.get("language") or "").lower()
        with lock:
            use_roko = rokomari_enabled and roko_fail_streak < 25
        if img_bytes is None and use_roko and lang != "arabic":
            try:
                rhit = search_rokomari_cover(title, author)
                with lock:
                    roko_fail_streak = 0
                if rhit:
                    _, img_bytes, ext, mime = rhit
                    src_used = "rokomari"
            except urllib.error.HTTPError as he:
                if he.code in (403, 429, 503):
                    with lock:
                        roko_fail_streak += 1
                time.sleep(0.5)
            except Exception:
                pass

        # Tier 3: OpenLibrary & Archive.org (for English / International books)
        is_english = (b0.get("category") == "English Books") or bool(re.fullmatch(r"[\x00-\x7f]+", clean_query_text(title)))
        if img_bytes is None and is_english:
            ehit = search_english_apis_cover(title, author)
            if ehit:
                _, img_bytes, ext, mime = ehit
                src_used = "openlibrary_or_archive"

        # Tier 4: Direct Drive EPUB embedded cover or PDF Page-1 extraction
        if img_bytes is None:
            for cand_book in books_sorted:
                extracted = extract_cover_from_drive_book(cand_book)
                if extracted:
                    img_bytes, ext, mime, src_used = extracted
                    break

        if not img_bytes:
            return {"status": "no_cover_found", "folder": cat_folder, "stem": stem, "book_ids": [b["drive_file_id"] for b in books]}

        # Upload cover image cleanly to target folder
        final_name = f"{stem}{ext}"
        fd, tmp_s = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        tmp_p = Path(tmp_s)
        try:
            tmp_p.write_bytes(img_bytes)
            uploaded = dapi.upload_resumable(tmp_p, final_name, tfid, mime_type=mime)
            return {
                "status": "uploaded",
                "cover_id": uploaded["id"],
                "cover_name": final_name,
                "folder": cat_folder,
                "stem": stem,
                "book_ids": [b["drive_file_id"] for b in books],
                "source": src_used,
            }
        finally:
            tmp_p.unlink(missing_ok=True)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_target, k): k for k in shard_keys}
        for fut in as_completed(futs):
            try:
                res = fut.result()
            except Exception as exc:
                res = {"status": "error", "error": str(exc), "key": str(futs[fut])}
            with lock:
                done += 1
                if res:
                    results.append(res)
                    st = res.get("source") or res.get("status")
                    source_stats[st] += 1
                if done % 50 == 0 or done == len(shard_keys):
                    print(f"  [Shard {args.shard_index}] {done}/{len(shard_keys)} stats={dict(source_stats)}", flush=True)

    out_path = SHARDS_DIR / f"shard_{args.shard_index:02d}.json"
    out_path.write_text(
        json.dumps({"shard_index": args.shard_index, "num_shards": args.num_shards, "stats": dict(source_stats), "items": results}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n=== SHARD {args.shard_index} DONE === {dict(source_stats)}", flush=True)


if __name__ == "__main__":
    main()
