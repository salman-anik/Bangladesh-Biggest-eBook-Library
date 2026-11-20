"""Multi-threaded, idempotent, resumable Google Drive reorganization & renaming applier.

Reads reports/dry_run_plan.json.gz and executes only safe, non-destructive operations:
  - creates target library folders (never duplicates existing folders)
  - moves + renames unique valid eBooks in a single PATCH per file
  - quarantines broken HTML redirects, corrupted files, and MD5 duplicates to 08_Review_and_Unclassified/
  - moves non-ebook assets (JSONs, covers, legacy reports, archives) to 00_Library_Management/ / 08_Review_and_Unclassified/
  - creates Author & Series Drive shortcuts (zero physical copies)
  - verifies legacy top-level folders have 0 remaining files before reversible trashed=true

Prints REMAINING=<n> so GitHub Actions can auto-chain resume runs if max-minutes is reached.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import csv
import gzip
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_api as d  # noqa: E402

ROOT = os.environ.get("LIBRARY_ROOT_ID", "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq")

STATIC_ARCHITECTURE_FOLDERS = [
    "00_Library_Management",
    "00_Library_Management/Master_Catalog",
    "00_Library_Management/Reports",
    "00_Library_Management/Reports/Archived_Legacy_Reports",
    "00_Library_Management/Reports/Archived_Legacy_Docs",
    "00_Library_Management/Metadata",
    "00_Library_Management/Metadata/eBanglaLibrary_JSON",
    "00_Library_Management/Cover_Images",
    "01_Bangla_Books",
    "01_Bangla_Books/উপন্যাস",
    "01_Bangla_Books/গল্প ও ছোটগল্প",
    "01_Bangla_Books/কবিতা",
    "01_Bangla_Books/প্রবন্ধ",
    "01_Bangla_Books/নাটক",
    "01_Bangla_Books/জীবনী ও আত্মজীবনী",
    "01_Bangla_Books/ইতিহাস",
    "01_Bangla_Books/বিজ্ঞান ও প্রযুক্তি",
    "01_Bangla_Books/শিশু-কিশোর সাহিত্য",
    "01_Bangla_Books/ভ্রমণ",
    "01_Bangla_Books/অনুবাদ ও বিদেশী সাহিত্য",
    "01_Bangla_Books/থ্রিলার, রহস্য ও গোয়েন্দা",
    "01_Bangla_Books/ধর্ম ও দর্শন",
    "01_Bangla_Books/ভাষা ও ব্যাকরণ",
    "01_Bangla_Books/অন্যান্য",
    "02_English_Books",
    "02_English_Books/Fiction",
    "02_English_Books/Non_Fiction",
    "02_English_Books/Science",
    "02_English_Books/Technology",
    "02_English_Books/History",
    "02_English_Books/Philosophy",
    "02_English_Books/Biography",
    "02_English_Books/Others",
    "03_Education_and_Textbooks",
    "03_Education_and_Textbooks/School",
    *[f"03_Education_and_Textbooks/School/Class_{i:02d}" for i in range(1, 11)],
    "03_Education_and_Textbooks/HSC_Class_11-12",
    "03_Education_and_Textbooks/Madrasa",
    "03_Education_and_Textbooks/University",
    "03_Education_and_Textbooks/Admission",
    "03_Education_and_Textbooks/Professional_Exams",
    "04_Islamic_Books",
    "04_Islamic_Books/কুরআন ও তাফসির",
    "04_Islamic_Books/হাদিস",
    "04_Islamic_Books/ফিকহ",
    "04_Islamic_Books/আকিদা",
    "04_Islamic_Books/সীরাত",
    "04_Islamic_Books/ইসলামিক ইতিহাস",
    "04_Islamic_Books/ইসলামিক সাহিত্য",
    "04_Islamic_Books/অন্যান্য",
    "05_Authors_and_Scholars",
    "05_Authors_and_Scholars/A-Z",
    "05_Authors_and_Scholars/বাংলা বর্ণমালা",
    "06_Series_and_Collections",
    "07_Reference_and_Research",
    "07_Reference_and_Research/Dictionaries",
    "07_Reference_and_Research/Encyclopedias",
    "07_Reference_and_Research/Research_Papers",
    "07_Reference_and_Research/Magazines",
    "07_Reference_and_Research/Journals",
    "08_Review_and_Unclassified",
    "08_Review_and_Unclassified/Needs_Manual_Review",
    "08_Review_and_Unclassified/Exact_Duplicates_Quarantine",
    "08_Review_and_Unclassified/Broken_HTML_Redirects",
    "08_Review_and_Unclassified/Corrupted_or_Empty",
    "08_Review_and_Unclassified/Archives_ZIP",
]


def scan_live_tree() -> tuple[dict[str, str], dict[str, dict], set[tuple[str, str]], dict[str, dict]]:
    """List all non-trashed items once and map folders, files, and existing shortcuts under ROOT."""
    t0 = time.time()
    all_items: dict[str, dict] = {}
    for i, f in enumerate(d.list_all("trashed = false")):
        all_items[f["id"]] = f
        if i and i % 25000 == 0:
            print(f"  live scan: {i} items ({time.time()-t0:.0f}s)", flush=True)
    all_items[ROOT] = d.get(ROOT)

    children: dict[str, list[str]] = collections.defaultdict(list)
    for f in all_items.values():
        for p in f.get("parents") or []:
            children[p].append(f["id"])

    folder_path_to_id: dict[str, str] = {"": ROOT}
    file_live: dict[str, dict] = {}
    existing_shortcuts: set[tuple[str, str]] = set()
    q = collections.deque([(ROOT, "")])
    seen_folders = {ROOT}

    while q:
        cur_id, cur_path = q.popleft()
        for cid in children.get(cur_id, []):
            f = all_items[cid]
            mt = f["mimeType"]
            name = f["name"]
            if mt == d.FOLDER:
                fpath = f"{cur_path}/{name}" if cur_path else name
                if cid not in seen_folders:
                    seen_folders.add(cid)
                    folder_path_to_id.setdefault(fpath, cid)
                    q.append((cid, fpath))
            elif mt == d.SHORTCUT:
                tid = (f.get("shortcutDetails") or {}).get("targetId", "")
                if tid:
                    existing_shortcuts.add((cur_id, tid))
                file_live[cid] = f
            else:
                file_live[cid] = f

    print(
        f"Live scan ready in {time.time()-t0:.0f}s: {len(folder_path_to_id)-1} folders, "
        f"{len(file_live)} files, {len(existing_shortcuts)} shortcuts",
        flush=True,
    )
    return folder_path_to_id, file_live, existing_shortcuts, all_items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="reports/dry_run_plan.json.gz")
    ap.add_argument("--phase", default="all",
                    choices=["all", "folders", "ebooks", "quarantine", "assets", "shortcuts", "trash_empty_legacy"])
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--max-minutes", type=float, default=290.0)
    ap.add_argument("--out-dir", default="out/apply")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    deadline = t_start + args.max_minutes * 60.0

    with gzip.open(args.plan, "rt", encoding="utf-8") as gz:
        plan = json.load(gz)

    folder_path_to_id, file_live, existing_shortcuts, _ = scan_live_tree()
    folder_lock = threading.Lock()

    def ensure_folder(path: str) -> str:
        path = path.strip("/")
        if not path:
            return ROOT
        if path in folder_path_to_id:
            return folder_path_to_id[path]
        with folder_lock:
            if path in folder_path_to_id:
                return folder_path_to_id[path]
            parts = path.split("/")
            cur_id = ROOT
            built = ""
            for part in parts:
                built = f"{built}/{part}" if built else part
                if built in folder_path_to_id:
                    cur_id = folder_path_to_id[built]
                else:
                    created = d.mkdir(part, cur_id)
                    cur_id = created["id"]
                    folder_path_to_id[built] = cur_id
            return cur_id

    # Collect all target folders required by the plan
    needed_folders = set(STATIC_ARCHITECTURE_FOLDERS)
    for op in plan.get("ebook_moves_and_renames", []):
        needed_folders.add(op["target_folder"])
    for qk in ("quarantine_broken_html", "quarantine_corrupted", "quarantine_duplicates"):
        for item in plan.get(qk, []):
            needed_folders.add(item["target_folder"])
    for m in plan.get("non_ebook_moves", []):
        needed_folders.add(m["target_folder"])
    for sc in plan.get("shortcuts", []):
        needed_folders.add(sc["shortcut_folder"])

    print(f"Ensuring {len(needed_folders)} target folders exist...", flush=True)
    for fp in sorted(needed_folders, key=lambda s: (s.count("/"), s)):
        ensure_folder(fp)
    (out_dir / "folder_id_map.json").write_text(
        json.dumps(folder_path_to_id, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"Target folders ready ({len(folder_path_to_id)-1} total).", flush=True)

    if args.phase == "folders":
        print("REMAINING=0", flush=True)
        return

    failures_map: dict[tuple[str, str], dict] = {}
    fail_lock = threading.Lock()
    stats = collections.Counter()
    log_fh = open(out_dir / "ops_log.jsonl", "a", encoding="utf-8")
    log_lock = threading.Lock()

    def record_log(obj: dict):
        with log_lock:
            log_fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def run_move_rename_task(task: dict) -> str:
        if time.time() > deadline:
            return "deferred"
        fid = task["id"]
        target_fid = folder_path_to_id[task["target_folder"]]
        target_name = task["target_name"]
        live = file_live.get(fid)
        if live is None:
            try:
                live = d.get(fid, "id,name,parents,trashed")
                if live.get("trashed"):
                    return "skipped_trashed"
            except Exception as e:
                with fail_lock:
                    failures_map[(task["kind"], fid)] = {"phase": task["kind"], "id": fid, "name": target_name, "error": f"missing:{e}"}
                return "error"
        cur_parents = live.get("parents") or []
        cur_name = live.get("name", "")
        need_mv = target_fid not in cur_parents
        need_rn = cur_name != target_name
        if not need_mv and not need_rn:
            with fail_lock:
                failures_map.pop((task["kind"], fid), None)
            return "skipped_already_done"
        try:
            d.move_and_rename(
                fid,
                new_name=target_name if need_rn else None,
                add_parent=target_fid if need_mv else None,
                remove_parent=",".join(cur_parents) if need_mv and cur_parents else None,
            )
            with fail_lock:
                failures_map.pop((task["kind"], fid), None)
            record_log({"op": task["kind"], "id": fid, "to": f"{task['target_folder']}/{target_name}"})
            return "applied"
        except Exception as e:
            with fail_lock:
                failures_map[(task["kind"], fid)] = {"phase": task["kind"], "id": fid, "name": target_name, "error": str(e)[:250]}
            return "error"

    def execute_batch(label: str, items: list[dict]):
        pending = []
        skipped = 0
        for it in items:
            fid = it["id"]
            target_fid = folder_path_to_id[it["target_folder"]]
            live = file_live.get(fid)
            if live and target_fid in (live.get("parents") or []) and live.get("name") == it["target_name"]:
                skipped += 1
            else:
                pending.append(it)
        stats[f"{label}_already_done"] += skipped
        print(f"[{label}] total={len(items)} already_done={skipped} pending={len(pending)}", flush=True)
        if not pending:
            return 0
        t0 = time.time()
        done_now = 0
        deferred = 0
        retry_items: list[dict] = []
        with cf.ThreadPoolExecutor(args.workers) as ex:
            for i, (it, res) in enumerate(zip(pending, ex.map(run_move_rename_task, pending)), 1):
                if res == "applied":
                    stats[f"{label}_applied"] += 1
                    done_now += 1
                elif res == "deferred":
                    stats[f"{label}_deferred"] += 1
                    deferred += 1
                elif res == "error":
                    retry_items.append(it)
                else:
                    stats[f"{label}_{res}"] += 1
                if i % 500 == 0 or i == len(pending):
                    log_fh.flush()
                    print(
                        f"  [{label}] {i}/{len(pending)} ({time.time()-t0:.0f}s) "
                        f"applied={done_now} retry_q={len(retry_items)} deferred={deferred}",
                        flush=True,
                    )
        if retry_items and time.time() <= deadline:
            print(f"  [{label}] retrying {len(retry_items)} transient failures with workers=2...", flush=True)
            with cf.ThreadPoolExecutor(2) as ex2:
                for res in ex2.map(run_move_rename_task, retry_items):
                    stats[f"{label}_{res}"] += 1
        elif retry_items:
            stats[f"{label}_error"] += len(retry_items)
        return deferred

    remaining = 0

    if args.phase in ("all", "ebooks"):
        eb_tasks = [
            {
                "kind": "ebook",
                "id": op["drive_file_id"],
                "target_folder": op["target_folder"],
                "target_name": op["target_name"],
            }
            for op in plan.get("ebook_moves_and_renames", [])
        ]
        remaining += execute_batch("ebooks", eb_tasks)

    if args.phase in ("all", "quarantine") and time.time() <= deadline:
        q_tasks = []
        for item in plan.get("quarantine_broken_html", []):
            q_tasks.append({"kind": "quarantine_html", "id": item["drive_file_id"],
                            "target_folder": item["target_folder"], "target_name": item["target_name"]})
        for item in plan.get("quarantine_corrupted", []):
            q_tasks.append({"kind": "quarantine_corrupt", "id": item["drive_file_id"],
                            "target_folder": item["target_folder"], "target_name": item["target_name"]})
        for item in plan.get("quarantine_duplicates", []):
            q_tasks.append({"kind": "quarantine_dup", "id": item["dup_id"],
                            "target_folder": item["target_folder"], "target_name": item["target_name"]})
        remaining += execute_batch("quarantine", q_tasks)
    elif args.phase == "all" and time.time() > deadline:
        remaining += (
            len(plan.get("quarantine_broken_html", []))
            + len(plan.get("quarantine_corrupted", []))
            + len(plan.get("quarantine_duplicates", []))
        )

    if args.phase in ("all", "assets") and time.time() <= deadline:
        a_tasks = [
            {
                "kind": "asset",
                "id": m["drive_file_id"],
                "target_folder": m["target_folder"],
                "target_name": m["name"],
            }
            for m in plan.get("non_ebook_moves", [])
        ]
        remaining += execute_batch("assets", a_tasks)
    elif args.phase == "all" and time.time() > deadline:
        remaining += len(plan.get("non_ebook_moves", []))

    if args.phase in ("all", "shortcuts") and time.time() <= deadline:
        sc_items = plan.get("shortcuts", [])
        sc_pending = []
        sc_skipped = 0
        for sc in sc_items:
            pfid = folder_path_to_id[sc["shortcut_folder"]]
            if (pfid, sc["target_file_id"]) in existing_shortcuts:
                sc_skipped += 1
            else:
                sc_pending.append((pfid, sc["target_file_id"], sc["shortcut_name"]))
        stats["shortcuts_already_done"] += sc_skipped
        print(f"[shortcuts] total={len(sc_items)} already_done={sc_skipped} pending={len(sc_pending)}", flush=True)

        def run_sc(item: tuple[str, str, str]) -> str:
            if time.time() > deadline:
                return "deferred"
            pfid, tid, nm = item
            try:
                d.shortcut(tid, pfid, nm)
                with fail_lock:
                    failures_map.pop(("shortcut", f"{pfid}:{tid}"), None)
                return "applied"
            except Exception as e:
                with fail_lock:
                    failures_map[("shortcut", f"{pfid}:{tid}")] = {"phase": "shortcut", "id": tid, "name": nm, "error": str(e)[:250]}
                return "error"

        t0 = time.time()
        sc_retry: list[tuple[str, str, str]] = []
        with cf.ThreadPoolExecutor(args.workers) as ex:
            for i, (sc_it, res) in enumerate(zip(sc_pending, ex.map(run_sc, sc_pending)), 1):
                if res == "error":
                    sc_retry.append(sc_it)
                else:
                    stats[f"shortcuts_{res}"] += 1
                if res == "deferred":
                    remaining += 1
                if i % 500 == 0 or i == len(sc_pending):
                    print(
                        f"  [shortcuts] {i}/{len(sc_pending)} ({time.time()-t0:.0f}s) "
                        f"applied={stats['shortcuts_applied']} retry_q={len(sc_retry)}",
                        flush=True,
                    )
        if sc_retry and time.time() <= deadline:
            print(f"  [shortcuts] retrying {len(sc_retry)} transient failures with workers=2...", flush=True)
            with cf.ThreadPoolExecutor(2) as ex2:
                for res in ex2.map(run_sc, sc_retry):
                    stats[f"shortcuts_{res}"] += 1
        elif sc_retry:
            stats["shortcuts_error"] += len(sc_retry)
    elif args.phase == "all" and time.time() > deadline:
        remaining += len(plan.get("shortcuts", []))

    if args.phase in ("all", "trash_empty_legacy") and remaining == 0 and time.time() <= deadline:
        print("[trash_empty_legacy] Re-scanning Drive to verify 0 remaining files in legacy roots...", flush=True)
        _, _, _, all_live = scan_live_tree()
        children_live: dict[str, list[str]] = collections.defaultdict(list)
        for f in all_live.values():
            for p in f.get("parents") or []:
                children_live[p].append(f["id"])

        for leg in plan.get("legacy_root_folders", []):
            lid, lname = leg["id"], leg["name"]
            if lid not in all_live:
                stats["legacy_already_gone"] += 1
                continue
            # Count any non-folder items recursively inside this legacy root
            q = collections.deque([lid])
            seen = {lid}
            files_left = 0
            while q:
                cur = q.popleft()
                for cid in children_live.get(cur, []):
                    cf_item = all_live[cid]
                    if cf_item["mimeType"] == d.FOLDER:
                        if cid not in seen:
                            seen.add(cid)
                            q.append(cid)
                    else:
                        files_left += 1
            if files_left == 0:
                d.trash(lid)
                stats["legacy_roots_trashed"] += 1
                print(f"  Trashed verified-empty legacy root: {lname} ({lid}, {len(seen)} empty folders)", flush=True)
            else:
                stats["legacy_roots_skipped_nonempty"] += 1
                failures_map[("trash_legacy", lid)] = {"phase": "trash_legacy", "id": lid, "name": lname, "error": f"nonempty:{files_left}_files_left"}
                print(f"  REFUSED trash of {lname}: still contains {files_left} files!", flush=True)

    failures = list(failures_map.values())
    log_fh.close()
    with open(out_dir / "failures.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["phase", "id", "name", "error"])
        w.writeheader()
        w.writerows(failures)

    summary = {
        "phase": args.phase,
        "elapsed_sec": round(time.time() - t_start),
        "remaining": remaining,
        "stats": dict(stats),
        "failure_count": len(failures),
    }
    (out_dir / "apply_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"REMAINING={remaining}", flush=True)


if __name__ == "__main__":
    main()
