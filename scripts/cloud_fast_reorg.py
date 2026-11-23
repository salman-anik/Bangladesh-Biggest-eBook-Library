#!/usr/bin/env python3
"""High-speed REST API executor on GitHub Actions using library_tools/drive_api.py."""
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

QAWMI_ROOT_ID = "1oACGk9Yf70kBJGRdsNMVPBkFLhZNJ02O"
MISC_FOLDER_ID = "1x44IFWbIauj-228uDJd6riHIY7k0Jqn0"

ENGLISH_SUBFOLDER_IDS = [
    "1FMsxAa8L4BrBbENZSKEW1F7sDWo19oue",  # Biography & Memoirs
    "1w9uktrcbnXmEV77APF7BBA26eVJ_IUuQ",  # Computer Science
    "1JKijQSbz_srzkN1PG4FFW5FtTEzDOyMf",  # Fiction & Literature
    "11wriQeCfwa8cqPfokhoMK0jwmCFf7BHr",  # History
    "1ZAzXZthCslv932R9eYLS3yciPFVkvV5U",  # Other Subjects
    "1o8H3F2KCkIuBelOcNr0kWb5p4T3A4SAi",  # Philosophy
    "1PkcIj1wMG64n3HRdB8cUbg8fDgSO4p1e",  # Science & Technology
    "11V1qGfvBW70rhE8d9VUb9znYFE5QIshv",  # Self Development & Non-Fiction
]

LEGACY_QAWMI_SHELL_IDS = [
    "1cy96QS6Do7k9w3ukRD-ULIPnDy9jJ2EW",  # Taisir
    "1ExOhiVaPlFFdfpIoMbPqNnTXidK1eB0d",  # Maktab
    "1wxKuPVb0dQY9toH4d4TgjAJIAYoibtew",  # Mizan
    "1uuMRF7HI_kLaIAL3TNaBZcj8RzFF_x8T",  # Nahw Meer
    "1lB7suo8IISvAa7O53hEWTm8EehUSg-ql",  # Urdu 1
    "1LCT15LlasNjryMYZyuVKkrd05HfBo1Pz",  # Urdu 2
    "1dT_qECy9sGgXPG4IXStXkRRsRdKKUAPI",  # Urdu 3
    "1yJsS9gsNxCXM7uQGev8SPH0pxildwifC",  # Hidayatun
    "1wvAbBJLvB9iITdFgYirq6ODp4FYfiCgL",  # Kafia
    "1dDor_YkLSJ6yGgBXtTR1i48nxOV4_A9U",  # Urdu 4
    "1Fu4gIPcJRwIXppDija7pqBa3Sq3yfDoB",  # Sharhe Jami
    "1sqqeq8Qlv_t3fMf9MlxdJ_zoFUnXeV33",  # Urdu 5
    "1i4omgK56Yy6Qel-UTAQGrFGqR6XQ80Oi",  # Urdu 6
    "1zG9E3MtJ_XYPaoc3lvSRl6Pqks-Xg9Eb",  # Jalalain
    "1PAwvYYVn6IAR2VTa5VPrDNxNICAWwH2t",  # Mishkat
    "1MvgR4LDoofTANnTm_emws_zK0T13E3OX",  # Urdu 7
    "13UappvN5ZhDAImTkLrRmYtJh9cDzIUmI",  # Dawra Bangla
    "1ydIgC4_Cwk3uo3q9Pej-g310_Y0pPPCH",  # Urdu 8
    "1YWmDGConBdjjPCNQWLeqGu6sr3GM9nJK",  # Madani Nisab
    "1Lr8oezzPkV2875vw8RUrgtf49yH0Qj3g",  # Mantiq & Falsafa
    "1xplEKfrk6DxfNpnxaSgMU1slOGcoYpWW",  # Tafseer & Al-Quran
    "1ipi8AazO58_rz0XKVJn9uipYLX8DAgHQ",  # Hadith & Sunnah
    "1MR7e8P5Hy60om1erTA8LF8MOMQqXcpPg",  # Fiqh & Madhhab
    "1CE2s-GxEzGG7PEFQzeIl9gi225xyxCpx",  # Aqeedah & Beliefs
    "12XAXhHvXDOJN9ZTX_9_rgOYmUfvSudb8",  # History & Heritage
    "15h28hijX79rOCmBg6P1466_97KYyin4T",  # Sanabiyah Ulya container
]

def canonical_qawmi_pair(lvl: str, sub: str) -> tuple[str, str]:
    if lvl == "Fazilat":
        if sub == "Hadith & Sunnah":
            sub = "Hadith & Usulul Hadith"
        elif sub == "Tafseer & Al-Quran":
            sub = "Tafseer & Ulumul Quran"
        elif sub == "Fiqh & Madhhab":
            sub = "Fiqh & Usulul Fiqh"
        elif sub == "Arabic Language & Literature":
            sub = "Arabic Literature & Balaghat"
    elif lvl == "Common & Reference Books":
        if sub == "Tasawwuf & Akhlaq":
            sub = "Tasawwuf, Akhlaq & Dua"
        elif sub == "Seerah & Islamic History":
            sub = "Seerah, Akabir Biographies & Islamic History"
    elif lvl == "Takmil (Dawra-e-Hadith)":
        if sub == "Hadith & Sunnah":
            sub = "Dawra-e-Hadith Combined & General"
    return lvl, sub

def list_children_ids(folder_ids: list[str]) -> dict[str, str]:
    """Return {file_id: cur_parent_id} for all live files inside folder_ids."""
    parent_map: dict[str, str] = {}
    def one(pid):
        q = f"'{pid}' in parents and trashed = false"
        return pid, list(dapi.list_all(q=q, fields="id,mimeType"))
    with ThreadPoolExecutor(max_workers=10) as ex:
        for pid, items in ex.map(one, folder_ids):
            for it in items:
                if it.get("mimeType") != dapi.FOLDER:
                    parent_map[it["id"]] = pid
    return parent_map

def execute_moves(label: str, tasks: list[tuple[str, str, str, str]]) -> list[dict]:
    print(f"=== {label}: {len(tasks)} moves queued ===", flush=True)
    if not tasks:
        return []
    done = 0
    errors = []
    lock = threading.Lock()

    def do_one(t):
        fid, add_p, rem_p, fname = t
        dapi.move(fid, add_p, rem_p)
        return fid

    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(do_one, t): t for t in tasks}
        for fut in as_completed(futs):
            t = futs[fut]
            try:
                fut.result()
                with lock:
                    done += 1
                    if done % 100 == 0 or done == len(tasks):
                        print(f"  [{label}] {done}/{len(tasks)} moved", flush=True)
            except Exception as exc:
                errors.append({"id": t[0], "name": t[3], "error": str(exc)})
                print(f"  [ERR] {t[3]} ({t[0]}): {exc}", flush=True)
    return errors

def main():
    q_folders = json.loads((DATA / "qawmi_level_subject_folders.json").read_text(encoding="utf-8"))
    erows = json.loads((DATA / "english_books_migration_plan.json").read_text(encoding="utf-8"))
    qrows = json.loads((DATA / "qawmi_reorg_migration_plan.json").read_text(encoding="utf-8"))

    # 1. Scan live parent IDs in English Books subfolders
    print("Scanning remaining live files in English Books...", flush=True)
    eng_live_parents = list_children_ids(ENGLISH_SUBFOLDER_IDS)
    print(f"Live files still in English Books subfolders: {len(eng_live_parents)}", flush=True)

    qawmi_override = {
        "Sarhe miat Amel.pdf": q_folders["Mutawassitah/Arabic Language & Literature"],
        "Sharhe Jami.pdf": q_folders["Sanabiyah/Arabic Language & Literature"],
        "Al Misbahun Noori (Sharhe-Quduri) Part-01.pdf": q_folders["Sanabiyah/Fiqh & Madhhab"],
        "Al Misbahun Noori (Sharhe-Quduri) Part-02.pdf": q_folders["Sanabiyah/Fiqh & Madhhab"],
        "AL Subhunnuri sharhul kuduri VOL= 1,2 (In Arabic).pdf": q_folders["Sanabiyah/Fiqh & Madhhab"],
        "Jadut Talibeen.pdf": q_folders["Mutawassitah/Hadith & Sunnah"],
    }

    eng_tasks = []
    for r in erows:
        if r["action"] != "Move":
            continue
        fid = r["drive_file_id"]
        cur_p = eng_live_parents.get(fid)
        if not cur_p:
            continue  # Already moved by earlier local run!
        dest_id = qawmi_override.get(r["filename"], r["dest_folder_id"])
        if cur_p != dest_id:
            eng_tasks.append((fid, dest_id, cur_p, r["filename"]))

    eng_errs = execute_moves("English Books Migration", eng_tasks)

    # 2. Scan live parent IDs in Qawmi legacy/misc folders
    print("Scanning live files in Qawmi Madrasa legacy & misc folders...", flush=True)
    q_live_parents = list_children_ids([*LEGACY_QAWMI_SHELL_IDS, MISC_FOLDER_ID])
    print(f"Live files in Qawmi source folders: {len(q_live_parents)}", flush=True)

    q_tasks = []
    for r in qrows:
        fid = r["drive_file_id"]
        cur_p = q_live_parents.get(fid)
        if not cur_p:
            continue
        lvl, sub = canonical_qawmi_pair(r["proposed_level"], r["proposed_subject"])
        dest_id = q_folders[f"{lvl}/{sub}"]
        if cur_p != dest_id:
            q_tasks.append((fid, dest_id, cur_p, r["filename"]))

    q_errs = execute_moves("Qawmi Madrasa Reorganization", q_tasks)

    # 3. Archive verified-empty legacy Qawmi shells into Review & Unclassified (Qawmi)/Archived Empty Legacy Qawmi Folders
    rev_id = q_folders["Review & Unclassified (Qawmi)"]
    existing_rev_kids = list(dapi.list_all(q=f"'{rev_id}' in parents and mimeType = '{dapi.FOLDER}' and trashed = false", fields="id,name"))
    arch_id = next((x["id"] for x in existing_rev_kids if x["name"] == "Archived Empty Legacy Qawmi Folders"), None)
    if not arch_id:
        arch_id = dapi.mkdir("Archived Empty Legacy Qawmi Folders", rev_id)["id"]

    archived = 0
    for lid in LEGACY_QAWMI_SHELL_IDS:
        rem = list(dapi.list_all(q=f"'{lid}' in parents and trashed = false", fields="id"))
        if not rem:
            info = dapi.get(lid, fields="id,name,parents")
            cur_parents = info.get("parents") or []
            if cur_parents and cur_parents[0] != arch_id:
                dapi.move(lid, arch_id, cur_parents[0])
                archived += 1
        else:
            print(f"[SKIP-NONEMPTY] {lid} has {len(rem)} items", flush=True)

    summary = {
        "english_moves_executed": len(eng_tasks) - len(eng_errs),
        "english_errors": eng_errs,
        "qawmi_moves_executed": len(q_tasks) - len(q_errs),
        "qawmi_errors": q_errs,
        "legacy_empty_folders_archived": archived,
    }
    (DATA / "cloud_fast_reorg_result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== CLOUD FAST REORG SUMMARY ===", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if eng_errs or q_errs:
        sys.exit(1)

if __name__ == "__main__":
    main()
