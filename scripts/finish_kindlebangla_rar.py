#!/usr/bin/env python3
"""
Finish remaining KindleBangla Drive folders + RAR archives cleanly without worker starvation.
Splits small (<=10 MB, 8 workers, 240s timeout) vs large (>10 MB, 2 workers, 900s timeout)
so 70-192 MB comic/anthology .rar files complete reliably without resetting.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import clean_classifier as cc
import title_cleaner as tc

GDRIVE_CLI = r"C:\Users\USER\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"
UNRAR_EXE = r"C:\Users\USER\.gemini\antigravity\scratch\tools\unrar\UnRAR.exe"
KB_COVERS_FOLDER_ID = "1QELhzYgRpAkieE9tnEAgM2B4PQsmx84m"
ROOT_DRIVE_ID = "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
FMT_PRIORITY = {".epub": 0, ".pdf": 1, ".mobi": 2, ".azw3": 3}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

_LOCK = threading.Lock()
_FOLDER_LOCK = threading.Lock()


def gd_run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [GDRIVE_CLI, "plugin-cli", "gdrive", *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def gd_json(args: list[str], timeout: int = 120, retries: int = 3) -> dict | list | None:
    full_args = [*args, "--json"] if "--json" not in args else args
    for attempt in range(retries):
        try:
            res = gd_run(full_args, timeout=timeout)
            out = (res.stdout or "").strip()
            if res.returncode == 0 and out:
                try:
                    return json.loads(out)
                except json.JSONDecodeError:
                    # mutate mkdir / cp / upload emit human text "(ID: <id>)" even with --json
                    m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", out)
                    if m:
                        return {"id": m.group(1)}
            err = (res.stderr or "") + out
            if "notFound" in err:
                return {"_not_found": True}
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def gd_ensure_folder(clean_folders: dict[str, str], rel_path: str) -> str:
    rel_path = rel_path.strip("/")
    with _FOLDER_LOCK:
        if rel_path in clean_folders:
            return clean_folders[rel_path]
        parts = rel_path.split("/")
        cur_path = ""
        parent_id = ROOT_DRIVE_ID
        for part in parts:
            cur_path = f"{cur_path}/{part}" if cur_path else part
            if cur_path in clean_folders:
                parent_id = clean_folders[cur_path]
                continue
            # Check Drive first before mkdir to avoid duplicate folders
            ls = gd_json(["readonly", "ls", parent_id], timeout=45)
            found_id = None
            if isinstance(ls, list):
                for it in ls:
                    if it.get("mimeType") == "application/vnd.google-apps.folder" and unicodedata.normalize("NFC", it.get("name", "")) == unicodedata.normalize("NFC", part):
                        found_id = it["id"]
                        break
            if not found_id:
                mk = gd_json(["mutate", "mkdir", part, "--parent", parent_id], timeout=45)
                if isinstance(mk, dict) and mk.get("id"):
                    found_id = mk["id"]
            if not found_id:
                raise RuntimeError(f"Failed creating folder {cur_path}")
            clean_folders[cur_path] = found_id
            parent_id = found_id
        return parent_id


def download_cover_fallback(url: str, dst_dir: Path, stem: str) -> Path | None:
    if not url:
        return None
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext not in IMG_EXTS:
        ext = ".webp"
    safe_stem = tc.sanitize_filename(stem) or "cover"
    out = dst_dir / f"{safe_stem}{ext}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
        if len(data) > 500:
            out.write_bytes(data)
            return out
    except Exception:
        pass
    return None


def upload_cover(cover_path: Path | None, cover_name_stem: str, book_rec: dict, url_key: str, copied_covers: dict) -> tuple[str, str]:
    with _LOCK:
        if url_key in copied_covers and copied_covers[url_key]:
            cid = copied_covers[url_key]
            return cid, f"https://drive.google.com/file/d/{cid}/view"
    if not cover_path or not cover_path.exists():
        return "", ""
    ext = cover_path.suffix.lower() or ".jpg"
    safe_name = f"{tc.sanitize_filename(cover_name_stem) or 'cover'}{ext}"
    with tempfile.TemporaryDirectory() as td:
        staged = Path(td) / safe_name
        shutil.copy2(cover_path, staged)
        up = gd_json(["mutate", "upload", str(staged), "--parent", KB_COVERS_FOLDER_ID], timeout=120)
        if isinstance(up, dict) and up.get("id"):
            cid = up["id"]
            with _LOCK:
                copied_covers[url_key] = cid
            return cid, f"https://drive.google.com/file/d/{cid}/view"
    return "", ""


def _atomic_write_json(path: Path, obj: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def save_state(state_path: Path, state: dict, extra_path: Path, extra_books: list, covers_path: Path, book_covers: dict, folders_path: Path, clean_folders: dict) -> None:
    with _LOCK:
        _atomic_write_json(state_path, state)
        _atomic_write_json(extra_path, extra_books)
        _atomic_write_json(covers_path, book_covers)
        _atomic_write_json(folders_path, clean_folders)


def record_uploaded_book(
    book_meta: dict,
    file_obj: dict,
    clean_filename: str,
    leaf: str,
    src_fid: str,
    cov_id: str,
    cov_link: str,
    extra_books: list,
    book_covers: dict,
    seen_sids: set[str],
) -> None:
    new_id = file_obj["id"]
    size = int(file_obj.get("size") or 0)
    mime = file_obj.get("mimeType") or (
        "application/epub+zip" if clean_filename.lower().endswith(".epub") else "application/pdf"
    )
    parts = leaf.split("/")
    title = tc.fix_unicode_nfc(book_meta.get("title") or "")
    author = tc.fix_unicode_nfc(book_meta.get("author") or "")
    url = book_meta.get("url") or ""
    cov_url = book_meta.get("cover_url") or ""
    th_url = book_meta.get("thumbnail_url") or cov_url
    sid = f"kb:{src_fid}:{Path(clean_filename).stem[:40]}" if src_fid else f"kb:{new_id}"

    rec = {
        "source_id": sid,
        "file_id": new_id,
        "name": clean_filename,
        "size": size,
        "mimeType": mime,
        "top_category": parts[0],
        "leaf_path": leaf,
        "leaf_category": parts[-1],
        "subfolder": None,
        "author": author or "Various / Unknown",
        "publication": "Kindle Bangla (kindlebangla.com)",
        "link": f"https://drive.google.com/file/d/{new_id}/view",
        "cover_url": cov_url,
        "thumbnail_url": th_url,
        "cover_drive_id": cov_id,
        "internal_title": title or Path(clean_filename).stem,
    }
    cov_rec = {
        "title": title or Path(clean_filename).stem,
        "author": author or "Various / Unknown",
        "source": "kindlebangla.com",
        "book_url": url,
        "cover_url": cov_url,
        "thumbnail_url": th_url,
        "cover_drive_id": cov_id,
        "cover_drive_link": cov_link or (f"https://drive.google.com/file/d/{cov_id}/view" if cov_id else ""),
    }
    with _LOCK:
        if not any(b.get("file_id") == new_id for b in extra_books):
            extra_books.append(rec)
        seen_sids.add(sid)
        book_covers[new_id] = cov_rec


def process_folder_item(item: dict, dir_files: list[dict], clean_folders: dict, state: dict, extra_books: list, book_covers: dict, seen_sids: set[str]) -> tuple[str, str, int]:
    url = item.get("url", "")
    title = tc.fix_unicode_nfc(item.get("title") or "")
    author = tc.fix_unicode_nfc(item.get("author") or "")
    cats = item.get("categories") or []

    ebooks: list[dict] = []
    images: list[dict] = []
    for f in dir_files:
        name = f.get("name", "")
        ext = Path(name).suffix.lower()
        if ext in FMT_PRIORITY:
            ebooks.append(f)
        elif ext in IMG_EXTS:
            images.append(f)

    if not ebooks:
        return url, "", 0

    # Pick best format per normalized stem (epub > pdf > mobi > azw3)
    best_by_stem: dict[str, dict] = {}
    for f in ebooks:
        p = Path(f["name"])
        ext = p.suffix.lower()
        k = tc.fold_bengali_key(p.stem)
        prev = best_by_stem.get(k)
        if prev is None or FMT_PRIORITY[ext] < FMT_PRIORITY[Path(prev["name"]).suffix.lower()]:
            best_by_stem[k] = f

    cov_id = state["copied_covers"].get(url, "")
    cov_link = f"https://drive.google.com/file/d/{cov_id}/view" if cov_id else ""
    if not cov_id and images:
        img = images[0]
        img_ext = Path(img["name"]).suffix.lower() or ".jpg"
        cov_name = f"{tc.sanitize_filename(title or Path(img['name']).stem) or 'cover'}{img_ext}"
        cp = gd_json(["mutate", "cp", img["id"], cov_name, "--parent", KB_COVERS_FOLDER_ID], timeout=60)
        if isinstance(cp, dict) and cp.get("id"):
            cov_id = cp["id"]
            cov_link = f"https://drive.google.com/file/d/{cov_id}/view"
            with _LOCK:
                state["copied_covers"][url] = cov_id

    if not cov_id and item.get("cover_url"):
        with tempfile.TemporaryDirectory() as td:
            cpath = download_cover_fallback(item["cover_url"], Path(td), title or "cover")
            cov_id, cov_link = upload_cover(cpath, title or "cover", item, url, state["copied_covers"])

    added = 0
    first_fid = ""
    for f in best_by_stem.values():
        ext = Path(f["name"]).suffix.lower()
        raw_stem = Path(f["name"]).stem
        # If multiple books inside folder, keep raw_stem + author; single book prefers catalog title
        b_title = title if len(best_by_stem) == 1 and title else tc.strip_watermarks_and_noise(raw_stem)
        clean_name = tc.clean_book_filename(f"{b_title}{ext}", author=author, known_title=b_title)
        leaf = cc.classify_clean_leaf(title=clean_name, author=author, genres=cats, publication="Kindle Bangla")
        parent_id = gd_ensure_folder(clean_folders, f"pdf/{leaf}")
        cp = gd_json(["mutate", "cp", f["id"], clean_name, "--parent", parent_id], timeout=90)
        if isinstance(cp, dict) and cp.get("id"):
            cp.setdefault("size", f.get("size") or 0)
            cp.setdefault("mimeType", f.get("mimeType") or "")
            if not first_fid:
                first_fid = cp["id"]
            record_uploaded_book(item, cp, clean_name, leaf, f["id"], cov_id, cov_link, extra_books, book_covers, seen_sids)
            added += 1
    if added:
        with _LOCK:
            state["processed_urls"][url] = first_fid
    return url, first_fid, added


def process_rar_item(item: dict, timeout_dl: int, clean_folders: dict, state: dict, extra_books: list, book_covers: dict, seen_sids: set[str]) -> tuple[str, str, int, str]:
    url = item.get("url", "")
    fid = item.get("drive_file_id", "")
    title = tc.fix_unicode_nfc(item.get("title") or "")
    author = tc.fix_unicode_nfc(item.get("author") or "")
    cats = item.get("categories") or []

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        arc = tdp / "archive.rar"
        ok_dl = False
        for attempt in range(3):
            try:
                if arc.exists():
                    arc.unlink()
                res = gd_run(["readonly", "download", fid, "--out", str(arc)], timeout=timeout_dl)
                if res.returncode == 0 and arc.exists() and arc.stat().st_size > 100:
                    ok_dl = True
                    break
                err_txt = (res.stderr or "") + (res.stdout or "")
                if "notFound" in err_txt or "404" in err_txt:
                    return url, "", 0, "404"
            except subprocess.TimeoutExpired:
                pass
            time.sleep(2 * (attempt + 1))

        if not ok_dl:
            return url, "", 0, "download_failed"

        ext_dir = tdp / "ext"
        ext_dir.mkdir(exist_ok=True)
        # Extract using official UnRAR.exe (-p- disables password prompt); fallback to Python zipfile if actually a zip
        ur = subprocess.run([UNRAR_EXE, "x", "-o+", "-p-", "-inul", str(arc), str(ext_dir)], stdin=subprocess.DEVNULL, capture_output=True, timeout=180)
        if ur.returncode != 0:
            try:
                import zipfile
                with zipfile.ZipFile(arc) as zf:
                    zf.extractall(ext_dir)
            except Exception:
                return url, "", 0, f"extract_failed:{ur.returncode}"

        all_files = [p for p in ext_dir.rglob("*") if p.is_file()]
        ebooks = [p for p in all_files if p.suffix.lower() in FMT_PRIORITY]
        images = [p for p in all_files if p.suffix.lower() in IMG_EXTS and not p.stem.lower().startswith("thumb")]
        if not ebooks:
            return url, "", 0, "no_ebooks_in_archive"

        best_by_stem: dict[str, Path] = {}
        for p in ebooks:
            k = tc.fold_bengali_key(p.stem)
            prev = best_by_stem.get(k)
            if prev is None or FMT_PRIORITY[p.suffix.lower()] < FMT_PRIORITY[prev.suffix.lower()]:
                best_by_stem[k] = p

        # Match image by stem or default to first image or cover_url
        img_by_stem: dict[str, Path] = {tc.fold_bengali_key(p.stem): p for p in images}
        default_img = images[0] if images else download_cover_fallback(item.get("cover_url") or "", tdp, title or "cover")

        added = 0
        first_fid = ""
        for k, bpath in best_by_stem.items():
            ext = bpath.suffix.lower()
            raw_stem = tc.fix_unicode_nfc(bpath.stem)
            b_title = title if len(best_by_stem) == 1 and title else tc.strip_watermarks_and_noise(raw_stem)
            # Strip trailing generic "(1)" or series duplicate author inside b_title
            clean_name = tc.clean_book_filename(f"{b_title}{ext}", author=author, known_title=b_title)
            leaf = cc.classify_clean_leaf(title=clean_name, author=author, genres=cats, publication="Kindle Bangla")
            parent_id = gd_ensure_folder(clean_folders, f"pdf/{leaf}")

            cov_src = img_by_stem.get(k) or default_img
            cov_url_key = url if len(best_by_stem) == 1 else f"{url}#{Path(clean_name).stem}"
            cov_id, cov_link = upload_cover(cov_src, Path(clean_name).stem, item, cov_url_key, state["copied_covers"])

            staged = tdp / clean_name
            if staged != bpath:
                shutil.copy2(bpath, staged)
            up = gd_json(["mutate", "upload", str(staged), "--parent", parent_id], timeout=300)
            if isinstance(up, dict) and up.get("id"):
                up.setdefault("size", staged.stat().st_size)
                if not first_fid:
                    first_fid = up["id"]
                rec_meta = dict(item)
                rec_meta["title"] = b_title
                record_uploaded_book(rec_meta, up, clean_name, leaf, fid, cov_id, cov_link, extra_books, book_covers, seen_sids)
                added += 1

        if added:
            with _LOCK:
                state["processed_urls"][url] = first_fid
        return url, first_fid, added, "ok"


def main() -> None:
    cat = json.loads((DATA / "kindlebangla_catalog.json").read_text(encoding="utf-8"))
    state_p = DATA / "kb_ingest_state.json"
    extra_p = DATA / "extra_books.json"
    covers_p = DATA / "book_covers.json"
    folders_p = DATA / "clean_folders.json"

    state = json.loads(state_p.read_text(encoding="utf-8"))
    extra_books = json.loads(extra_p.read_text(encoding="utf-8"))
    book_covers = json.loads(covers_p.read_text(encoding="utf-8"))
    clean_folders = json.loads(folders_p.read_text(encoding="utf-8"))

    seen_sids = {str(b.get("source_id", "")) for b in extra_books}
    done_urls = set(state.get("processed_urls", {}).keys())
    pending = [x for x in cat if x.get("url") and x["url"] not in done_urls]
    print(f"Pending KindleBangla items: {len(pending)} (already done: {len(done_urls)})", flush=True)

    folders = [x for x in pending if x.get("drive_folder_id")]
    files = [x for x in pending if x.get("drive_file_id")]

    total_added = 0
    errors: list[tuple[str, str]] = []

    # 1. Stream & copy remaining Drive folders
    if folders:
        print(f"Step 1: Processing {len(folders)} remaining KindleBangla Drive folders...", flush=True)
        with tempfile.TemporaryDirectory() as td:
            di = Path(td) / "d_in.jsonl"
            do = Path(td) / "d_out.jsonl"
            di.write_text("\n".join(json.dumps({"id": x["drive_folder_id"]}) for x in folders), encoding="utf-8")
            res_ls = subprocess.run([GDRIVE_CLI, "plugin-cli", "gdrive", "readonly", "stream", "ls", "-i", str(di), "-o", str(do), "-c", "16", "--max", "500"], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90, check=False)
            print(f"  stream ls rc={res_ls.returncode}", flush=True)
            dir_map: dict[str, list[dict]] = {}
            if do.exists():
                for ln in do.read_text(encoding="utf-8").splitlines():
                    if not ln.strip(): continue
                    row = json.loads(ln)
                    if row.get("_ok"):
                        dir_map[row["id"]] = row.get("data") or []
        for idx, x in enumerate(folders, 1):
            dfiles = dir_map.get(x["drive_folder_id"], [])
            url, fid, added = process_folder_item(x, dfiles, clean_folders, state, extra_books, book_covers, seen_sids)
            total_added += added
            print(f"  Folder {idx}/{len(folders)}: {x.get('title','')[:35]} -> added={added}", flush=True)
        save_state(state_p, state, extra_p, extra_books, covers_p, book_covers, folders_p, clean_folders)
        print(f"  Folders complete: added {total_added} books.", flush=True)

    # 2. Stream info on all remaining files to split small vs large RARs
    if files:
        print(f"Step 2: Streaming file sizes for {len(files)} remaining archives...", flush=True)
        size_map: dict[str, int] = {}
        err_404: set[str] = set()
        with tempfile.TemporaryDirectory() as td:
            fi = Path(td) / "f_in.jsonl"
            fo = Path(td) / "f_out.jsonl"
            fi.write_text("\n".join(json.dumps({"id": x["drive_file_id"]}) for x in files), encoding="utf-8")
            res_inf = subprocess.run([GDRIVE_CLI, "plugin-cli", "gdrive", "readonly", "stream", "info", "-i", str(fi), "-o", str(fo), "-c", "16"], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, check=False)
            print(f"  stream info rc={res_inf.returncode}", flush=True)
            if fo.exists():
                for ln in fo.read_text(encoding="utf-8").splitlines():
                    if not ln.strip(): continue
                    row = json.loads(ln)
                    if row.get("_ok") and isinstance(row.get("data"), dict):
                        size_map[row["data"]["id"]] = int(row["data"].get("size") or 0)
                    else:
                        err_404.add(row.get("id", ""))

        live_files = [x for x in files if x["drive_file_id"] not in err_404]
        for x in files:
            if x["drive_file_id"] in err_404:
                errors.append((x.get("title", ""), "404_not_found_upstream"))

        small_rars = [x for x in live_files if size_map.get(x["drive_file_id"], 0) <= 10 * 1024 * 1024]
        large_rars = [x for x in live_files if size_map.get(x["drive_file_id"], 0) > 10 * 1024 * 1024]
        large_rars.sort(key=lambda x: size_map.get(x["drive_file_id"], 0))
        print(f"  Split: {len(small_rars)} small (<=10MB, 8 workers) + {len(large_rars)} large (>10MB, 2 workers) + {len(err_404)} upstream 404", flush=True)

        done_cnt = 0
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(process_rar_item, x, 240, clean_folders, state, extra_books, book_covers, seen_sids) for x in small_rars]
            for fut in as_completed(futs):
                url, fid, added, status = fut.result()
                done_cnt += 1
                total_added += added
                if status != "ok":
                    errors.append((url, status))
                if done_cnt % 25 == 0 or done_cnt == len(small_rars):
                    print(f"  Small RARs {done_cnt}/{len(small_rars)} (total added {total_added})", flush=True)
                    save_state(state_p, state, extra_p, extra_books, covers_p, book_covers, folders_p, clean_folders)

        done_lg = 0
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = [ex.submit(process_rar_item, x, 900, clean_folders, state, extra_books, book_covers, seen_sids) for x in large_rars]
            for fut in as_completed(futs):
                url, fid, added, status = fut.result()
                done_lg += 1
                total_added += added
                if status != "ok":
                    errors.append((url, status))
                print(f"  Large RAR {done_lg}/{len(large_rars)} status={status} added={added} (total added {total_added})", flush=True)
                if done_lg % 5 == 0 or done_lg == len(large_rars):
                    save_state(state_p, state, extra_p, extra_books, covers_p, book_covers, folders_p, clean_folders)

    save_state(state_p, state, extra_p, extra_books, covers_p, book_covers, folders_p, clean_folders)
    kb_total = sum(1 for b in extra_books if str(b.get("source_id", "")).startswith("kb:"))
    print(f"KindleBangla Complete! Added this run: {total_added} | Total kb extra_books: {kb_total} | processed_urls: {len(state['processed_urls'])} | errors/404: {len(errors)}", flush=True)
    for title_or_url, reason in errors[:25]:
        print(f"  note: {title_or_url} -> {reason}", flush=True)


if __name__ == "__main__":
    main()
