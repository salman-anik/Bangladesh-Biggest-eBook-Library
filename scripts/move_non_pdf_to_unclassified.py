#!/usr/bin/env python3
"""
Segregate all non-PDF book files (EPUB, MOBI/AZW, DOC/DOCX/RTF, TXT, DJVU, etc.)
into `Review & Unclassified/<Format>/<Arranged Subfolder>` on Google Drive.

Rules obeyed strictly:
- Never deletes any file or folder.
- Never touches PDFs, folders, Google Drive shortcuts, native Google Docs/Sheets/Slides,
  or Library Management/.
- Idempotent: files already organized under `Review & Unclassified/<Format>/` are skipped.
- Never creates duplicate folders or overwrites colliding filenames.
- Verifies every move on Drive (`parents` & `not trashed`).
- Logs every `create_folder` and `move` to Library Management/Reports/rename_changelog.{json,csv,md}.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import datetime as dt
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import drive_utils as du  # noqa: E402

FORMAT_BUCKET_BY_EXT: dict[str, str] = {
    ".epub": "EPUB",
    ".mobi": "MOBI",
    ".azw": "MOBI",
    ".azw3": "MOBI",
    ".doc": "DOC & DOCX",
    ".docx": "DOC & DOCX",
    ".rtf": "DOC & DOCX",
    ".txt": "TXT",
    ".djvu": "Other Formats",
    ".png": "Other Formats",
    ".jpg": "Other Formats",
    ".jpeg": "Other Formats",
    ".cbr": "Other Formats",
    ".cbz": "Other Formats",
    ".chm": "Other Formats",
}
ALL_FORMAT_ROOTS = set(FORMAT_BUCKET_BY_EXT.values())


def derive_subpath(src_folder: str) -> list[str]:
    parts = [p.strip() for p in (src_folder or "").split("/") if p.strip()]
    if not parts:
        return ["Uncategorized"]
    top = parts[0]
    rest = parts[1:]

    if top == "Review & Unclassified":
        if not rest or rest[0] == "Pending Review":
            return ["Uncategorized"]
        return [rest[-1]]
    if top == "Bangla Books":
        return [rest[0]] if rest else ["Bangla Books"]
    if top == "Religion Books":
        if len(rest) >= 2:
            return [rest[0], rest[1]]
        return [rest[0]] if rest else ["Religion Books"]
    if top == "English Books":
        return ["English Books", rest[0]] if rest else ["English Books"]
    if top == "Education & Textbooks":
        return ["Education & Textbooks", rest[0]] if rest else ["Education & Textbooks"]
    if top == "Authors & Scholars":
        if len(rest) >= 3 and rest[0] == "Islamic Scholars":
            return ["Authors & Scholars", rest[2]]
        if len(rest) >= 2:
            return ["Authors & Scholars", rest[1]]
        return ["Authors & Scholars"]
    if top == "Series & Collections":
        if len(rest) >= 2:
            return ["Series & Collections", rest[1]]
        return ["Series & Collections"]
    if top == "Reference & Research":
        return ["Reference & Research", rest[0]] if rest else ["Reference & Research"]
    return [top] + ([rest[0]] if rest else [])


def run_non_pdf_segregation(repo_dir: Path, dry_run: bool = False, local_catalog_only: bool = False) -> dict[str, Any]:
    if local_catalog_only:
        cat = json.loads((repo_dir / "books.json").read_text(encoding="utf-8"))
        cats, subs, fmts = cat["cats"], cat["subs"], cat["fmts"]
        files: list[dict[str, Any]] = []
        folders_by_path: dict[str, str] = {"Review & Unclassified": "UNCLASS_ROOT"}
        children_by_folder: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for b in cat["books"]:
            fid, title, _a, ci, si, _li, fi, sz, _cov, _ser = b
            c = cats[ci] if 0 <= ci < len(cats) else ""
            s = subs[si] if 0 <= si < len(subs) else ""
            fp = f"{c}/{s}".strip("/")
            ext = "." + (fmts[fi].lower() if 0 <= fi < len(fmts) else "pdf")
            files.append(
                {
                    "id": fid,
                    "name": f"{title}{ext}",
                    "ext": ext,
                    "mimeType": "application/octet-stream",
                    "size": sz,
                    "parent_id": f"P_{fp}",
                    "folder": fp,
                }
            )
    else:
        print(f"[NonPDF] Walking live Drive root {du.ROOT_ID}...", flush=True)
        tree = du.walk_drive_tree(du.ROOT_ID, skip_top_folders=du.SKIP_TOP_FOLDERS)
        files = tree["files"]
        folders_by_path = tree["folders_by_path"]
        children_by_folder = collections.defaultdict(list, tree["children_by_folder"])

    unclass_root_id = folders_by_path.get("Review & Unclassified")
    if not unclass_root_id and not local_catalog_only:
        unclass_root_id, _ = du.resolve_folder_path("Review & Unclassified")

    plan: list[dict[str, Any]] = []
    skipped_already_arranged = 0
    for f in files:
        ext = f["ext"]
        if ext == ".pdf" or ext not in FORMAT_BUCKET_BY_EXT:
            continue
        fmt_bucket = FORMAT_BUCKET_BY_EXT[ext]
        src_folder = f["folder"]
        src_parts = [p for p in src_folder.split("/") if p]
        if len(src_parts) >= 2 and src_parts[0] == "Review & Unclassified" and src_parts[1] in ALL_FORMAT_ROOTS:
            skipped_already_arranged += 1
            continue

        rel_segs = [fmt_bucket] + derive_subpath(src_folder)
        dest_folder = "Review & Unclassified/" + "/".join(rel_segs)
        plan.append(
            {
                "id": f["id"],
                "name": f["name"],
                "ext": ext,
                "format_bucket": fmt_bucket,
                "old_parent_id": f["parent_id"],
                "src_folder": src_folder,
                "rel_segs": rel_segs,
                "dest_folder": dest_folder,
                "size": f["size"],
            }
        )

    print(
        f"[NonPDF] Identified {len(plan)} non-PDF files to arrange under Review & Unclassified "
        f"({skipped_already_arranged} already arranged).",
        flush=True,
    )

    folder_lock = threading.Lock()
    folder_id_by_path: dict[str, str] = dict(folders_by_path)
    names_by_folder_id: dict[str, set[str]] = collections.defaultdict(set)
    for fid, kids in children_by_folder.items():
        for k in kids:
            names_by_folder_id[fid].add(k.get("name", "").lower())

    folder_creations: list[dict[str, Any]] = []

    def ensure_path(rel_segs: list[str]) -> str:
        cur_id = unclass_root_id or "UNCLASS_ROOT"
        cur_path = "Review & Unclassified"
        for seg in rel_segs:
            next_path = f"{cur_path}/{seg}"
            with folder_lock:
                existing_id = folder_id_by_path.get(next_path)
                if existing_id:
                    cur_id = existing_id
                    cur_path = next_path
                    continue
                if dry_run or local_catalog_only:
                    fake_id = f"DRY_{next_path}"
                    folder_id_by_path[next_path] = fake_id
                    folder_creations.append(
                        {
                            "id": fake_id,
                            "action": "create_folder",
                            "folder": cur_path,
                            "old_parent_id": cur_id,
                            "new_parent_id": cur_id,
                            "old_name": "",
                            "new_name": seg,
                            "category": "Review & Unclassified",
                        }
                    )
                    cur_id = fake_id
                    cur_path = next_path
                    continue
                siblings = children_by_folder.get(cur_id)
                if siblings is None:
                    siblings = du.list_children(cur_id)
                    children_by_folder[cur_id] = siblings
                created_meta, created = du.find_or_create_folder(
                    cur_id, seg, existing_children=siblings, parent_path=cur_path
                )
                nid = created_meta["id"]
                folder_id_by_path[next_path] = nid
                if created:
                    folder_creations.append(
                        {
                            "id": nid,
                            "action": "create_folder",
                            "folder": cur_path,
                            "old_parent_id": cur_id,
                            "new_parent_id": cur_id,
                            "old_name": "",
                            "new_name": seg,
                            "category": "Review & Unclassified",
                        }
                    )
                cur_id = nid
                cur_path = next_path
        return cur_id

    # First ensure target folders sequentially/safely (only ~50-90 unique folders)
    dest_id_map: dict[str, str] = {}
    unique_paths = {tuple(item["rel_segs"]) for item in plan}
    for seg_tuple in sorted(unique_paths):
        dest_id_map["Review & Unclassified/" + "/".join(seg_tuple)] = ensure_path(list(seg_tuple))

    move_logs: list[dict[str, Any]] = []
    collisions = 0
    verified_moves = 0
    errors: list[dict[str, Any]] = []

    def _move_one(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        dest_id = dest_id_map[item["dest_folder"]]
        with folder_lock:
            if item["name"].lower() in names_by_folder_id[dest_id]:
                return "collision", item
            names_by_folder_id[dest_id].add(item["name"].lower())

        if dry_run or local_catalog_only:
            return "moved", {
                "id": item["id"],
                "action": "move",
                "folder": f"{item['src_folder']} -> {item['dest_folder']}",
                "old_parent_id": item["old_parent_id"],
                "new_parent_id": dest_id,
                "old_name": item["name"],
                "new_name": item["name"],
                "category": f"Review & Unclassified/{item['format_bucket']}",
                "format_bucket": item["format_bucket"],
                "dest_folder": item["dest_folder"],
            }

        du.drive_request(
            "PATCH",
            f"/files/{item['id']}",
            params={
                "supportsAllDrives": "true",
                "addParents": dest_id,
                "removeParents": item["old_parent_id"],
                "fields": "id,name,parents",
            },
        )
        chk = du.drive_request(
            "GET",
            f"/files/{item['id']}",
            params={"supportsAllDrives": "true", "fields": "id,name,parents,trashed"},
        )
        ok = dest_id in (chk.get("parents") or []) and not chk.get("trashed", False)
        return ("verified" if ok else "moved"), {
            "id": item["id"],
            "action": "move",
            "folder": f"{item['src_folder']} -> {item['dest_folder']}",
            "old_parent_id": item["old_parent_id"],
            "new_parent_id": dest_id,
            "old_name": item["name"],
            "new_name": item["name"],
            "category": f"Review & Unclassified/{item['format_bucket']}",
            "format_bucket": item["format_bucket"],
            "dest_folder": item["dest_folder"],
        }

    t0 = time.time()
    if dry_run or local_catalog_only:
        for item in plan:
            status, payload = _move_one(item)
            if status == "collision":
                collisions += 1
            else:
                move_logs.append(payload)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futs = [pool.submit(_move_one, item) for item in plan]
            for idx, fut in enumerate(concurrent.futures.as_completed(futs), 1):
                try:
                    status, payload = fut.result()
                    if status == "collision":
                        collisions += 1
                    else:
                        if status == "verified":
                            verified_moves += 1
                        move_logs.append(payload)
                except Exception as exc:
                    errors.append({"error": str(exc)[:220]})
                if idx % 100 == 0 or idx == len(plan):
                    print(f"  moved {idx}/{len(plan)} non-PDF files ({time.time() - t0:.1f}s)...", flush=True)

    applied_at = dt.datetime.now(dt.timezone.utc).isoformat()
    cl_entries = folder_creations + move_logs
    cl_res = {"batch_id": "", "total_entries": 0}
    if not dry_run and not local_catalog_only and cl_entries:
        cl_res = du.update_rename_changelog(
            repo_dir, cl_entries, applied_at, sync_drive=True, batch_id=du.make_batch_id(applied_at, "non_pdf")
        )

    by_format = collections.Counter(m["format_bucket"] for m in move_logs)
    by_dest = collections.Counter(m["dest_folder"] for m in move_logs)

    out = {
        "applied_at": applied_at,
        "dry_run": dry_run or local_catalog_only,
        "planned_count": len(plan),
        "skipped_already_arranged": skipped_already_arranged,
        "folders_created": len(folder_creations),
        "moved_count": len(move_logs),
        "verified_moves": verified_moves,
        "collisions_skipped": collisions,
        "errors_count": len(errors),
        "batch_id": cl_res["batch_id"],
        "by_format": dict(by_format.most_common()),
        "by_destination_folder": dict(by_dest.most_common()),
        "errors": errors,
    }
    reports_dir = repo_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "non_pdf_segregation_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        "# Non-PDF Segregation Report (Review & Unclassified)",
        "",
        f"- **Timestamp (UTC):** `{applied_at}`",
        f"- **Dry Run:** `{out['dry_run']}`",
        f"- **Batch ID:** `{cl_res['batch_id']}`",
        f"- **Folders Created under Review & Unclassified:** `{len(folder_creations)}`",
        f"- **Non-PDF Files Moved:** `{len(move_logs)}` (verified on Drive: `{verified_moves}`, collisions skipped: `{collisions}`)",
        "",
        "## Breakdown by Format Folder",
        "",
        "| Format Folder | Files Moved |",
        "|---|---:|",
    ]
    for fmt, cnt in by_format.most_common():
        md.append(f"| `Review & Unclassified/{fmt}` | {cnt} |")
    md += ["", "## Top Arranged Destination Subfolders", "", "| Destination Subfolder | Files Moved |", "|---|---:|"]
    for df, cnt in by_dest.most_common(60):
        md.append(f"| `{df}` | {cnt} |")
    (reports_dir / "non_pdf_segregation_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "dry_run": out["dry_run"],
                "folders_created": out["folders_created"],
                "moved_count": out["moved_count"],
                "verified_moves": out["verified_moves"],
                "by_format": out["by_format"],
                "collisions_skipped": collisions,
                "errors_count": len(errors),
            },
            indent=2,
        ),
        flush=True,
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--local-catalog-only", action="store_true")
    args = ap.parse_args()
    run_non_pdf_segregation(Path(args.repo_dir).resolve(), dry_run=args.dry_run, local_catalog_only=args.local_catalog_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
