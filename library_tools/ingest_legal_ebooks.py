"""Multi-threaded Legal eBook Downloader, Validator & Google Drive Importer.

Reads verified candidates from reports/legal_discovery_candidates.csv (plus
optional live Project Gutenberg feed from Ubuntu runner), validates every
downloaded PDF/EPUB, deduplicates against live Drive MD5 checksums and titles,
uploads with clean 'Title — Author.ext' naming, and records exact source &
license provenance.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_drive_reorg as adr  # noqa: E402
import build_dry_run_plan as bdp  # noqa: E402
import discover_legal_ebooks as dle  # noqa: E402
import drive_api as d  # noqa: E402
import taxonomy_rules as tr  # noqa: E402

UA = "BangladeshBiggestEBookLibraryBot/1.0 (+https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library)"
MIN_BYTES = 5000


def fetch_gutenberg_from_runner(existing_keys: set[str], en_limit: int = 120) -> list[dict]:
    """Try Project Gutenberg official catalog CSV (fast from cloud runner) or Gutendex fallback."""
    out: list[dict] = []
    try:
        req = urllib.request.Request("https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", "replace")
        for r in csv.DictReader(io.StringIO(raw)):
            if r.get("Type") != "Text":
                continue
            langs = {x.strip().lower() for x in (r.get("Language") or "").split(";")}
            gid = (r.get("Text#") or "").strip()
            title = (r.get("Title") or "").replace("\n", " ").split(";")[0].strip()[:150]
            raw_auth = (r.get("Authors") or "Unknown").split(";")[0].strip()
            raw_auth = re.sub(r",?\s*\d{4}-(?:\d{4})?$", "", raw_auth).strip()
            if "," in raw_auth:
                p = [x.strip() for x in raw_auth.split(",", 1)]
                author = f"{p[1]} {p[0]}".strip()
            else:
                author = raw_auth or "Unknown"
            if not gid or not title:
                continue
            subj = ((r.get("Subjects") or "") + " " + (r.get("Bookshelves") or "")).lower()
            dl = f"https://www.gutenberg.org/ebooks/{gid}.epub.noimages"
            src = f"https://www.gutenberg.org/ebooks/{gid}"
            if "bn" in langs:
                out.append({
                    "title": title, "author": author, "language": "Bangla",
                    "category": "01_Bangla_Books", "subcategory": "অন্যান্য", "series": "",
                    "format": "EPUB", "source_name": "Project Gutenberg",
                    "source_url": src, "download_url": dl,
                    "license": "Public Domain (Project Gutenberg)", "copyright_status": "Public Domain",
                    "already_in_library": str(dle.is_present(title, existing_keys)),
                })
            elif "en" in langs and len([x for x in out if x["language"] == "English"]) < en_limit and int(gid) <= 2500:
                if "philosophy" in subj or "ethics" in subj: sub = "Philosophy"
                elif "history" in subj: sub = "History"
                elif "biography" in subj or "autobiography" in subj: sub = "Biography"
                elif any(k in subj for k in ("science", "physics", "biology", "mathematics")): sub = "Science"
                elif any(k in subj for k in ("fiction", "literature", "novel", "poetry", "drama")): sub = "Fiction"
                else: sub = "Non_Fiction"
                out.append({
                    "title": title, "author": author, "language": "English",
                    "category": "02_English_Books", "subcategory": sub, "series": "",
                    "format": "EPUB", "source_name": "Project Gutenberg",
                    "source_url": src, "download_url": dl,
                    "license": "Public Domain (Project Gutenberg)", "copyright_status": "Public Domain",
                    "already_in_library": str(dle.is_present(title, existing_keys)),
                })
        print(f"Gutenberg CSV fetched: {len(out)} items", flush=True)
        return out
    except Exception as e:
        print(f"Gutenberg CSV skipped ({e}); trying Gutendex...", flush=True)

    try:
        url = "https://gutendex.com/books?languages=en"
        while url and len(out) < en_limit:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            for b in data.get("results", []):
                if len(out) >= en_limit:
                    break
                fmts = b.get("formats") or {}
                epub_url = fmts.get("application/epub+zip") or fmts.get("application/epub3+zip")
                if not epub_url or b.get("copyright") is True:
                    continue
                authors = b.get("authors") or []
                raw_auth = authors[0]["name"] if authors else "Unknown"
                author = " ".join(reversed([x.strip() for x in raw_auth.split(",", 1)])) if "," in raw_auth else raw_auth
                title = (b.get("title") or "").split(";")[0].split("\n")[0].strip()[:150]
                blob = (" ".join(b.get("subjects") or []) + " " + " ".join(b.get("bookshelves") or [])).lower()
                if "philosophy" in blob: sub = "Philosophy"
                elif "history" in blob: sub = "History"
                elif "biography" in blob: sub = "Biography"
                elif any(k in blob for k in ("science", "physics", "biology", "math")): sub = "Science"
                elif any(k in blob for k in ("fiction", "novel", "poetry", "drama")): sub = "Fiction"
                else: sub = "Non_Fiction"
                out.append({
                    "title": title, "author": author, "language": "English",
                    "category": "02_English_Books", "subcategory": sub, "series": "",
                    "format": "EPUB", "source_name": "Project Gutenberg",
                    "source_url": f"https://www.gutenberg.org/ebooks/{b['id']}",
                    "download_url": epub_url,
                    "license": "Public Domain (Project Gutenberg)", "copyright_status": "Public Domain",
                    "already_in_library": str(dle.is_present(title, existing_keys)),
                })
            url = data.get("next")
        print(f"Gutendex EN fetched: {len(out)} items", flush=True)
    except Exception as e:
        print(f"Gutendex skipped ({e})", flush=True)
    return out


def validate_file(path: Path, expected_fmt: str) -> tuple[bool, str, str]:
    """Return (ok, real_ext, md5_hex_or_reason)."""
    size = path.stat().st_size
    if size < MIN_BYTES:
        return False, expected_fmt.lower(), f"too_small:{size}"
    with open(path, "rb") as fh:
        head = fh.read(4096)
    low = head[:600].lower()
    if b"<!doctype html" in low or b"<html" in low:
        return False, expected_fmt.lower(), "html_error_page"

    fmt = expected_fmt.upper()
    if head.startswith(b"%PDF") or b"%PDF-" in head[:1024]:
        real_ext = "pdf"
    elif head.startswith(b"PK\x03\x04"):
        real_ext = "epub"
        try:
            with zipfile.ZipFile(path, "r") as zf:
                bad = zf.testzip()
                if bad is not None:
                    return False, "epub", f"bad_zip_member:{bad}"
                if not any(n.endswith(".opf") for n in zf.namelist()):
                    return False, "epub", "no_opf_in_epub"
        except Exception as e:
            return False, "epub", f"invalid_epub:{e.__class__.__name__}"
    else:
        return False, fmt.lower(), f"unexpected_magic:{head[:8]!r}"

    h = hashlib.md5()
    with open(path, "rb") as fh:
        while chunk := fh.read(1024 * 1024):
            h.update(chunk)
    return True, real_ext, h.hexdigest()


def download_to_temp(url: str, dest: Path, retries: int = 3) -> None:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as fh:
                while chunk := resp.read(256 * 1024):
                    fh.write(chunk)
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2.0 * (attempt + 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="reports/legal_discovery_candidates.csv")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--include-gutenberg", action="store_true")
    ap.add_argument("--max-minutes", type=float, default=240.0)
    ap.add_argument("--out-dir", default="out/legal_ingest")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + args.max_minutes * 60.0

    rows = list(csv.DictReader(open(args.candidates, encoding="utf-8-sig")))

    # Scan live Drive inventory once for MD5 & filename deduplication + folder map
    folder_path_to_id, file_live, existing_shortcuts, _ = adr.scan_live_tree()
    existing_md5s = {f.get("md5Checksum") for f in file_live.values() if f.get("md5Checksum")}
    existing_names: dict[str, set[str]] = collections.defaultdict(set)
    existing_title_keys: set[str] = set()
    for f in file_live.values():
        nm = f.get("name", "")
        nk = dle.norm_key(re.sub(r"\.[A-Za-z0-9]{1,5}$", "", nm))
        if len(nk) >= 3:
            existing_title_keys.add(nk)
        for p in f.get("parents") or []:
            existing_names[p].add(nm.lower())

    if args.include_gutenberg:
        gut = fetch_gutenberg_from_runner(existing_title_keys, en_limit=120)
        seen_ta = {(dle.norm_key(r["title"]), dle.norm_key(r["author"])) for r in rows}
        for g in gut:
            k = (dle.norm_key(g["title"]), dle.norm_key(g["author"]))
            if k not in seen_ta:
                seen_ta.add(k)
                rows.append(g)

    candidates = [r for r in rows if str(r.get("already_in_library", "")).lower() != "true"]
    print(f"Candidates to consider (not marked already_in_library): {len(candidates)}", flush=True)

    lock = threading.Lock()
    folder_lock = threading.Lock()

    def ensure_folder(path: str) -> str:
        path = path.strip("/")
        if path in folder_path_to_id:
            return folder_path_to_id[path]
        with folder_lock:
            if path in folder_path_to_id:
                return folder_path_to_id[path]
            parts = path.split("/")
            cur = adr.ROOT
            built = ""
            for p in parts:
                built = f"{built}/{p}" if built else p
                if built in folder_path_to_id:
                    cur = folder_path_to_id[built]
                else:
                    res = d.mkdir(p, cur)
                    cur = res["id"]
                    folder_path_to_id[built] = cur
            return cur

    # Index existing author folders under 05_Authors_and_Scholars/
    author_folder_index: dict[str, str] = {}
    for fp, fid in folder_path_to_id.items():
        if fp.startswith("05_Authors_and_Scholars/বাংলা বর্ণমালা/") and fp.count("/") == 2:
            author_folder_index[fp.split("/")[2]] = fid
        elif fp.startswith("05_Authors_and_Scholars/A-Z/") and fp.count("/") == 3:
            author_folder_index[fp.split("/")[3]] = fid

    ingested: list[dict] = []
    failed: list[dict] = []
    skipped = collections.Counter()

    tmp_root = Path(tempfile.mkdtemp(prefix="legal_ebooks_"))

    def process_one(idx_row: tuple[int, dict]) -> None:
        i, c = idx_row
        if time.time() > deadline:
            skipped["time_limit"] += 1
            return
        title = tr.nfc(c["title"])
        lang = c["language"]
        author = tr.canonicalize_author(c["author"], lang)
        target_folder = f"{c['category']}/{c['subcategory']}".strip("/")
        parent_id = ensure_folder(target_folder)

        fmt = (c.get("format") or "PDF").lower()
        target_name = bdp.format_target_filename(title, author, fmt)
        with lock:
            if target_name.lower() in existing_names[parent_id]:
                skipped["already_in_folder_name"] += 1
                return
            if dle.is_present(title, existing_title_keys):
                skipped["already_in_live_titles"] += 1
                return

        local_file = tmp_root / f"dl_{i}.{fmt}"
        try:
            download_to_temp(c["download_url"], local_file)
            ok, real_ext, val_res = validate_file(local_file, fmt)
            if not ok:
                with lock:
                    failed.append({"title": title, "author": author, "source_url": c["source_url"],
                                   "download_url": c["download_url"], "reason": val_res})
                return

            md5 = val_res
            final_name = bdp.format_target_filename(title, author, real_ext)
            with lock:
                if md5 in existing_md5s:
                    skipped["duplicate_md5"] += 1
                    return
                if final_name.lower() in existing_names[parent_id]:
                    skipped["already_in_folder_name"] += 1
                    return
                existing_md5s.add(md5)
                existing_names[parent_id].add(final_name.lower())
                existing_title_keys.add(dle.norm_key(title))

            mime = "application/epub+zip" if real_ext == "epub" else "application/pdf"
            uploaded = d.upload_resumable(local_file, final_name, parent_id, mime_type=mime)
            new_fid = uploaded["id"]
            fsize = int(uploaded.get("size") or local_file.stat().st_size)

            # Create author shortcut if author folder exists in 05_Authors_and_Scholars
            auth_fid = author_folder_index.get(bdp.sanitize_filename(author, 80))
            if auth_fid:
                with lock:
                    need_sc = (auth_fid, new_fid) not in existing_shortcuts
                    if need_sc:
                        existing_shortcuts.add((auth_fid, new_fid))
                if need_sc:
                    try:
                        d.shortcut(new_fid, auth_fid, final_name)
                    except Exception:
                        pass

            rec = {
                "title": title,
                "author": author,
                "language": lang,
                "category": c["category"],
                "subcategory": c["subcategory"],
                "series": c.get("series", ""),
                "format": real_ext.upper(),
                "file_size": fsize,
                "md5": md5,
                "drive_file_id": new_fid,
                "drive_path": f"{target_folder}/{final_name}",
                "source_name": c["source_name"],
                "source_url": c["source_url"],
                "download_url": c["download_url"],
                "license": c["license"],
                "copyright_status": c["copyright_status"],
                "date_added": time.strftime("%Y-%m-%d"),
            }
            with lock:
                ingested.append(rec)
        except Exception as e:
            with lock:
                failed.append({"title": title, "author": author, "source_url": c["source_url"],
                               "download_url": c["download_url"], "reason": str(e)[:200]})
        finally:
            if local_file.exists():
                local_file.unlink(missing_ok=True)

    t0 = time.time()
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for i, _ in enumerate(ex.map(process_one, enumerate(candidates)), 1):
            if i % 50 == 0 or i == len(candidates):
                print(
                    f"  legal ingest {i}/{len(candidates)} ({time.time()-t0:.0f}s) "
                    f"uploaded={len(ingested)} skipped={sum(skipped.values())} failed={len(failed)}",
                    flush=True,
                )

    shutil.rmtree(tmp_root, ignore_errors=True)
    with open(out_dir / "ingested_books.jsonl", "w", encoding="utf-8") as fh:
        for rec in ingested:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(out_dir / "failed_downloads.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["title", "author", "source_url", "download_url", "reason"])
        w.writeheader()
        w.writerows(failed)

    summary = {
        "candidates_checked": len(candidates),
        "uploaded_count": len(ingested),
        "uploaded_bytes": sum(r["file_size"] for r in ingested),
        "skipped": dict(skipped),
        "failed_count": len(failed),
        "by_source_uploaded": dict(collections.Counter(r["source_name"] for r in ingested)),
        "by_language_uploaded": dict(collections.Counter(r["language"] for r in ingested)),
        "elapsed_sec": round(time.time() - t0),
    }
    (out_dir / "legal_ingest_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
