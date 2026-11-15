#!/usr/bin/env python3
"""Verify and trash empty category/leaf/subfolder containers in Bangladesh-Biggest-eBook-Library."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
MERGED_FILE = ROOT / "data" / "merged_books.json"
CLEAN_FOLDERS_FILE = ROOT / "data" / "clean_folders.json"
GDRIVE_BIN = shutil.which("gdrive") or shutil.which("gdrive.exe") or shutil.which("gdrive.cmd") or "gdrive"


def run_gdrive(args: list[str], retries: int = 4) -> str:
    cmd = [GDRIVE_BIN] + args
    for attempt in range(retries):
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=(os.name == "nt"),
        )
        if res.returncode == 0:
            return res.stdout
        err = (res.stderr or "") + (res.stdout or "")
        if any(k in err for k in ("403", "Quota", "rateLimit", "429")):
            time.sleep(min(60, 15 * (attempt + 1)))
            continue
        if attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
            continue
        raise RuntimeError(f"gdrive failed ({res.returncode}): {err.strip()}")
    raise RuntimeError(f"gdrive exhausted retries: {' '.join(args)}")


def is_folder_empty(fid: str) -> bool:
    out = run_gdrive(["readonly", "ls", fid, "--json", "--max", "5"])
    items = json.loads(out) if out.strip() else []
    return len(items) == 0


def trash_batch(ops: list[dict]) -> int:
    if not ops:
        return 0
    done = 0
    for i in range(0, len(ops), 50):
        chunk = ops[i : i + 50]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(chunk, tf, ensure_ascii=False)
            p = tf.name
        try:
            run_gdrive(["mutate", "batch", "--file", p])
            done += len(chunk)
        finally:
            try:
                os.unlink(p)
            except OSError:
                pass
    return done


def main() -> None:
    books = json.loads(MERGED_FILE.read_text(encoding="utf-8"))
    cf = json.loads(CLEAN_FOLDERS_FILE.read_text(encoding="utf-8"))

    used = Counter()
    for b in books:
        used[b["top_category"]] += 1
        parts = b["leaf_path"].split("/")
        if len(parts) == 3:
            used[f"{parts[0]}/{parts[1]}"] += 1
        used[b["leaf_path"]] += 1
        if b.get("subfolder"):
            used[f"{b['leaf_path']}/{b['subfolder']}"] += 1

    candidates = [(k, fid) for k, fid in cf.items() if used.get(k, 0) == 0]
    print(f"Candidate 0-book folders: {len(candidates)}", flush=True)

    # Pass 1: deepest folders first (depth >= 1, i.e., leaves & subfolders)
    deep = [(k, fid) for k, fid in candidates if "/" in k]
    top = [(k, fid) for k, fid in candidates if "/" not in k]

    empty_deep: list[tuple[str, str]] = []
    non_empty: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(is_folder_empty, fid): (k, fid) for k, fid in deep}
        for fut in as_completed(futs):
            k, fid = futs[fut]
            if fut.result():
                empty_deep.append((k, fid))
            else:
                non_empty.append((k, fid))

    print(f"Verified empty deep folders: {len(empty_deep)} | Non-empty skipped: {len(non_empty)}", flush=True)
    trashed_deep = trash_batch([{"op": "trash", "fileId": fid} for _, fid in empty_deep])
    print(f"Trashed deep folders: {trashed_deep}", flush=True)
    for k, _ in empty_deep:
        cf.pop(k, None)

    # Pass 2: top-level 0-book folders (e.g. Others and Unclassified) after children trashed
    empty_top: list[tuple[str, str]] = []
    for k, fid in top:
        if is_folder_empty(fid):
            empty_top.append((k, fid))
        else:
            non_empty.append((k, fid))
    print(f"Verified empty top folders: {len(empty_top)}", flush=True)
    trashed_top = trash_batch([{"op": "trash", "fileId": fid} for _, fid in empty_top])
    print(f"Trashed top folders: {trashed_top}", flush=True)
    for k, _ in empty_top:
        cf.pop(k, None)

    CLEAN_FOLDERS_FILE.write_text(json.dumps(cf, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated data/clean_folders.json -> {len(cf)} active folders.", flush=True)
    if non_empty:
        print("Skipped non-empty folders:")
        for k, fid in non_empty[:20]:
            print(f"  - {k} ({fid})")


if __name__ == "__main__":
    main()
