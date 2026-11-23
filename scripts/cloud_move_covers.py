#!/usr/bin/env python3
"""Move all Qawmi Madrasa covers from Qawmi Madrasa/Covers & Thumbnails into
Library Management/Cover Images (1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj) via fast Drive REST API,
then archive the verified-empty legacy cover folder without deleting anything.
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "library_tools"))
import drive_api as dapi  # noqa: E402

QAWMI_COVERS_ID = "1WRjc_Jm-cx1MPUcqoF87n_bwRh7z9u57"
MGMT_COVERS_ID = "1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj"
ARCHIVED_QAWMI_FOLDERS_ID = "1EmNtwC2Udr5UCXlzXEfeoD_EoTAK50dD"


def main() -> None:
    print("Listing live items inside Qawmi Covers & Thumbnails...", flush=True)
    src_items = [
        it
        for it in dapi.list_all(
            q=f"'{QAWMI_COVERS_ID}' in parents and mimeType != '{dapi.FOLDER}' and trashed = false",
            fields="id,name,mimeType,parents",
        )
    ]
    print(f"Found {len(src_items)} cover files to move into Library Management/Cover Images.", flush=True)

    errors: list[dict[str, str]] = []
    lock = threading.Lock()
    done = 0

    def move_one(it: dict) -> None:
        nonlocal done
        fid = it["id"]
        cur_p = (it.get("parents") or [QAWMI_COVERS_ID])[0]
        if cur_p != MGMT_COVERS_ID:
            dapi.move(fid, MGMT_COVERS_ID, cur_p)
        with lock:
            done += 1
            if done % 200 == 0 or done == len(src_items):
                print(f"  Covers moved: {done}/{len(src_items)} (errors={len(errors)})", flush=True)

    if src_items:
        with ThreadPoolExecutor(max_workers=16) as ex:
            futs = {ex.submit(move_one, it): it for it in src_items}
            for fut in as_completed(futs):
                it = futs[fut]
                try:
                    fut.result()
                except Exception as exc:
                    with lock:
                        errors.append({"id": it["id"], "name": it["name"], "error": str(exc)})

    rem_in_src = list(
        dapi.list_all(q=f"'{QAWMI_COVERS_ID}' in parents and trashed = false", fields="id,name")
    )
    archived_empty_folder = False
    if not rem_in_src:
        info = dapi.get(QAWMI_COVERS_ID, fields="id,name,parents")
        cur_parents = info.get("parents") or []
        if cur_parents and cur_parents[0] != ARCHIVED_QAWMI_FOLDERS_ID:
            dapi.move(QAWMI_COVERS_ID, ARCHIVED_QAWMI_FOLDERS_ID, cur_parents[0])
            archived_empty_folder = True
            print(f"Archived empty folder {QAWMI_COVERS_ID} into {ARCHIVED_QAWMI_FOLDERS_ID}.", flush=True)
    else:
        print(f"WARNING: {len(rem_in_src)} items still inside {QAWMI_COVERS_ID}!", flush=True)

    mgmt_total = sum(
        1
        for _ in dapi.list_all(
            q=f"'{MGMT_COVERS_ID}' in parents and mimeType != '{dapi.FOLDER}' and trashed = false",
            fields="id",
        )
    )

    result = {
        "source_folder_id": QAWMI_COVERS_ID,
        "target_folder_id": MGMT_COVERS_ID,
        "covers_found": len(src_items),
        "covers_moved": len(src_items) - len(errors),
        "errors": errors,
        "remaining_in_source": len(rem_in_src),
        "archived_empty_source_folder": archived_empty_folder,
        "total_covers_in_mgmt_cover_images": mgmt_total,
    }
    (DATA / "cloud_move_covers_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\n=== CLOUD COVER CONSOLIDATION SUMMARY ===", flush=True)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if errors or rem_in_src:
        sys.exit(1)


if __name__ == "__main__":
    main()
