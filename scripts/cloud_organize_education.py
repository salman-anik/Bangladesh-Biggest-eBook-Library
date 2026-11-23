#!/usr/bin/env python3
"""
Phase 1 & 2 Executor: Organize all existing resources inside `Education & Textbooks`
on Google Drive (via `library_tools/drive_api.py` on GitHub Actions).

CRITICAL SAFETY INVARIANT:
- `Qawmi Madrasa` (1oACGk9Yf70kBJGRdsNMVPBkFLhZNJ02O) and its shortcut inside Alia Madrasa
  (1i1XtTl1S-GBhZN8lDX4k-LPkiE4Kv1cx) are 100% OFF-LIMITS.
- Never delete any existing file; never overwrite existing files; create subfolders only
  when at least one real file/subfolder belongs inside them.
"""

from __future__ import annotations

import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "library_tools"))
import drive_api as dapi  # noqa: E402

EDU_ROOT_ID = "1Hoy8Zv0ObmQcGLrDUhmkGSYK_DDSK1BR"
GEN_EDU_ID = "1vFzQc7tNQk0JquTutgpRLBZWjgaP-412"
UNIV_EDU_ID = "1nmyPDZNogp78QSMioB8Jm8N9qpcum8hP"
MADRASA_ID = "1VO_Hd9yR2EA17zPaeLcYYfik3I1gG9zM"
ALIA_ID = "1_kES2hSESWdRgkbAib9EfOgKx4lIizPH"
BCS_ROOT_ID = "1N4WBU0dH2vHCvQ_2LmKRTTHiqeqEVD6x"

# Subfolders under General Education
PRIMARY_ID = "1-EaZBohJwsOiaMy4-Udlcfx35vicb6p9"
SECONDARY_ID = "1WU2EH838pfxibXEEnc1f8h4_EI8PQglO"
HSC_OLD_ID = "1eLoOJlVOTm_z1Jd9PgJ2o4pYJ_JeUFPU"
ADMISSION_OLD_ID = "12bPXR_IlHukYrfJgC6wxSyzqq20H7pQd"
OTHER_SCHOOL_ID = "1ri9HaWFnWfOl36miTJOVmIMJqbeHZnN0"

# Subfolders under Alia Madrasa
DAKHIL_ID = "12zo0KsCpeuFomj4ZnMCUyjwLdn9HL3sK"
EBTEDAYEE_ID = "1aA4qAiVXCHUBFpMK9i-sPCVf1Rn3TUUJ"
ALIA_GEN_ID = "1T6YBUBeRpUUaaIEWSK5EMOw6ptu5uJ4n"

# STRICTLY OFF-LIMITS IDS
QAWMI_ROOT_ID = "1oACGk9Yf70kBJGRdsNMVPBkFLhZNJ02O"
QAWMI_SHORTCUT_ID = "1i1XtTl1S-GBhZN8lDX4k-LPkiE4Kv1cx"
FORBIDDEN_IDS = {QAWMI_ROOT_ID, QAWMI_SHORTCUT_ID}


def assert_safe_id(fid: str, context: str = "") -> None:
    if fid in FORBIDDEN_IDS:
        raise RuntimeError(f"SAFETY ABORT: attempted operation on forbidden Qawmi ID {fid} ({context})")


def snapshot_qawmi() -> dict[str, Any]:
    meta = dapi.get(QAWMI_ROOT_ID, fields="id,name,modifiedTime,parents,trashed")
    children = list(
        dapi.list_all(
            q=f"'{QAWMI_ROOT_ID}' in parents and trashed = false",
            fields="id,name,mimeType,modifiedTime",
        )
    )
    shortcut_meta = None
    try:
        shortcut_meta = dapi.get(QAWMI_SHORTCUT_ID, fields="id,name,modifiedTime,parents,trashed")
    except Exception:
        pass
    return {
        "meta": meta,
        "child_count": len(children),
        "children_sig": sorted(f"{c['id']}:{c['name']}:{c.get('modifiedTime','')}" for c in children),
        "shortcut_meta": shortcut_meta,
    }


class FolderManager:
    """Thread-safe lazy folder creator that reuses existing Drive folders."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._children_loaded: set[str] = set()
        self._cache: dict[tuple[str, str], str] = {}
        self.created_folders: list[dict[str, str]] = []

    def _load_parent(self, parent_id: str) -> None:
        assert_safe_id(parent_id, "load_parent")
        if parent_id in self._children_loaded:
            return
        items = list(
            dapi.list_all(
                q=f"'{parent_id}' in parents and mimeType = '{dapi.FOLDER}' and trashed = false",
                fields="id,name",
            )
        )
        for it in items:
            self._cache[(parent_id, it["name"])] = it["id"]
        self._children_loaded.add(parent_id)

    def get_or_create(self, parent_id: str, name: str) -> str:
        assert_safe_id(parent_id, f"get_or_create({name})")
        with self._lock:
            self._load_parent(parent_id)
            key = (parent_id, name)
            if key in self._cache:
                fid = self._cache[key]
                assert_safe_id(fid, f"cached({name})")
                return fid
            created = dapi.mkdir(name, parent_id)
            fid = created["id"]
            self._cache[key] = fid
            self.created_folders.append({"id": fid, "name": name, "parent_id": parent_id})
            return fid

    def ensure_path(self, root_id: str, parts: list[str]) -> str:
        curr = root_id
        for part in parts:
            curr = self.get_or_create(curr, part)
        return curr


def list_direct_children(parent_id: str) -> list[dict[str, Any]]:
    assert_safe_id(parent_id, "list_direct_children")
    return list(
        dapi.list_all(
            q=f"'{parent_id}' in parents and trashed = false",
            fields="id,name,mimeType,parents,size,md5Checksum,modifiedTime",
        )
    )


def classify_primary_class(name: str) -> list[str]:
    low = name.lower()
    if any(k in name for k in ("প্রাক-প্রাথমিক", "প্রাক প্রাথমিক")) or "pre-primary" in low or "pre primary" in low:
        return ["Primary Education", "Pre-Primary"]
    if any(k in name for k in ("প্রথম শ্রেণি", "১ম শ্রেণি")) or re.search(r"\bclass[- _]?1\b|\bprothom\b", low):
        return ["Primary Education", "Class 1"]
    if any(k in name for k in ("দ্বিতীয় শ্রেণি", "দ্বিতীয় শ্রেণি", "২য় শ্রেণি")) or re.search(r"\bclass[- _]?2\b|\bdwitij", low):
        return ["Primary Education", "Class 2"]
    if any(k in name for k in ("তৃতীয় শ্রেণি", "তৃতীয় শ্রেণি", "৩য় শ্রেণি")) or re.search(r"\bclass[- _]?3\b|\btritij", low):
        return ["Primary Education", "Class 3"]
    if any(k in name for k in ("চতুর্থ শ্রেণি", "৪র্থ শ্রেণি")) or re.search(r"\bclass[- _]?4\b|\bchoturth", low):
        return ["Primary Education", "Class 4"]
    if any(k in name for k in ("পঞ্চম শ্রেণি", "৫ম শ্রেণি")) or re.search(r"\bclass[- _]?5\b|\bponchom", low):
        return ["Primary Education", "Class 5"]
    return ["NCTB Textbooks", "Primary"]


def classify_secondary_file(name: str) -> tuple[str, list[str]]:
    """Return ('general'|'academic', path_parts)."""
    low = name.lower()
    if "saifur" in low:
        return ("academic", ["Coaching & Training Center Materials", "Coaching Center Collections", "Saifur's"])
    if any(k in low for k in ("ssc qps", "board question", "board exam", "suggestion", "test paper")):
        return ("general", ["Board Examination", "SSC", "Science"])
    if any(k in low for k in ("class six", "class 6", "class-6", "ষষ্ঠ")):
        return ("general", ["Secondary Education", "Class 6"])
    if any(k in low for k in ("class seven", "class 7", "class-7", "সপ্তম")):
        return ("general", ["Secondary Education", "Class 7"])
    if any(k in low for k in ("class eight", "class 8", "class-8", "অষ্টম")):
        return ("general", ["Secondary Education", "Class 8"])
    if any(k in low for k in ("class-9", "class 9", "নবম")):
        return ("general", ["Secondary Education", "Class 9"])
    if any(k in low for k in ("class 10", "class-10", "দশম")):
        return ("general", ["Secondary Education", "Class 10"])
    return ("general", ["NCTB Textbooks", "Secondary"])


def classify_hsc_file(name: str) -> tuple[str, list[str]]:
    """Return ('general'|'academic'|'university', path_parts)."""
    low = name.lower()
    if "saifur" in low:
        return ("academic", ["Coaching & Training Center Materials", "Coaching Center Collections", "Saifur's"])
    if "udvash" in low:
        return ("academic", ["Coaching & Training Center Materials", "Coaching Center Collections", "Udvash"])
    if "unmesh" in low:
        return ("academic", ["Coaching & Training Center Materials", "Coaching Center Collections", "Unmesh"])
    if "retina" in low:
        return ("academic", ["Coaching & Training Center Materials", "Coaching Center Collections", "Retina"])
    if "10 minute school" in low:
        return ("academic", ["Coaching & Training Center Materials", "Coaching Center Collections", "10 Minute School"])
    if "admission" in low or "medical" in low or "buet" in low:
        return ("university", ["Admission Preparation", "Previous Admission Questions"])

    # NCTB Official Higher Secondary Textbooks
    is_nctb = ("nctb" in low) or any(
        k in name for k in ("একাদশ দ্বাদশ", "একাদশ-দ্বাদশ", "উচ্চ মাধ্যমিক")
    ) and not any(k in low for k in ("panjeree", "lecture", "royal", "guide", "suggestion", "model test", "test paper", "cq", "mcq", "question"))

    if is_nctb:
        return ("general", ["NCTB Textbooks", "Higher Secondary"])

    if any(k in low for k in ("suggestion", "model test", "board question", "test paper", "cq ", "mcq")):
        if any(k in low for k in ("physics", "chemistry", "biology", "math", "ict", "botany", "zoology", "agriculture")):
            return ("general", ["Board Examination", "HSC", "Science"])
        if any(k in low for k in ("accounting", "finance", "business", "management", "marketing", "economics")):
            return ("general", ["Board Examination", "HSC", "Business Studies"])
        if any(k in low for k in ("history", "civics", "geography", "logic", "sociology", "social work", "islamic")):
            return ("general", ["Board Examination", "HSC", "Humanities"])
        return ("general", ["Board Examination", "HSC", "Model Tests"])

    # Subject-wise books & guides
    if any(k in low for k in ("ict", "information and communication", "তথ্য ও যোগাযোগ")):
        return ("general", ["Subject-wise Books", "ICT"])
    if any(k in low for k in ("physics", "পদার্থ")):
        return ("general", ["Subject-wise Books", "Physics"])
    if any(k in low for k in ("chemistry", "রসায়ন", "রসায়ন")):
        return ("general", ["Subject-wise Books", "Chemistry"])
    if any(k in low for k in ("biology", "botany", "zoology", "জীববিজ্ঞান")):
        return ("general", ["Subject-wise Books", "Biology"])
    if any(k in low for k in ("math", "গণিত", "উচ্চতর গণিত")):
        return ("general", ["Subject-wise Books", "Mathematics"])
    if any(k in low for k in ("accounting", "হিসাববিজ্ঞান")):
        return ("general", ["Subject-wise Books", "Accounting"])
    if any(k in low for k in ("finance", "banking", "ফিন্যান্স")):
        return ("general", ["Subject-wise Books", "Finance & Banking"])
    if any(k in low for k in ("economics", "অর্থনীতি")):
        return ("general", ["Subject-wise Books", "Economics"])
    if any(k in low for k in ("history", "ইতিহাস")):
        return ("general", ["Subject-wise Books", "History"])
    if any(k in low for k in ("geography", "ভূগোল")):
        return ("general", ["Subject-wise Books", "Geography"])
    if any(k in low for k in ("civics", "পৌরনীতি")):
        return ("general", ["Subject-wise Books", "Civics & Good Governance"])
    if any(k in low for k in ("bangla", "বাংলা", "সহপাঠ", "ব্যাকরণ", "ovizatri")):
        return ("general", ["Subject-wise Books", "Bangla"])
    if any(k in low for k in ("english", "grammar", "ইংরেজি")):
        return ("general", ["Subject-wise Books", "English"])

    if any(k in low for k in ("business", "management", "marketing", "production", "statistics")):
        return ("general", ["Higher Secondary Education", "Business Studies"])
    if any(k in low for k in ("logic", "sociology", "social work", "psychology", "islamic")):
        return ("general", ["Higher Secondary Education", "Humanities"])
    if any(k in low for k in ("class 11", "11 ", "একাদশ", "1st paper", "first paper")):
        return ("general", ["Higher Secondary Education", "Class 11"])
    if any(k in low for k in ("class 12", "12 ", "দ্বাদশ", "2nd paper", "second paper")):
        return ("general", ["Higher Secondary Education", "Class 12"])
    return ("general", ["Higher Secondary Education", "Science"])


def classify_university_file(name: str) -> list[str]:
    low = name.lower()
    if any(k in low for k in ("python",)):
        return ["Computer Science & IT", "Programming", "Python"]
    if any(k in low for k in ("c++", "c how to", "c programming")):
        return ["Computer Science & IT", "Programming", "C & C++"]
    if "java" in low and "javascript" not in low:
        return ["Computer Science & IT", "Programming", "Java"]
    if any(k in low for k in ("data science", "data analytics")):
        return ["Computer Science & IT", "Data Science"]
    if any(k in low for k in ("machine learning", "deep learning", "artificial intelligence", "neural network")):
        return ["Computer Science & IT", "Machine Learning"]
    if any(k in low for k in ("information systems", "computer science", "workplace software")):
        return ["Computer Science & IT", "Software Engineering"]
    if any(k in low for k in ("antenna", "ray theory", "modes of a step", "transmission", "tocci", "digital systems", "circuit", "electronics", "signal")):
        return ["Engineering & Technology", "Electrical & Electronic Engineering"]
    if any(k in low for k in ("rotational", "fluid mechanics", "hydraulics", "thermodynamics", "mechanics")):
        return ["Engineering & Technology", "Mechanical Engineering"]
    if any(k in low for k in ("statistics", "probability")):
        return ["Science & Mathematics", "Statistics"]
    if any(k in low for k in ("calculus", "algebra", "trigonometry", "prealgebra", "precalculus", "geometry", "vector product", "mathematics", "math")):
        return ["Science & Mathematics", "Mathematics"]
    if any(k in low for k in ("physics", "astronomy", "fusion reactor", "x-ray", "x — ray", "quantum", "optics")):
        return ["Science & Mathematics", "Physics"]
    if any(k in low for k in ("organic chemistry", "chemistry")):
        return ["Science & Mathematics", "Chemistry"]
    if any(k in low for k in ("biology", "microbiology", "anatomy", "physiology")):
        return ["Science & Mathematics", "Biology"]
    if any(k in low for k in ("microeconomics", "macroeconomics", "economics")):
        return ["Business & Economics", "Economics"]
    if any(k in low for k in ("accounting",)):
        return ["Business & Economics", "Accounting"]
    if any(k in low for k in ("finance",)):
        return ["Business & Economics", "Finance"]
    if any(k in low for k in ("marketing",)):
        return ["Business & Economics", "Marketing"]
    if any(k in low for k in ("management", "organizational behavior", "entrepreneurship", "business ethics")):
        return ["Business & Economics", "Management"]
    if any(k in low for k in ("psychology", "psychologia")):
        return ["Arts & Humanities", "Psychology"]
    if any(k in low for k in ("sociology",)):
        return ["Arts & Humanities", "Sociology"]
    if any(k in low for k in ("philosophy", "ethics")):
        return ["Arts & Humanities", "Philosophy"]
    if any(k in low for k in ("history", "american government")):
        return ["Arts & Humanities", "History"]
    if any(k in low for k in ("writing guide", "literature", "english")):
        return ["Arts & Humanities", "English Literature"]
    return ["Undergraduate", "Honours & Degree Books"]


def classify_ebtedayee_file(name: str) -> list[str]:
    low = name.lower()
    if any(k in name for k in ("প্রথম", "১ম")) or re.search(r"\bprothom\b|\bclass[- _]?1\b|\b(?:one|1st)\b", low):
        return ["Ebtedayee", "Class 1"]
    if any(k in name for k in ("দ্বিতীয়", "দ্বিতীয়", "২য়")) or re.search(r"\bdwitij|\bclass[- _]?2\b|\b(?:two|2nd)\b", low):
        return ["Ebtedayee", "Class 2"]
    if any(k in name for k in ("তৃতীয়", "তৃতীয়", "৩য়")) or re.search(r"\btritij|\bclass[- _]?3\b|\b(?:three|3rd)\b", low):
        return ["Ebtedayee", "Class 3"]
    if any(k in name for k in ("চতুর্থ", "৪র্থ")) or re.search(r"\bchoturth|\bfour\b|\bclass[- _]?4\b|\b4th\b", low):
        return ["Ebtedayee", "Class 4"]
    if any(k in name for k in ("পঞ্চম", "৫ম")) or re.search(r"\bponchom|\bfive\b|\bclass[- _]?5\b|\b5th\b", low):
        return ["Ebtedayee", "Class 5"]
    return ["Subject-wise Books", "Islamic Studies"]


def classify_dakhil_file(name: str) -> list[str]:
    low = name.lower()
    if any(k in name for k in ("ষষ্ঠ", "৬ষ্ঠ")) or re.search(r"\bshoshth|\bsix\b|\bclass[- _]?6\b|\b6th\b", low):
        return ["Dakhil", "Class 6"]
    if any(k in name for k in ("সপ্তম", "৭ম")) or re.search(r"\bsoptom|\bseven\b|\bclass[- _]?7\b|\b7th\b", low):
        return ["Dakhil", "Class 7"]
    if any(k in name for k in ("অষ্টম", "৮ম")) or re.search(r"\boshtom|\beight\b|\bclass[- _]?8\b|\b8th\b", low):
        return ["Dakhil", "Class 8"]
    if any(k in name for k in ("দশম", "১০ম")) and not any(k in name for k in ("নবম", "৯ম")):
        return ["Dakhil", "Class 10"]
    if any(k in name for k in ("নবম", "৯ম")) or re.search(r"\bnobom|\bnine\b|\bclass[- _]?9\b|\b9th\b", low):
        return ["Dakhil", "Class 9"]
    if re.search(r"\bten\b|\bclass[- _]?10\b|\b10th\b", low):
        return ["Dakhil", "Class 10"]
    return ["Subject-wise Books", "Islamic Studies"]


def classify_bcs_file(name: str) -> tuple[str, list[str]]:
    low = name.lower()
    if low.startswith("hsc-") or "hsc" in low:
        if any(k in low for k in ("accounting", "management")):
            return ("general", ["Higher Secondary Education", "Business Studies"])
        return ("general", ["Higher Secondary Education", "Science"])
    if "ru question bank" in low:
        return ("university", ["Admission Preparation", "Public University"])
    if "bank" in low:
        return ("academic", ["Coaching & Training Center Materials", "Job Preparation Coaching", "Bank Jobs"])
    if "bcs" in low:
        return ("academic", ["Coaching & Training Center Materials", "Job Preparation Coaching", "BCS"])
    if any(k in low for k in ("bpsc", "dghs", "ministry", "primary", "issb", "biman", "job")):
        return ("academic", ["Coaching & Training Center Materials", "Job Preparation Coaching", "Government Jobs"])
    return ("academic", ["Coaching & Training Center Materials", "Job Preparation Coaching", "Other Competitive Exams"])


def execute_moves(moves: list[tuple[dict[str, Any], str, str]], max_workers: int = 8) -> tuple[int, list[dict[str, str]]]:
    """Each entry is (item_dict, old_parent_id, new_parent_id)."""
    ok = 0
    errors: list[dict[str, str]] = []
    filtered: list[tuple[dict[str, Any], str, str]] = []
    for item, old_p, new_p in moves:
        assert_safe_id(item["id"], f"move {item['name']}")
        assert_safe_id(old_p, f"old_parent {item['name']}")
        assert_safe_id(new_p, f"new_parent {item['name']}")
        if old_p != new_p:
            filtered.append((item, old_p, new_p))

    def _one(task: tuple[dict[str, Any], str, str]) -> None:
        item, old_p, new_p = task
        dapi.move(item["id"], new_p, old_p)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {ex.submit(_one, t): t for t in filtered}
        for fut in as_completed(fut_map):
            item, old_p, new_p = fut_map[fut]
            try:
                fut.result()
                ok += 1
            except Exception as exc:
                errors.append({"id": item["id"], "name": item["name"], "error": str(exc)})
    return ok, errors


def trash_if_empty_non_qawmi(folder_id: str, label: str) -> bool:
    assert_safe_id(folder_id, f"trash_if_empty({label})")
    left = list_direct_children(folder_id)
    if len(left) == 0:
        dapi.trash(folder_id)
        print(f"  Trashed verified-empty shell folder: {label} ({folder_id})")
        return True
    print(f"  Kept folder (still has {len(left)} items): {label} ({folder_id})")
    return False


def main() -> None:
    print("Taking pre-flight snapshot of Qawmi Madrasa (OFF-LIMITS)...")
    q_before = snapshot_qawmi()
    print(f"Qawmi pre-flight: {q_before['child_count']} direct folders, modifiedTime={q_before['meta'].get('modifiedTime')}")

    fm = FolderManager()
    acad_res_id = fm.get_or_create(EDU_ROOT_ID, "Academic Resources")

    # Rename Higher Secondary (Class 11-12) -> Higher Secondary Education if needed
    hsc_meta = dapi.get(HSC_OLD_ID, fields="id,name")
    if hsc_meta["name"] != "Higher Secondary Education":
        dapi.rename(HSC_OLD_ID, "Higher Secondary Education")
        print(f"Renamed {hsc_meta['name']} -> Higher Secondary Education")

    total_moved = 0
    all_errors: list[dict[str, str]] = []
    section_counts: dict[str, int] = {}

    def plan_and_run(label: str, tasks: list[tuple[dict[str, Any], str, str]]) -> None:
        nonlocal total_moved
        print(f"[{label}] Planning {len(tasks)} moves...")
        moved, errs = execute_moves(tasks, max_workers=8)
        total_moved += moved
        all_errors.extend(errs)
        section_counts[label] = moved
        print(f"[{label}] Moved {moved}, Errors {len(errs)}")

    # 1. FIRST relocate Admission & Entrance Preparation subfolders so FolderManager reuses them cleanly
    adm_moves: list[tuple[dict[str, Any], str, str]] = []
    adm_children = {c["name"]: c for c in list_direct_children(ADMISSION_OLD_ID)}
    if adm_children:
        univ_adm_id = fm.ensure_path(UNIV_EDU_ID, ["Admission Preparation"])
        hsc_board_id = fm.ensure_path(GEN_EDU_ID, ["Board Examination", "HSC"])
        study_guides_id = fm.ensure_path(acad_res_id, ["Study Guides"])
        coach_col_id = fm.ensure_path(acad_res_id, ["Coaching & Training Center Materials", "Coaching Center Collections"])

        if "Engineering & Technology Admission" in adm_children:
            c = adm_children["Engineering & Technology Admission"]
            dapi.rename(c["id"], "Engineering University")
            adm_moves.append((c, ADMISSION_OLD_ID, univ_adm_id))
        if "Medical & Dental Admission" in adm_children:
            c = adm_children["Medical & Dental Admission"]
            dapi.rename(c["id"], "Medical & Dental")
            adm_moves.append((c, ADMISSION_OLD_ID, univ_adm_id))
        if "Agriculture Admission" in adm_children:
            c = adm_children["Agriculture Admission"]
            dapi.rename(c["id"], "Agricultural University")
            adm_moves.append((c, ADMISSION_OLD_ID, univ_adm_id))
        if "University Admission" in adm_children:
            ua = adm_children["University Admission"]
            for sub in list_direct_children(ua["id"]):
                if sub["name"] == "Public Universities":
                    dapi.rename(sub["id"], "Public University")
                elif sub["name"] == "Private Universities":
                    dapi.rename(sub["id"], "Private University")
                adm_moves.append((sub, ua["id"], univ_adm_id))
        if "HSC & Academic Preparation" in adm_children:
            hsc_prep = adm_children["HSC & Academic Preparation"]
            for sub in list_direct_children(hsc_prep["id"]):
                if sub["name"] == "Board Questions":
                    dapi.rename(sub["id"], "Previous Year Questions")
                adm_moves.append((sub, hsc_prep["id"], hsc_board_id))
        if "General Competitive Exams" in adm_children:
            c = adm_children["General Competitive Exams"]
            dapi.rename(c["id"], "Competitive Exams")
            adm_moves.append((c, ADMISSION_OLD_ID, study_guides_id))
        if "Publisher & Coaching Collections" in adm_children:
            pcc = adm_children["Publisher & Coaching Collections"]
            for sub in list_direct_children(pcc["id"]):
                adm_moves.append((sub, pcc["id"], coach_col_id))

    plan_and_run("Admission Folders Relocation", adm_moves)
    for sub_name in ("University Admission", "HSC & Academic Preparation", "Publisher & Coaching Collections"):
        if sub_name in adm_children:
            trash_if_empty_non_qawmi(adm_children[sub_name]["id"], f"Admission/{sub_name}")
    trash_if_empty_non_qawmi(ADMISSION_OLD_ID, "General Education/Admission & Entrance Preparation")

    # 2. General Education -> Primary, Secondary, HSC, Other School Resources (reuses relocated folders!)
    gen_moves: list[tuple[dict[str, Any], str, str]] = []

    for item in list_direct_children(PRIMARY_ID):
        if item["mimeType"] == dapi.FOLDER:
            continue
        dst = fm.ensure_path(GEN_EDU_ID, classify_primary_class(item["name"]))
        gen_moves.append((item, PRIMARY_ID, dst))

    for item in list_direct_children(SECONDARY_ID):
        if item["mimeType"] == dapi.FOLDER:
            continue
        scope, path = classify_secondary_file(item["name"])
        root = GEN_EDU_ID if scope == "general" else acad_res_id
        dst = fm.ensure_path(root, path)
        gen_moves.append((item, SECONDARY_ID, dst))

    for item in list_direct_children(HSC_OLD_ID):
        if item["mimeType"] == dapi.FOLDER:
            continue
        scope, path = classify_hsc_file(item["name"])
        root = GEN_EDU_ID if scope == "general" else (UNIV_EDU_ID if scope == "university" else acad_res_id)
        dst = fm.ensure_path(root, path)
        gen_moves.append((item, HSC_OLD_ID, dst))

    for item in list_direct_children(OTHER_SCHOOL_ID):
        if item["mimeType"] == dapi.FOLDER:
            continue
        low = item["name"].lower()
        if "nctb" in low or "kormomukhi" in low:
            dst = fm.ensure_path(GEN_EDU_ID, ["NCTB Textbooks", "Secondary"])
        else:
            dst = fm.ensure_path(GEN_EDU_ID, classify_primary_class(item["name"]))
        gen_moves.append((item, OTHER_SCHOOL_ID, dst))

    plan_and_run("General Education Files", gen_moves)
    trash_if_empty_non_qawmi(OTHER_SCHOOL_ID, "General Education/Other School Resources")

    # 3. University Education -> Level / Subject folders
    univ_moves: list[tuple[dict[str, Any], str, str]] = []
    for item in list_direct_children(UNIV_EDU_ID):
        if item["mimeType"] == dapi.FOLDER:
            continue
        dst = fm.ensure_path(UNIV_EDU_ID, classify_university_file(item["name"]))
        univ_moves.append((item, UNIV_EDU_ID, dst))
    plan_and_run("University Education", univ_moves)

    # 4. Alia Madrasa -> Ebtedayee/Class 1-5, Dakhil/Class 6-10, Fazil, Subject-wise
    alia_moves: list[tuple[dict[str, Any], str, str]] = []
    for item in list_direct_children(EBTEDAYEE_ID):
        if item["mimeType"] == dapi.FOLDER:
            continue
        dst = fm.ensure_path(ALIA_ID, classify_ebtedayee_file(item["name"]))
        alia_moves.append((item, EBTEDAYEE_ID, dst))

    for item in list_direct_children(DAKHIL_ID):
        if item["mimeType"] == dapi.FOLDER:
            continue
        dst = fm.ensure_path(ALIA_ID, classify_dakhil_file(item["name"]))
        alia_moves.append((item, DAKHIL_ID, dst))

    for item in list_direct_children(ALIA_ID):
        if item["mimeType"] in (dapi.FOLDER, dapi.SHORTCUT) or item["id"] in FORBIDDEN_IDS:
            continue
        low = item["name"].lower()
        if "fazil" in low and ("1st" in low or "first" in low):
            dst = fm.ensure_path(ALIA_ID, ["Fazil", "First Year"])
        elif "four" in low:
            dst = fm.ensure_path(ALIA_ID, ["Ebtedayee", "Class 4"])
        elif "6" in low or "arbi 6" in low:
            dst = fm.ensure_path(ALIA_ID, ["Dakhil", "Class 6"])
        else:
            dst = fm.ensure_path(ALIA_ID, ["Subject-wise Books", "Islamic Studies"])
        alia_moves.append((item, ALIA_ID, dst))

    for item in list_direct_children(ALIA_GEN_ID):
        if item["mimeType"] in (dapi.FOLDER, dapi.SHORTCUT) or item["id"] in FORBIDDEN_IDS:
            continue
        dst = fm.ensure_path(ALIA_ID, ["Subject-wise Books", "Islamic Studies"])
        alia_moves.append((item, ALIA_GEN_ID, dst))

    plan_and_run("Alia Madrasa", alia_moves)
    trash_if_empty_non_qawmi(ALIA_GEN_ID, "Alia Madrasa/General")

    # 5. Professional & Job Exams (BCS) -> Academic Resources / Job Preparation Coaching + split HSC/RU
    bcs_moves: list[tuple[dict[str, Any], str, str]] = []
    for item in list_direct_children(BCS_ROOT_ID):
        if item["mimeType"] == dapi.FOLDER:
            continue
        scope, path = classify_bcs_file(item["name"])
        root = GEN_EDU_ID if scope == "general" else (UNIV_EDU_ID if scope == "university" else acad_res_id)
        dst = fm.ensure_path(root, path)
        bcs_moves.append((item, BCS_ROOT_ID, dst))
    plan_and_run("Professional & Job Exams (BCS)", bcs_moves)
    trash_if_empty_non_qawmi(BCS_ROOT_ID, "Education & Textbooks/Professional & Job Exams (BCS)")

    # Post-flight verification of Qawmi Madrasa (MUST BE 100% IDENTICAL)
    q_after = snapshot_qawmi()
    q_unchanged = (
        q_before["child_count"] == q_after["child_count"]
        and q_before["children_sig"] == q_after["children_sig"]
        and q_before["meta"].get("modifiedTime") == q_after["meta"].get("modifiedTime")
    )
    if not q_unchanged:
        raise RuntimeError(f"QAWMI VERIFICATION FAILED!\nBEFORE: {q_before}\nAFTER: {q_after}")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_moved": total_moved,
        "errors_count": len(all_errors),
        "errors": all_errors,
        "section_counts": section_counts,
        "created_folders_count": len(fm.created_folders),
        "created_folders": fm.created_folders,
        "academic_resources_folder_id": acad_res_id,
        "qawmi_madrasa_verified_unchanged": True,
        "qawmi_direct_folder_count": q_after["child_count"],
        "qawmi_modified_time": q_after["meta"].get("modifiedTime"),
    }
    report_path = ROOT / "reports" / "education_reorg_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DONE: total_moved={total_moved}, errors={len(all_errors)}, qawmi_unchanged={q_unchanged}")


if __name__ == "__main__":
    main()
