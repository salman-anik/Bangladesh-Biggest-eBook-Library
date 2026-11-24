#!/usr/bin/env python3
"""
Rollback Utility for Google Drive Library Changes.

Reads versioned change batches from `Library Management/Reports/rename_changelog.json`,
lets you inspect recorded batches, preview reversals safely (--dry-run), or revert
a specific batch on Google Drive (--apply) while logging the rollback itself into
`Library Management/Reports/` and Drive (`Library Management/Library Statistics & Reports`).
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def load_changelog(repo_dir: Path) -> list[dict[str, Any]]:
    json_path = repo_dir / "Library Management" / "Reports" / "rename_changelog.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Changelog not found at {json_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {json_path}")
    return data


def list_batches(entries: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for item in entries:
        bid = item.get("batch_id") or "unbatched"
        grouped[bid].append(item)

    if not grouped:
        print("No Drive change batches recorded.")
        return

    print(f"Recorded Drive change batches ({len(grouped)}):\n")
    for bid, items in grouped.items():
        ts = items[0].get("timestamp", "")
        actions = collections.Counter(it.get("action", "rename") for it in items)
        act_str = ", ".join(f"{k}:{v}" for k, v in sorted(actions.items()))
        sample = items[0].get("new_name") or items[0].get("old_name") or items[0].get("id")
        print(f"  {bid} | {ts} | count={len(items)} ({act_str}) | sample='{sample}'")


def sync_reverted_catalog(repo_dir: Path, reverted_entries: list[dict[str, Any]]) -> int:
    by_id = {e["id"]: e for e in reverted_entries if e.get("action") != "create_folder"}
    if not by_id:
        return 0
    max_updated = 0
    for rel in ("books.json", "visualize/public/books.json"):
        p = repo_dir / rel
        if not p.exists():
            continue
        cat = json.loads(p.read_text(encoding="utf-8"))
        updated_here = 0
        for b in cat.get("books", []):
            bid = b[0]
            if bid in by_id:
                target_name = by_id[bid]["restored_name"]
                stem = os.path.splitext(target_name)[0]
                if " - " in stem:
                    t_part, a_part = stem.rsplit(" - ", 1)
                    if re.search(r"(?:খন্ড|খণ্ড|পর্ব|\b(?:vol|volume|part|edition)\b)", a_part, re.I):
                        b[1] = stem.strip()
                    else:
                        b[1] = t_part.strip()
                        if a_part.strip() and b[2] in ("Unknown", "Unknown Author", ""):
                            b[2] = a_part.strip()
                else:
                    b[1] = stem.strip()
                updated_here += 1
        if updated_here:
            cat["generated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            p.write_text(json.dumps(cat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            max_updated = max(max_updated, updated_here)
    return max_updated


def run_rollback(
    repo_dir: Path,
    batch_id: str,
    apply_changes: bool,
    force: bool = False,
) -> int:
    entries = load_changelog(repo_dir)
    target = [e for e in entries if (e.get("batch_id") or "unbatched") == batch_id]
    if not target:
        print(f"Error: Batch '{batch_id}' not found in changelog.", file=sys.stderr)
        return 1

    rev_entries = list(reversed(target))
    mode_label = "APPLY" if apply_changes else "DRY-RUN"
    print(f"[{mode_label}] Target batch '{batch_id}' ({len(rev_entries)} item(s), reverse order):")

    if not apply_changes:
        for idx, item in enumerate(rev_entries, 1):
            act = item.get("action", "rename")
            fid = item.get("id", "")
            old_name = item.get("old_name", "")
            new_name = item.get("new_name", "")
            old_p = item.get("old_parent_id", "")
            new_p = item.get("new_parent_id", "")
            if act == "create_folder":
                print(f"  {idx}. [SKIP folder] {new_name} ({fid}) — folders are never auto-deleted")
                continue
            if act == "create_shortcut":
                print(f"  {idx}. [TRASH shortcut only] {new_name} ({fid}) in parent {new_p}")
                continue
            parts: list[str] = []
            if old_name and new_name and old_name != new_name:
                parts.append(f"rename '{new_name}' -> '{old_name}'")
            if old_p and new_p and old_p != new_p:
                parts.append(f"move parent '{new_p}' -> '{old_p}'")
            desc = " & ".join(parts) if parts else "no-op"
            print(f"  {idx}. {fid}: {desc}")
        print("\nRun again with --apply (and GDRIVE_OAUTH_JSON set) to execute this rollback.")
        return 0

    sys.path.insert(0, str(repo_dir / "scripts"))
    import intelligent_book_renamer as ibr

    applied_at = dt.datetime.now(dt.timezone.utc).isoformat()
    rollback_batch_id = ibr.make_batch_id(applied_at, prefix="rollback")
    rollback_records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in rev_entries:
        act = item.get("action", "rename")
        fid = item.get("id", "")
        old_name = item.get("old_name", "")
        new_name = item.get("new_name", "")
        old_p = item.get("old_parent_id", "")
        new_p = item.get("new_parent_id", "")

        if act == "create_folder":
            skipped.append({"id": fid, "reason": "create_folder_never_deleted", "name": new_name})
            continue
        if act == "create_shortcut":
            try:
                meta = ibr.drive_request(
                    "GET",
                    f"/files/{fid}",
                    params={"supportsAllDrives": "true", "fields": "id,name,mimeType,trashed,parents"},
                )
                if meta.get("mimeType") != "application/vnd.google-apps.shortcut":
                    skipped.append({"id": fid, "reason": "not_a_shortcut_refused_delete", "name": meta.get("name", "")})
                    continue
                if meta.get("trashed"):
                    skipped.append({"id": fid, "reason": "shortcut_already_trashed"})
                    continue
                ibr.drive_request(
                    "PATCH",
                    f"/files/{fid}",
                    params={"supportsAllDrives": "true", "fields": "id,trashed"},
                    body={"trashed": True},
                )
                rollback_records.append(
                    {
                        "id": fid,
                        "batch_id": rollback_batch_id,
                        "timestamp": applied_at,
                        "action": "rollback_shortcut",
                        "folder": item.get("folder", ""),
                        "old_parent_id": new_p,
                        "new_parent_id": old_p,
                        "old_name": new_name,
                        "new_name": "[TRASHED SHORTCUT]",
                        "restored_name": new_name,
                        "category": item.get("category", ""),
                    }
                )
                print(f"  Trashed shortcut {fid}: '{new_name}'")
            except Exception as exc:
                errors.append({"id": fid, "error": str(exc)[:250]})
            continue

        try:
            meta = ibr.drive_request(
                "GET",
                f"/files/{fid}",
                params={"supportsAllDrives": "true", "fields": "id,name,parents,trashed"},
            )
            if meta.get("trashed"):
                skipped.append({"id": fid, "reason": "file_in_trash"})
                continue

            live_name = meta.get("name", "")
            live_parents = meta.get("parents") or []

            need_rename = bool(old_name and new_name and old_name != new_name)
            need_move = bool(old_p and new_p and old_p != new_p)

            if not force:
                if need_rename and live_name != new_name:
                    skipped.append(
                        {"id": fid, "reason": f"live_name_mismatch (expected '{new_name}', got '{live_name}')"}
                    )
                    continue
                if need_move and new_p not in live_parents:
                    skipped.append(
                        {"id": fid, "reason": f"live_parent_mismatch (expected '{new_p}', got {live_parents})"}
                    )
                    continue

            params: dict[str, Any] = {"supportsAllDrives": "true", "fields": "id,name,parents"}
            body: dict[str, Any] = {}
            if need_rename:
                body["name"] = old_name
            if need_move:
                params["addParents"] = old_p
                rm_parent = new_p if new_p in live_parents else ",".join(live_parents)
                if rm_parent:
                    params["removeParents"] = rm_parent

            if not body and "addParents" not in params:
                skipped.append({"id": fid, "reason": "nothing_to_revert"})
                continue

            updated = ibr.drive_request("PATCH", f"/files/{fid}", params=params, body=body or None)
            restored_name = updated.get("name", old_name or live_name)
            restored_parents = updated.get("parents") or [old_p]

            rollback_records.append(
                {
                    "id": fid,
                    "batch_id": rollback_batch_id,
                    "timestamp": applied_at,
                    "action": "rollback",
                    "folder": item.get("folder", ""),
                    "old_parent_id": live_parents[0] if live_parents else new_p,
                    "new_parent_id": restored_parents[0] if restored_parents else old_p,
                    "old_name": live_name,
                    "new_name": restored_name,
                    "restored_name": restored_name,
                    "category": item.get("category", ""),
                }
            )
            print(f"  Reverted {fid}: '{live_name}' -> '{restored_name}'")
        except Exception as exc:
            errors.append({"id": fid, "error": str(exc)[:250]})
            print(f"  ERROR reverting {fid}: {exc}", file=sys.stderr)

    if rollback_records:
        catalog_synced = sync_reverted_catalog(repo_dir, rollback_records)
        cl_res = ibr.update_rename_changelog(
            repo_dir,
            rollback_records,
            applied_at,
            sync_drive=True,
            batch_id=rollback_batch_id,
            default_action="rollback",
        )
        print(
            json.dumps(
                {
                    "rollback_batch_id": rollback_batch_id,
                    "reverted_count": len(rollback_records),
                    "skipped_count": len(skipped),
                    "error_count": len(errors),
                    "catalog_synced": catalog_synced,
                    "changelog_total_entries": cl_res["total_entries"],
                },
                indent=2,
            )
        )
    else:
        print(json.dumps({"reverted_count": 0, "skipped": skipped, "errors": errors}, indent=2))

    return 1 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Rollback Google Drive changes logged in Library Management")
    ap.add_argument("--repo-dir", default=".", help="Path to repository root")
    ap.add_argument("--list-batches", action="store_true", help="List all recorded Drive change batches")
    ap.add_argument("--batch", default="", help="Batch ID to roll back")
    ap.add_argument("--dry-run", action="store_true", help="Preview rollback actions without modifying Drive (default)")
    ap.add_argument("--apply", action="store_true", help="Execute rollback against Google Drive API")
    ap.add_argument("--force", action="store_true", help="Revert even if live file name/parent changed since batch")
    args = ap.parse_args()

    repo_dir = Path(args.repo_dir).resolve()
    if args.list_batches:
        list_batches(load_changelog(repo_dir))
        return 0
    if not args.batch:
        ap.error("Specify --list-batches or --batch <BATCH_ID>")

    return run_rollback(repo_dir, args.batch, apply_changes=bool(args.apply), force=bool(args.force))


if __name__ == "__main__":
    raise SystemExit(main())
