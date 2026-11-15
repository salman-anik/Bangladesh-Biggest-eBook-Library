#!/usr/bin/env python3
"""
Reorganize oversized Drive leaf folders (>200 books) into Author & Alphabetical subfolders,
and fix known classic literature misclassifications (e.g., Bishad Sindhu -> Literature/Novels).

Usage:
  python -u scripts/reorganize_large_leaves.py --plan-only
  python -u scripts/reorganize_large_leaves.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
MERGED_FILE = ROOT / "data" / "merged_books.json"
CLEAN_FOLDERS_FILE = ROOT / "data" / "clean_folders.json"
STATE_FILE = ROOT / "data" / "reorg_subfolders_state.json"

GDRIVE_BIN = shutil.which("gdrive") or shutil.which("gdrive.exe") or shutil.which("gdrive.cmd") or "gdrive"
LEAF_THRESHOLD = 200
AUTHOR_MIN_BOOKS = 5

_PRINT_LOCK = threading.Lock()


def log(msg: str) -> None:
    with _PRINT_LOCK:
        print(msg, flush=True)


def run_gdrive(args: list[str], retries: int = 5) -> str:
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
        if "403" in err or "Quota" in err or "rateLimit" in err or "429" in err:
            wait = min(65, 15 * (attempt + 1))
            log(f"  WARN rate-limit on {' '.join(args[:3])}, sleeping {wait}s...")
            time.sleep(wait)
            continue
        if attempt < retries - 1:
            time.sleep(3 * (attempt + 1))
            continue
        raise RuntimeError(f"gdrive failed ({res.returncode}): {err.strip()}")
    raise RuntimeError(f"gdrive exhausted retries: {' '.join(args)}")


def sanitize_folder_name(name: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', " ", name).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:90].strip() or "Other"


def bangla_alpha_bucket(title: str) -> str:
    s = re.sub(r'^[\s"\'“”‘’\(\)\[\]\{\}\-–—.,:;!?]+', "", title or "").strip()
    if not s:
        return "0-9 & Other"
    ch = s[0]
    c_low = ch.lower()
    if "a" <= c_low <= "f":
        return "English (A-F)"
    if "g" <= c_low <= "m":
        return "English (G-M)"
    if "n" <= c_low <= "s":
        return "English (N-S)"
    if "t" <= c_low <= "z":
        return "English (T-Z)"
    if ch in "অআআইঈউঊঋএঐওঔ":
        return "অ-ঔ"
    if ch in "কখগঘঙ":
        return "ক-ঙ"
    if ch in "চছজঝঞ":
        return "চ-ঞ"
    if ch in "টঠডঢণড়ঢ়":
        return "ট-ণ"
    if ch in "তথদধন":
        return "ত-ন"
    if ch in "পফব":
        return "প-ব"
    if ch in "ভম":
        return "ভ-ম"
    if ch in "যরলশষসহয়ংঃঁ":
        return "য-হ"
    return "0-9 & Other"


def apply_classification_fixes(books: list[dict]) -> list[dict]:
    fixes = []
    for b in books:
        title = b.get("title") or b.get("name") or ""
        if "বিষাদ সিন্ধু" in title and b.get("top_category") == "Religion":
            old_leaf = b.get("leaf_path")
            b["top_category"] = "Literature"
            b["leaf_path"] = "Literature/Novels"
            b["leaf_category"] = "Novels"
            fixes.append((b["folder_id"], old_leaf, "Literature/Novels", title))
    return fixes


def plan_subfolders(books: list[dict]) -> tuple[dict[str, dict], dict[tuple[str, str], int]]:
    by_leaf: dict[str, list[dict]] = defaultdict(list)
    for b in books:
        by_leaf[b["leaf_path"]].append(b)

    large_leaves = {lp: lst for lp, lst in by_leaf.items() if len(lst) > LEAF_THRESHOLD}
    assignments: dict[str, dict] = {}
    bucket_counts: dict[tuple[str, str], int] = Counter()

    for lp, lst in large_leaves.items():
        auth_counts = Counter()
        for b in lst:
            a = (b.get("author") or "").strip()
            if a and not a.startswith("Various") and not a.startswith("NCTB"):
                auth_counts[a] += 1

        for b in lst:
            a = (b.get("author") or "").strip()
            if a and auth_counts.get(a, 0) >= AUTHOR_MIN_BOOKS:
                sub = sanitize_folder_name(a)
            else:
                sub = bangla_alpha_bucket(b.get("title") or b.get("name") or "")
            assignments[b["folder_id"]] = {
                "leaf_path": lp,
                "subfolder": sub,
                "book": b,
            }
            bucket_counts[(lp, sub)] += 1

    return assignments, bucket_counts


def run_batch_moves(ops: list[dict], workers: int = 2) -> tuple[int, int]:
    if not ops:
        return 0, 0
    batch_size = 50
    chunks = [ops[i : i + batch_size] for i in range(0, len(ops), batch_size)]
    done = 0
    failed = 0

    def exec_chunk(idx: int, chunk: list[dict]) -> tuple[int, int]:
        for attempt in range(5):
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
                json.dump(chunk, tf, ensure_ascii=False)
                tf_path = tf.name
            try:
                out = run_gdrive(["mutate", "batch", "--file", tf_path, "--json"], retries=3)
                # Verify individual op statuses if JSON returned
                try:
                    res_list = json.loads(out)
                    retry_ops = []
                    ok_cnt = 0
                    for op, r in zip(chunk, res_list if isinstance(res_list, list) else []):
                        if isinstance(r, dict) and r.get("error"):
                            retry_ops.append(op)
                        else:
                            ok_cnt += 1
                    if not retry_ops:
                        return len(chunk), 0
                    chunk = retry_ops
                    time.sleep(15 * (attempt + 1))
                    continue
                except json.JSONDecodeError:
                    return len(chunk), 0
            except Exception as e:
                err_s = str(e)
                is_quota = any(k in err_s for k in ("403", "Quota", "rateLimit", "429"))
                if attempt < 4 and is_quota:
                    wait = min(65, 20 * (attempt + 1))
                    log(f"  WARN batch {idx+1}/{len(chunks)} quota ({err_s[:100]}), retrying in {wait}s...")
                    time.sleep(wait)
                elif attempt < 2 and not is_quota:
                    log(f"  WARN batch {idx+1}/{len(chunks)} failed ({err_s[:120]}), retrying in 3s...")
                    time.sleep(3)
                else:
                    log(f"  ERR batch {idx+1}/{len(chunks)} failed permanently: {e}")
                    return 0, len(chunk)
            finally:
                try:
                    os.unlink(tf_path)
                except OSError:
                    pass
        return 0, len(chunk)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(exec_chunk, i, ch): i for i, ch in enumerate(chunks)}
        for fut in as_completed(futs):
            ok, bad = fut.result()
            done += ok
            failed += bad
            if (done + failed) % 500 < batch_size or done + failed == len(ops):
                log(f"  [move] {done}/{len(ops)} moved (failed={failed})")
    return done, failed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    books = json.loads(MERGED_FILE.read_text(encoding="utf-8"))
    clean_folders = json.loads(CLEAN_FOLDERS_FILE.read_text(encoding="utf-8"))
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {"moved": {}, "subfolders": {}}

    fixes = apply_classification_fixes(books)
    log(f"Classification fixes: {len(fixes)}")
    for fid, old_lp, new_lp, title in fixes:
        log(f"  - {title}: {old_lp} -> {new_lp}")

    assignments, bucket_counts = plan_subfolders(books)
    unique_subfolders = sorted(bucket_counts.keys())
    log(f"\nLarge leaves (> {LEAF_THRESHOLD} books): {len({lp for lp, _ in unique_subfolders})}")
    log(f"Books to organize into subfolders: {len(assignments)}")
    log(f"Unique subfolders needed: {len(unique_subfolders)}")
    log("Largest 15 resulting subfolders:")
    for (lp, sub), cnt in sorted(bucket_counts.items(), key=lambda x: -x[1])[:15]:
        log(f"  {cnt:4d}  {lp} / {sub}")

    missing_leaf_ids = [lp for lp in {lp for lp, _ in unique_subfolders} if lp not in clean_folders]
    if missing_leaf_ids:
        raise RuntimeError(f"Missing Drive IDs in clean_folders.json for: {missing_leaf_ids}")

    if args.plan_only:
        log("\n--plan-only complete. No Drive mutations executed.")
        return

    # Step 1: Pre-scan existing subfolders in the large leaves so we never duplicate
    large_leaf_paths = sorted({lp for lp, _ in unique_subfolders})
    existing_by_leaf: dict[str, dict[str, str]] = {}
    log(f"\nScanning {len(large_leaf_paths)} large leaves for existing subfolders...")
    for lp in large_leaf_paths:
        pid = clean_folders[lp]
        try:
            ls_out = run_gdrive(["readonly", "ls", pid, "--json", "--max", "0"])
            items = json.loads(ls_out) if ls_out.strip() else []
            fmap = {}
            for it in items:
                if it.get("mimeType") == "application/vnd.google-apps.folder":
                    fmap[it["name"]] = it["id"]
            existing_by_leaf[lp] = fmap
        except Exception as e:
            log(f"  WARN ls {lp}: {e}")
            existing_by_leaf[lp] = {}

    to_create = []
    for lp, sub in unique_subfolders:
        key = f"{lp}/{sub}"
        if key in clean_folders or key in state["subfolders"]:
            continue
        existing_id = existing_by_leaf.get(lp, {}).get(sub)
        if existing_id:
            clean_folders[key] = existing_id
            state["subfolders"][key] = existing_id
        else:
            to_create.append((lp, sub, key, clean_folders[lp]))

    log(f"Creating {len(to_create)} missing subfolders in Drive...")
    if to_create:
        def create_one(item: tuple[str, str, str, str]) -> tuple[str, str]:
            lp, sub, key, parent_id = item
            out = run_gdrive(["mutate", "mkdir", sub, "--parent", parent_id, "--json"])
            fid = None
            if out.strip().startswith("{"):
                data = json.loads(out)
                fid = data.get("id") or data.get("folder_id")
            if not fid:
                m = re.search(r'\b([A-Za-z0-9_-]{20,})\b', out)
                if m:
                    fid = m.group(1)
            if not fid:
                ls_out = run_gdrive(["readonly", "ls", parent_id, "--json", "--max", "0"])
                for it in json.loads(ls_out):
                    if it.get("mimeType") == "application/vnd.google-apps.folder" and it.get("name") == sub:
                        fid = it["id"]
                        break
            if not fid:
                raise RuntimeError(f"mkdir did not return id for {key}: {out!r}")
            return key, fid

        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(create_one, item): item for item in to_create}
            created_cnt = 0
            for fut in as_completed(futs):
                key, fid = fut.result()
                clean_folders[key] = fid
                state["subfolders"][key] = fid
                created_cnt += 1
                if created_cnt % 25 == 0 or created_cnt == len(to_create):
                    log(f"  [mkdir] {created_cnt}/{len(to_create)}")
                    CLEAN_FOLDERS_FILE.write_text(json.dumps(clean_folders, ensure_ascii=False, indent=2), encoding="utf-8")
                    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        CLEAN_FOLDERS_FILE.write_text(json.dumps(clean_folders, ensure_ascii=False, indent=2), encoding="utf-8")
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # Ensure state subfolders merged into clean_folders
    for k, fid in state["subfolders"].items():
        clean_folders.setdefault(k, fid)

    # Step 2: Move book folders into their target subfolder
    ops = []
    for fid, info in assignments.items():
        lp = info["leaf_path"]
        sub = info["subfolder"]
        key = f"{lp}/{sub}"
        target_parent = clean_folders[key]
        if state["moved"].get(fid) == target_parent:
            continue
        ops.append({"op": "move", "fileId": fid, "toParent": target_parent})

    # Also ensure any fixed books NOT in large leaves (if any) move to their new leaf
    for fid, old_lp, new_lp, _ in fixes:
        if fid not in assignments:
            target_parent = clean_folders[new_lp]
            if state["moved"].get(fid) != target_parent:
                ops.append({"op": "move", "fileId": fid, "toParent": target_parent})

    log(f"\nExecuting {len(ops)} book-folder move ops on Drive (workers={args.workers})...")
    done, failed = run_batch_moves(ops, workers=args.workers)
    if failed == 0:
        for op in ops:
            state["moved"][op["fileId"]] = op["toParent"]
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # Step 3: Update merged_books.json with subfolder field
    for b in books:
        fid = b["folder_id"]
        if fid in assignments:
            b["subfolder"] = assignments[fid]["subfolder"]
        else:
            b["subfolder"] = None

    MERGED_FILE.write_text(json.dumps(books, ensure_ascii=False, indent=2), encoding="utf-8")
    CLEAN_FOLDERS_FILE.write_text(json.dumps(clean_folders, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\nDone! Moved={done}, Failed={failed}. Updated data/merged_books.json & data/clean_folders.json.")


if __name__ == "__main__":
    main()
