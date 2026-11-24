#!/usr/bin/env python3
"""
Comprehensive Series & Collections Shortcut Organizer for Google Drive.

Creates categorized subfolders under `Series & Collections/`:
  - `Series & Collections/Book Series/` (Fiction & Comics)
  - `Series & Collections/Tafsir Series/` (Quran & Tafsir)
  - `Series & Collections/Hadith Series/` (Hadith & Sunnah)
  - `Series & Collections/Islamic History & Seerah Series/`
  - `Series & Collections/Educational & Textbook Series/`

Then collects all matching original (non-shortcut) files across the entire Drive,
deduplicates against existing shortcuts in each target folder, creates native
Google Drive shortcuts (`application/vnd.google-apps.shortcut`) in batches,
cleans up the known misplaced Byomkesh shortcut in `মিসির আলি সিরিজ`,
and verifies all created folders and shortcut counts.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import drive_utils as du  # noqa: E402

# (category_folder, series_folder, keywords)
ALL_SERIES_DEFS: list[tuple[str, str, list[str]]] = [
    # --- Book Series (Fiction & Comics) ---
    ("Book Series", "মাসুদ রানা সিরিজ", ["মাসুদ রানা", "masud rana"]),
    ("Book Series", "মিসির আলি সিরিজ", ["মিসির আলি", "misir ali", "নিশীথিনী", "বৃহন্নলা", "তন্দ্রাবিলাস", "যখন নামিবে আঁধার"]),
    ("Book Series", "হিমু সিরিজ", ["হিমু", "himu", "ময়ূরাক্ষী", "moyurakkhi", "দরজার ওপাশে", "আঙুল কাটা জগলু", "মজার ভূত"]),
    ("Book Series", "ফেলুদা সিরিজ", ["ফেলুদা", "feluda", "সোনার কেল্লা", "জয় বাবা ফেলুনাথ"]),
    ("Book Series", "প্রফেসর শঙ্কু সিরিজ", ["শঙ্কু", "shonku"]),
    ("Book Series", "ব্যোমকেশ বক্সী সিরিজ", ["ব্যোমকেশ", "byomkesh", "কহেন কবি কালিদাস"]),
    ("Book Series", "ঘনাদা সিরিজ", ["ঘনাদা", "ghanada"]),
    ("Book Series", "টেনিদা সিরিজ", ["টেনিদা", "tenida"]),
    ("Book Series", "শুভ্র সিরিজ", ["শুভ্র", "shuvro"]),
    ("Book Series", "শার্লক হোমস সিরিজ", ["শার্লক হোমস", "sherlock holmes"]),
    ("Book Series", "হ্যারি পটার সিরিজ", ["হ্যারি পটার", "harry potter"]),
    ("Book Series", "টিনটিন কমিক্স", ["টিনটিন", "tintin"]),
    ("Book Series", "কাকাবাবু সিরিজ", ["কাকাবাবু", "kakababu"]),
    ("Book Series", "তিন গোয়েন্দা সিরিজ", ["তিন গোয়েন্দা", "tin goyenda"]),
    ("Book Series", "ঋজুদা সিরিজ", ["ঋজুদা", "rijuda"]),
    ("Book Series", "নন্টে ফন্টে", ["নন্টে ফন্টে", "nonte phonte", "nonte fonte"]),
    ("Book Series", "কিরীটী রায় সিরিজ", ["কিরীটী", "kiriti"]),
    ("Book Series", "অরণ্যদেব (Phantom)", ["অরণ্যদেব", "aranyadeb", "phantom"]),
    ("Book Series", "অর্জুন সিরিজ", ["অর্জুন সমগ্র", "অর্জুন - সমরেশ", "গোয়েন্দা অর্জুন"]),
    ("Book Series", "Tairen Soul", ["tairen soul", "lord of the fading lands", "queen of song and souls", "crown of crystal flame", "king of sword and sky"]),
    ("Book Series", "কুয়াশা সিরিজ", ["কুয়াশা সিরিজ", "kuasha"]),
    ("Book Series", "অদ্ভুতুড়ে সিরিজ", ["অদ্ভুতুড়ে", "adbhuture"]),
    ("Book Series", "চাচা চৌধুরী", ["চাচা চৌধুরী", "chacha chaudhary"]),
    ("Book Series", "সাইমুম সিরিজ", ["সাইমুম", "saimum"]),
    ("Book Series", "কর্নেল সমগ্র", ["কর্নেল সমগ্র", "কর্নেল নীলাদ্রি", "colonel niladri"]),
    ("Book Series", "প্রহেলিকা সিরিজ", ["প্রহেলিকা", "prohelika"]),
    ("Book Series", "সাম্ভালা ট্রিলজি", ["সাম্ভালা", "shambhala"]),

    # --- Tafsir Series ---
    ("Tafsir Series", "ফী যিলালিল কুরআন", ["ফী যিলালিল", "ফি যিলালিল", "ফি জিলালিল", "zilalil quran"]),
    ("Tafsir Series", "তাফসীর ইবনে কাসীর", ["তাফসীর ইবনে কাসীর", "তাফসীরে ইবনে কাসীর", "তাফসীরে ইবনে কাসির", "ibn kathir", "tafsir ibn k"]),
    ("Tafsir Series", "তাফসীরে জালালাইন", ["জালালাইন", "jalalain", "jalalayn"]),
    ("Tafsir Series", "তাফহীমুল কুরআন", ["তাফহীমুল কুরআন", "তাফহীমুল কোরআন", "tafhimul quran"]),
    ("Tafsir Series", "তাফসীরে তাবারী", ["তাফসীরে তাবারী", "তাফসীরে তাবারি", "তাফসীর তাবারী", "tafsir tabari", "tafsir at-tabari"]),
    ("Tafsir Series", "তাফসীরে কাবীর", ["তাফসীরে কাবীর", "তাফসীর কাবীর", "tafsir kabir"]),
    ("Tafsir Series", "তাফসীরে সা'দী", ["তাফসীরে সা'দী", "তাফসীরে সাদী", "তাফসীরে সাদি", "tafsir sadi", "tafsir as-sa'di"]),
    ("Tafsir Series", "তাফসীরে মাআরেফুল কোরআন", ["মারেফুল কোরআন", "মাআরেফুল কুরআন", "মা'আরেফুল কুরআন", "মাআরিফুল কুরআন", "maariful quran"]),
    ("Tafsir Series", "তাফসীরে উসমানী", ["তাফসীরে উসমানী", "তাফসীর উসমানী", "tafsir usmani"]),
    ("Tafsir Series", "তাফসীরে বয়ানুল কুরআন", ["বয়ানুল কুরআন", "bayanul quran"]),
    ("Tafsir Series", "তাফসীরে মাজহারী", ["তাফসীরে মাজহারী", "তাফসীর মাজহারী", "mazhari"]),
    ("Tafsir Series", "তাফসীরে আহসানুল বায়ান", ["আহসানুল বায়ান", "ahsanul bayan"]),
    ("Tafsir Series", "তাফসীরে কুরতুবী", ["তাফসীরে কুরতুবী", "তাফসীর কুরতুবী", "qurtubi"]),

    # --- Hadith Series ---
    ("Hadith Series", "সহীহ বুখারী", ["সহীহ বুখারী", "সহিহ বুখারি", "বোখারী শরীফ", "sahih al-bukhari", "sahih bukhari"]),
    ("Hadith Series", "জামে তিরমিযী", ["তিরমিযী", "তিরমিযি", "জামে তিরমিযী", "tirmidhi"]),
    ("Hadith Series", "মিশকাতুল মাসাবীহ", ["মিশকাতুল মাসাবীহ", "মিশকাত শরীফ", "mishkat"]),
    ("Hadith Series", "সহীহ মুসলিম", ["সহীহ মুসলিম", "সহিহ মুসলিম", "মুসলিম শরীফ", "sahih muslim"]),
    ("Hadith Series", "সুনানে আবু দাউদ", ["আবু দাউদ", "abu dawud", "abu dawood"]),
    ("Hadith Series", "সুনানে নাসাঈ", ["নাসাঈ", "নাসায়ী", "nasai"]),
    ("Hadith Series", "মুয়াত্তা ইমাম মালিক", ["মুয়াত্তা", "muwatta"]),
    ("Hadith Series", "সুনানে ইবনে মাজাহ", ["ইবনে মাজাহ", "ইবনে মাজা", "ibn majah"]),
    ("Hadith Series", "রিয়াদুস সালেহীন", ["রিয়াদুস সালেহীন", "riyadus salihin", "riyad us saliheen"]),
    ("Hadith Series", "বুলুগুল মারাম", ["বুলুগুল মারাম", "bulughul maram"]),
    ("Hadith Series", "মুসনাদে আহমাদ", ["মুসনাদে আহমাদ", "মুসনাদ আহমাদ", "musnad ahmad"]),
    ("Hadith Series", "সুনানে দারিমী", ["সুনানে দারিমী", "দারিমী শরীফ", "darimi"]),
    ("Hadith Series", "কানযুল উম্মাল", ["কানযুল উম্মাল", "kanzul ummal"]),

    # --- Islamic History & Seerah Series ---
    ("Islamic History & Seerah Series", "আল-বিদায়া ওয়ান নিহায়া", ["আল বিদায়া", "আল-বিদায়া", "বিদায়া ওয়ান নিহায়া", "bidaya wan nihaya"]),
    ("Islamic History & Seerah Series", "আসহাবে রাসূলের জীবনকথা", ["আসহাবে রাসূলের জীবনকথা", "ashabe rasul"]),
    ("Islamic History & Seerah Series", "আর-রাহীকুল মাখতূম ও সীরাতুন্নবী", ["আর-রাহীকুল মাখতূম", "রাহীকুল মাখতূম", "সীরাতুন্নবী", "raheequl makhtum", "siratunnabi"]),
    ("Islamic History & Seerah Series", "তারীখে তাবারী", ["তারীখে তাবারী", "তারিখে তাবারি", "tarikh tabari"]),

    # --- Educational & Textbook Series ---
    ("Educational & Textbook Series", "NCTB পাঠ্যবই সিরিজ", ["nctb", "পাঠ্যবই"]),
]


def match_series(name: str, path: str) -> list[tuple[str, str]]:
    text = f"{name} {path}".lower()
    hits: list[tuple[str, str]] = []
    for cat_dir, series_dir, keywords in ALL_SERIES_DEFS:
        if any(kw in text for kw in keywords):
            hits.append((cat_dir, series_dir))
    return hits


def run(dry_run: bool = False, workers: int = 8) -> dict[str, Any]:
    service = du.get_drive_service()
    print("[1/5] Crawling Google Drive (folders, original files, existing shortcuts)...")
    crawl = du.crawl_drive(service, du.ROOT_FOLDER_ID)
    folders = crawl["folders"]
    files = crawl["files"]
    shortcuts = crawl["shortcuts"]
    path_to_folder_id = dict(crawl["path_to_folder_id"])

    print(
        f"  -> Folders: {len(folders)}, Original files: {len(files)}, Existing shortcuts: {len(shortcuts)}"
    )

    series_root_path = "Series & Collections"
    series_root_id = path_to_folder_id.get(series_root_path)
    if not series_root_id:
        series_root_id = du.ensure_folder_path(
            service, path_to_folder_id, du.ROOT_FOLDER_ID, series_root_path, dry_run=dry_run
        )

    # [2/5] Ensure category & series subfolders exist
    print("[2/5] Creating category and series subfolders under Series & Collections/...")
    created_folders = 0
    dest_folder_ids: dict[tuple[str, str], str] = {}
    for cat_dir, series_dir, _ in ALL_SERIES_DEFS:
        full_path = f"{series_root_path}/{cat_dir}/{series_dir}"
        existed = full_path in path_to_folder_id
        fid = du.ensure_folder_path(
            service, path_to_folder_id, du.ROOT_FOLDER_ID, full_path, dry_run=dry_run
        )
        if not existed and fid and not dry_run:
            created_folders += 1
        dest_folder_ids[(cat_dir, series_dir)] = fid

    # Cleanup known misplaced Byomkesh shortcut in মিসির আলি সিরিজ
    removed_misplaced: list[dict[str, Any]] = []
    misir_folder_id = path_to_folder_id.get("Series & Collections/Book Series/মিসির আলি সিরিজ")
    if misir_folder_id:
        for sc in shortcuts:
            if sc.get("parent_id") == misir_folder_id:
                nm = (sc.get("name") or "").lower()
                if "কহেন কবি কালিদাস" in nm or "শরদিন্দু" in nm or "byomkesh" in nm:
                    if not dry_run:
                        try:
                            du.execute_with_retry(
                                service.files().delete(fileId=sc["id"], supportsAllDrives=True)
                            )
                            removed_misplaced.append({"id": sc["id"], "name": sc["name"]})
                        except Exception as exc:
                            print(f"  WARN could not delete misplaced shortcut {sc['name']}: {exc}")
                    else:
                        removed_misplaced.append({"id": sc["id"], "name": sc["name"], "dry_run": True})

    # Index existing shortcuts per destination folder to guarantee zero duplicates
    existing_target_by_parent: dict[str, set[str]] = collections.defaultdict(set)
    existing_name_by_parent: dict[str, set[str]] = collections.defaultdict(set)
    for sc in shortcuts:
        pid = sc.get("parent_id")
        tid = sc.get("target_id")
        if pid and tid:
            existing_target_by_parent[pid].add(tid)
        if pid and sc.get("name"):
            existing_name_by_parent[pid].add(sc["name"].strip().lower())

    # [3/5] Collect file IDs & deduplicate
    print("[3/5] Collecting matching files and deduplicating shortcuts...")
    planned: list[dict[str, Any]] = []
    series_match_counts: dict[str, int] = collections.Counter()

    for f in files:
        fid = f["id"]
        fname = f["name"]
        fpath = f["path"]
        hits = match_series(fname, fpath)
        for cat_dir, series_dir in hits:
            series_key = f"{cat_dir}/{series_dir}"
            series_match_counts[series_key] += 1
            dest_id = dest_folder_ids.get((cat_dir, series_dir), "")
            if not dest_id:
                continue
            # Skip if file already lives directly inside this series folder
            if f.get("parent_id") == dest_id:
                continue
            if fid in existing_target_by_parent[dest_id]:
                continue
            if fname.strip().lower() in existing_name_by_parent[dest_id]:
                continue
            existing_target_by_parent[dest_id].add(fid)
            existing_name_by_parent[dest_id].add(fname.strip().lower())
            planned.append(
                {
                    "cat_dir": cat_dir,
                    "series_dir": series_dir,
                    "series_key": series_key,
                    "dest_path": f"{series_root_path}/{cat_dir}/{series_dir}",
                    "dest_id": dest_id,
                    "target_id": fid,
                    "name": fname,
                    "source_path": fpath,
                }
            )

    print(f"  -> Planned new shortcuts: {len(planned)}")

    # [4/5] Create Google Drive shortcuts in batches
    print("[4/5] Creating Google Drive shortcuts in parallel batches...")
    created_entries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if not dry_run and planned:
        def _create(item: dict[str, Any]) -> dict[str, Any]:
            tl_service = du.get_thread_local_service()
            res = du.create_shortcut(tl_service, item["dest_id"], item["name"], item["target_id"])
            sd = res.get("shortcutDetails") or {}
            return {
                **item,
                "shortcut_id": res.get("id", ""),
                "verified_target_id": sd.get("targetId", ""),
                "verified": sd.get("targetId") == item["target_id"],
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_create, p) for p in planned]
            done = 0
            for fut in concurrent.futures.as_completed(futs):
                done += 1
                try:
                    res = fut.result()
                    created_entries.append(res)
                except Exception as exc:
                    errors.append({"error": str(exc)})
                if done % 200 == 0 or done == len(futs):
                    print(f"  ... shortcuts {done}/{len(futs)} processed")

    # [5/5] Verify counts per folder on Drive
    print("[5/5] Verifying created folders and shortcut counts...")
    verified_counts: dict[str, int] = {}
    if not dry_run:
        for (cat_dir, series_dir), fid in dest_folder_ids.items():
            if not fid:
                continue
            children = du.list_folder_children(service, fid)
            verified_counts[f"{cat_dir}/{series_dir}"] = len(children)

    batch_id = f"series_shortcuts_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if not dry_run and created_entries:
        cl_entries = [
            {
                "action": "create_shortcut",
                "file_id": e["shortcut_id"],
                "target_id": e["target_id"],
                "old_name": e["name"],
                "new_name": e["name"],
                "old_path": e["source_path"],
                "new_path": f"{e['dest_path']}/{e['name']}",
                "dest_folder_id": e["dest_id"],
                "reason": f"Categorized series shortcut ({e['series_key']})",
            }
            for e in created_entries
        ]
        du.append_changelog_batch(
            service,
            du.ROOT_FOLDER_ID,
            batch_id=batch_id,
            stage="series_shortcuts",
            entries=cl_entries,
        )

    summary = {
        "applied_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dry_run": dry_run,
        "batch_id": batch_id,
        "folders_created": created_folders,
        "total_series_folders": len(dest_folder_ids),
        "misplaced_shortcuts_removed": removed_misplaced,
        "planned_shortcuts": len(planned),
        "created_shortcuts": len(created_entries),
        "verified_shortcuts": sum(1 for e in created_entries if e.get("verified")),
        "errors_count": len(errors),
        "series_match_counts": dict(sorted(series_match_counts.items())),
        "verified_folder_item_counts": dict(sorted(verified_counts.items())),
        "errors": errors[:50],
    }

    du.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (du.REPORTS_DIR / "series_shortcuts_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md_lines = [
        "# Categorized Series & Collections Shortcut Report",
        "",
        f"- **Timestamp (UTC):** `{summary['applied_at']}`",
        f"- **Dry Run:** `{dry_run}`",
        f"- **Batch ID:** `{batch_id}`",
        f"- **Category & Series Folders Managed:** `{len(dest_folder_ids)}` (newly created: `{created_folders}`)",
        f"- **New Shortcuts Created & Verified:** `{summary['created_shortcuts']}` (verified: `{summary['verified_shortcuts']}`)",
        f"- **Misplaced Shortcuts Cleaned:** `{len(removed_misplaced)}`",
        f"- **Errors:** `{len(errors)}`",
        "",
        "## Series Breakdown (Matched Books & Live Folder Item Counts)",
        "",
        "| Category / Series Folder | Matched Books | Live Folder Items |",
        "|---|---:|---:|",
    ]
    for cat_dir, series_dir, _ in ALL_SERIES_DEFS:
        key = f"{cat_dir}/{series_dir}"
        matched = series_match_counts.get(key, 0)
        live_cnt = verified_counts.get(key, 0)
        md_lines.append(f"| `{key}` | {matched} | {live_cnt} |")

    (du.REPORTS_DIR / "series_shortcuts_report.md").write_text(
        "\n".join(md_lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k not in ("series_match_counts", "verified_folder_item_counts", "errors")}, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Categorized Series Shortcut Organizer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    run(dry_run=args.dry_run, workers=args.workers)


if __name__ == "__main__":
    main()
