#!/usr/bin/env python3
"""Cloud Phase 1: Create mirrored category folder hierarchy inside
Library Management/Cover Images (1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj)
and move + rename all 8,020 existing covers cleanly in-place via Drive API.
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CATALOG = ROOT / "catalog"
sys.path.insert(0, str(ROOT / "library_tools"))
import drive_api as dapi  # noqa: E402

MGMT_COVERS_ID = "1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj"


def scan_cover_tree() -> tuple[dict[str, str], dict[str, dict]]:
    """Scan existing folders & files inside MGMT_COVERS_ID only."""
    folder_ids: dict[str, str] = {"": MGMT_COVERS_ID}
    file_parents: dict[str, dict] = {}
    queue: list[tuple[str, str]] = [("", MGMT_COVERS_ID)]

    while queue:
        next_q: list[tuple[str, str]] = []
        def scan_one(item: tuple[str, str]) -> tuple[str, str, list[dict]]:
            path, fid = item
            kids = list(dapi.list_all(q=f"'{fid}' in parents and trashed = false", fields="id,name,mimeType,parents"))
            return path, fid, kids

        with ThreadPoolExecutor(max_workers=12) as ex:
            for path, fid, kids in ex.map(scan_one, queue):
                for k in kids:
                    if k.get("mimeType") == dapi.FOLDER:
                        kp = f"{path}/{k['name']}" if path else k["name"]
                        folder_ids[kp] = k["id"]
                        next_q.append((kp, k["id"]))
                    else:
                        file_parents[k["id"]] = k
        queue = next_q
    return folder_ids, file_parents


def main() -> None:
    plan_data = json.loads((DATA / "existing_covers_audit_plan.json").read_text(encoding="utf-8"))
    assignments: dict[str, dict] = plan_data["assignments"]
    mc = json.loads((CATALOG / "master_catalog.json").read_text(encoding="utf-8"))

    # Collect all folder paths needed for BOTH existing covers and full 22,099 catalog books
    needed_leaf_paths: set[str] = {a["target_folder"] for a in assignments.values()}
    for b in mc:
        cat_folder = f"{b['category']}/{b['subcategory']}" if b.get("subcategory") else b["category"]
        needed_leaf_paths.add(cat_folder)

    all_prefixes: set[str] = set()
    for p in needed_leaf_paths:
        parts = p.split("/")
        for i in range(1, len(parts) + 1):
            all_prefixes.add("/".join(parts[:i]))

    print(f"Scanning existing tree inside Cover Images ({MGMT_COVERS_ID})...", flush=True)
    folder_ids, live_files = scan_cover_tree()
    print(f"Existing tree: {len(folder_ids)-1} subfolders, {len(live_files)} files.", flush=True)

    # Create missing folders level by level cleanly
    max_depth = max(p.count("/") for p in all_prefixes)
    created_folders = 0
    for depth in range(max_depth + 1):
        to_create = sorted(p for p in all_prefixes if p.count("/") == depth and p not in folder_ids)
        if not to_create:
            continue
        print(f"Creating {len(to_create)} folders at depth {depth}...", flush=True)

        def mk_one(path: str) -> tuple[str, str]:
            parent_p, name = (path.rsplit("/", 1) if "/" in path else ("", path))
            pid = folder_ids[parent_p]
            res = dapi.mkdir(name, pid)
            return path, res["id"]

        with ThreadPoolExecutor(max_workers=8) as ex:
            for path, new_id in ex.map(mk_one, to_create):
                folder_ids[path] = new_id
                created_folders += 1

    (DATA / "cover_folder_ids.json").write_text(json.dumps(folder_ids, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"All {len(folder_ids)-1} cover category folders ready ({created_folders} created).", flush=True)

    # Execute move_and_rename for all 8,020 existing covers
    tasks: list[tuple[str, str, str, str]] = []
    for cid, assign in assignments.items():
        live = live_files.get(cid)
        if not live:
            continue
        dst_fid = folder_ids[assign["target_folder"]]
        cur_p = (live.get("parents") or [MGMT_COVERS_ID])[0]
        new_name = assign["new_name"]
        need_move = cur_p != dst_fid
        need_rename = live.get("name") != new_name
        if need_move or need_rename:
            tasks.append((cid, new_name if need_rename else None, dst_fid if need_move else None, cur_p if need_move else None))

    print(f"Executing {len(tasks)} move/rename operations across {len(live_files)} covers...", flush=True)
    lock = threading.Lock()
    done = 0
    errors: list[dict[str, str]] = []

    def run_one(t: tuple[str, str | None, str | None, str | None]) -> None:
        nonlocal done
        cid, nname, add_p, rem_p = t
        dapi.move_and_rename(cid, new_name=nname, add_parent=add_p, remove_parent=rem_p)
        with lock:
            done += 1
            if done % 400 == 0 or done == len(tasks):
                print(f"  Progress: {done}/{len(tasks)} (errors={len(errors)})", flush=True)

    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(run_one, t): t[0] for t in tasks}
        for fut in as_completed(futs):
            cid = futs[fut]
            try:
                fut.result()
            except Exception as exc:
                with lock:
                    errors.append({"id": cid, "error": str(exc)})

    result = {
        "total_live_covers_scanned": len(live_files),
        "folders_ready": len(folder_ids) - 1,
        "folders_created": created_folders,
        "operations_planned": len(tasks),
        "operations_succeeded": len(tasks) - len(errors),
        "errors": errors,
    }
    (DATA / "cloud_arrange_existing_covers_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\n=== EXISTING COVERS ARRANGE SUMMARY ===", flush=True)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
