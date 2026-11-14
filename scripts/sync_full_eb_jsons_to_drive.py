"""Stream full scraped eBanglaLibrary books (all chapters & sub-topics) into merged Drive folders.

Uses streaming JSON iteration (scripts/eb_stream.py) over the ~3.74 GB
data/ebanglalibrary_raw.json without loading the whole file into memory.
Matches each book deterministically via eb_upload_state.json (url -> text_file_id),
book_url, or normalized (title, author), and updates its <Clean Book Name>.json
in-place inside its merged Google Drive book folder via `gdrive mutate update`
(or uploads via `gdrive mutate upload` if no text_file_id is present).
Updates data/merged_books.json with the new full-text JSON sizes & IDs.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
SCRATCH_TMP = Path(r"C:\Users\USER\.gemini\antigravity\brain\257bbbd5-d40b-4ea8-a579-659f152212d3\scratch\eb_sync_tmp")
GDRIVE_CLI = r"C:\Users\USER\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"

sys.path.insert(0, str(REPO / "scripts"))
import eb_stream  # noqa: E402
import title_cleaner as tc  # noqa: E402


def atomic_write_json(path: Path, obj: Any, indent: int | None = 2) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(obj, ensure_ascii=False, indent=indent) + ("\n" if indent is not None else "")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def normalize_key(title: str, author: str = "") -> tuple[str, str]:
    cleaned_t = tc.clean_book_stem((title or "").replace("\xa0", " "))
    nt = unicodedata.normalize("NFKC", cleaned_t).lower()
    nt = re.sub(r"[\s\-–—_.,:;!?\'\"`~(){}\[\]<>«»।/|\\]+", "", nt)
    na = unicodedata.normalize("NFKC", (author or "").replace("\xa0", " ")).lower()
    na = re.sub(r"[\s\-–—_.,:;!?\'\"`~(){}\[\]<>«»।/|\\]+", "", na)
    return nt, na


def gd_update_file(fid: str, filepath: Path, timeout: int = 180, retries: int = 5) -> tuple[bool, str]:
    cmd = [
        GDRIVE_CLI, "plugin-cli", "gdrive", "mutate", "update",
        fid, str(filepath), "--mime-type", "application/json", "--json",
    ]
    last_err = ""
    for attempt in range(retries):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            if r.returncode == 0:
                return True, r.stdout.strip()
            last_err = (r.stderr or r.stdout or f"exit {r.returncode}").strip()
        except Exception as e:
            last_err = str(e)
        low = last_err.lower()
        if "403" in low or "quota" in low or "429" in low or "rate" in low:
            time.sleep(min(20.0 * (attempt + 1), 65.0))
        else:
            time.sleep(min(2.0 * (2 ** attempt), 20.0))
    return False, last_err


def gd_upload_file(parent_id: str, filepath: Path, timeout: int = 180, retries: int = 5) -> tuple[bool, str]:
    cmd = [
        GDRIVE_CLI, "plugin-cli", "gdrive", "mutate", "upload",
        str(filepath), "--parent", parent_id, "--mime-type", "application/json", "--json",
    ]
    last_err = ""
    for attempt in range(retries):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            if r.returncode == 0:
                out = r.stdout.strip()
                m = re.search(r'"id"\s*:\s*"([A-Za-z0-9_-]+)"|\(ID:\s*([A-Za-z0-9_-]+)\)', out)
                if m:
                    return True, m.group(1) or m.group(2)
                last_err = f"uploaded but no id parsed: {out[:200]}"
            else:
                last_err = (r.stderr or r.stdout or f"exit {r.returncode}").strip()
        except Exception as e:
            last_err = str(e)
        low = last_err.lower()
        if "403" in low or "quota" in low or "429" in low or "rate" in low:
            time.sleep(min(20.0 * (attempt + 1), 65.0))
        else:
            time.sleep(min(2.0 * (2 ** attempt), 20.0))
    return False, last_err


def build_record_indexes(
    merged: list[dict[str, Any]],
    eb_up_map: dict[str, str],
) -> tuple[dict[str, int], dict[str, int], dict[tuple[str, str], int], dict[str, int]]:
    by_fid: dict[str, int] = {}
    by_url: dict[str, int] = {}
    by_norm_pair: dict[tuple[str, str], int] = {}
    by_norm_title: dict[str, int] = {}

    for i, rec in enumerate(merged):
        tfid = rec.get("text_file_id") or ""
        if tfid:
            by_fid[tfid] = i
        for f in rec.get("files") or []:
            if isinstance(f, dict) and f.get("id") and str(f.get("name", "")).lower().endswith(".json"):
                by_fid.setdefault(f["id"], i)
        burl = (rec.get("book_url") or "").strip()
        if burl:
            by_url[burl] = i
        t_key, a_key = normalize_key(rec.get("title") or rec.get("name") or "", rec.get("author") or "")
        if t_key:
            by_norm_pair.setdefault((t_key, a_key), i)
            by_norm_title.setdefault(t_key, i)

    return by_fid, by_url, by_norm_pair, by_norm_title


def find_merged_index(
    book: dict[str, Any],
    eb_up_map: dict[str, str],
    by_fid: dict[str, int],
    by_url: dict[str, int],
    by_norm_pair: dict[tuple[str, str], int],
    by_norm_title: dict[str, int],
) -> int | None:
    url = (book.get("url") or "").strip()
    if url in eb_up_map:
        old_fid = eb_up_map[url]
        if old_fid in by_fid:
            return by_fid[old_fid]
    if url and url in by_url:
        return by_url[url]
    t_key, a_key = normalize_key(book.get("title") or "", book.get("author") or "")
    if t_key and (t_key, a_key) in by_norm_pair:
        return by_norm_pair[(t_key, a_key)]
    if t_key and t_key in by_norm_title:
        return by_norm_title[t_key]
    raw_t = (book.get("title") or "").replace("\xa0", " ")
    head_t = re.split(r"\s+[-–—]\s+", raw_t, maxsplit=1)[0]
    h_key, _ = normalize_key(head_t, "")
    if h_key and h_key in by_norm_title:
        return by_norm_title[h_key]
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Only verify matching against merged_books.json without touching Drive.")
    ap.add_argument("--only-chapters", action="store_true", help="Only sync books with chapters (skip 0-chapter single-page books already synced).")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    raw_path = DATA / "ebanglalibrary_raw.json"
    merged_path = DATA / "merged_books.json"
    state_path = DATA / "sync_full_eb_state.json"

    merged: list[dict[str, Any]] = json.loads(merged_path.read_text(encoding="utf-8"))
    eb_up_data = json.loads((DATA / "eb_upload_state.json").read_text(encoding="utf-8"))
    eb_up_map: dict[str, str] = eb_up_data.get("uploaded", {})

    state: dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"synced": {}}
    synced: dict[str, dict[str, Any]] = state.setdefault("synced", {})

    by_fid, by_url, by_norm_pair, by_norm_title = build_record_indexes(merged, eb_up_map)

    if args.dry_run:
        total = matched = multi_ch = missing = already_done = 0
        for book in eb_stream.iter_json_array(raw_path):
            total += 1
            chaps = book.get("chapters") or []
            if chaps:
                multi_ch += 1
            if args.only_chapters and not chaps:
                continue
            url = (book.get("url") or "").strip()
            if url in synced:
                already_done += 1
            idx = find_merged_index(book, eb_up_map, by_fid, by_url, by_norm_pair, by_norm_title)
            if idx is not None:
                matched += 1
            else:
                missing += 1
                if missing <= 15:
                    print(f"  UNMATCHED: {book.get('title')!r} | {url}", flush=True)
        print(
            f"DRY-RUN: total={total:,}, multi_ch={multi_ch:,}, matched={matched:,}, "
            f"already_synced={already_done:,}, unmatched={missing:,}",
            flush=True,
        )
        return

    SCRATCH_TMP.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    stats = {"processed": 0, "updated": 0, "uploaded": 0, "skipped_done": 0, "unmatched": 0, "failed": 0}
    dirty_since_save = 0

    def process_one(book: dict[str, Any], rec_idx: int) -> None:
        nonlocal dirty_since_save
        url = (book.get("url") or "").strip()
        rec = merged[rec_idx]
        folder_id = rec.get("folder_id") or ""
        tfid = rec.get("text_file_id") or ""
        clean_name = unicodedata.normalize("NFC", rec.get("name") or rec.get("title") or "book")
        safe_fn = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", clean_name).strip(". ") or f"book_{rec_idx}"

        payload = {
            "source": book.get("source") or "ebanglalibrary.com",
            "post_id": book.get("post_id") or "",
            "url": url,
            "title": book.get("title") or rec.get("title") or "",
            "real_title": rec.get("title") or clean_name,
            "author": rec.get("author") or book.get("author") or "",
            "genres": book.get("genres") or [],
            "cover_url": book.get("cover_url") or rec.get("cover_url") or "",
            "thumbnail_url": book.get("thumbnail_url") or rec.get("thumbnail_url") or "",
            "top_category": rec.get("top_category") or "",
            "leaf_path": rec.get("leaf_path") or "",
            "leaf_category": rec.get("leaf_category") or "",
            "format": "json",
            "intro_content": book.get("intro_content") or "",
            "chapters": book.get("chapters") or [],
            "chapter_count": len(book.get("chapters") or []),
            "full_text_complete": bool(book.get("full_text_complete", False)),
        }

        tid = threading.get_ident()
        wdir = SCRATCH_TMP / f"w_{tid}"
        wdir.mkdir(parents=True, exist_ok=True)
        # In update mode Drive preserves the existing file name; use ASCII id to avoid any path length issue.
        # In upload mode Drive takes the filename from the local file path.
        use_upload = not bool(tfid)
        local_path = (wdir / f"{safe_fn}.json") if use_upload else (wdir / f"{tfid}.json")
        raw_bytes = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        local_path.write_bytes(raw_bytes)
        new_size = len(raw_bytes)

        ok = False
        new_fid = tfid
        action = ""
        err = ""
        if not use_upload:
            ok, msg = gd_update_file(tfid, local_path)
            action = "updated"
            if not ok and folder_id and ("not found" in msg.lower() or "404" in msg):
                use_upload = True
            elif not ok:
                err = msg
        if use_upload:
            if not folder_id:
                ok = False
                err = "missing folder_id"
            else:
                up_path = wdir / f"{safe_fn}.json"
                if up_path != local_path:
                    up_path.write_bytes(raw_bytes)
                ok, res = gd_upload_file(folder_id, up_path)
                action = "uploaded"
                if ok:
                    new_fid = res
                else:
                    err = res
                try:
                    up_path.unlink(missing_ok=True)
                except Exception:
                    pass

        try:
            local_path.unlink(missing_ok=True)
        except Exception:
            pass

        with lock:
            stats["processed"] += 1
            if ok:
                stats[action] += 1
                old_json_size = 0
                files_list = rec.setdefault("files", [])
                updated_entry = False
                for fe in files_list:
                    if isinstance(fe, dict) and (fe.get("id") == tfid or str(fe.get("name", "")).lower().endswith(".json")):
                        old_json_size = int(fe.get("size") or 0)
                        fe["id"] = new_fid
                        fe["name"] = f"{safe_fn}.json"
                        fe["size"] = new_size
                        fe["mimeType"] = "application/json"
                        updated_entry = True
                        break
                if not updated_entry:
                    files_list.append({
                        "id": new_fid,
                        "name": f"{safe_fn}.json",
                        "size": new_size,
                        "mimeType": "application/json",
                    })
                rec["text_file_id"] = new_fid
                rec["book_url"] = url
                if "json" not in (rec.get("formats") or []):
                    rec.setdefault("formats", []).append("json")
                # Keep size consistent if only JSON existed or delta changed
                cur_total = int(rec.get("size") or 0)
                if cur_total == 0 or old_json_size > 0:
                    rec["size"] = max(new_size, cur_total - old_json_size + new_size)
                else:
                    rec["size"] = cur_total + new_size

                synced[url] = {
                    "file_id": new_fid,
                    "folder_id": folder_id,
                    "size": new_size,
                    "chapters": payload["chapter_count"],
                }
                dirty_since_save += 1
            else:
                stats["failed"] += 1
                print(f"  FAIL [{rec_idx}] {clean_name!r} ({tfid}): {err[:180]}", flush=True)

            if dirty_since_save >= 50:
                atomic_write_json(state_path, state, indent=None)
                dirty_since_save = 0
            if stats["processed"] % 100 == 0:
                print(
                    f"Progress: {stats['processed']:,} done | updated={stats['updated']:,} "
                    f"uploaded={stats['uploaded']:,} failed={stats['failed']:,}",
                    flush=True,
                )

    max_inflight = max(args.workers * 3, 24)
    in_flight: set[concurrent.futures.Future] = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for book in eb_stream.iter_json_array(raw_path):
            chaps = book.get("chapters") or []
            if args.only_chapters and not chaps:
                continue
            url = (book.get("url") or "").strip()
            if url in synced:
                stats["skipped_done"] += 1
                continue
            rec_idx = find_merged_index(book, eb_up_map, by_fid, by_url, by_norm_pair, by_norm_title)
            if rec_idx is None:
                stats["unmatched"] += 1
                print(f"  UNMATCHED: {book.get('title')!r} | {url}", flush=True)
                continue
            fut = pool.submit(process_one, book, rec_idx)
            in_flight.add(fut)
            if len(in_flight) >= max_inflight:
                done, in_flight = concurrent.futures.wait(in_flight, return_when=concurrent.futures.FIRST_COMPLETED)
                for df in done:
                    df.result()

        for df in concurrent.futures.as_completed(in_flight):
            df.result()

    atomic_write_json(state_path, state, indent=None)
    atomic_write_json(merged_path, merged, indent=2)
    print(f"FINISHED sync_full_eb_jsons_to_drive: {stats}", flush=True)


if __name__ == "__main__":
    main()
