#!/usr/bin/env python3
"""Build a strictly filtered, collision-free Stage D safe rename plan.

Reads all 7 Stage C dry-run reports in `reports/renamer/`, filters out cosmetic
em-dash swaps, collisions, ALL-CAPS downgrades, uploader/scanner metadata
(`Sumon`, `SCC`, `Joy`, etc.), Bijoy/OCR matra corruption, Bangla->Banglish
downgrades, unrelated metadata replacements, NCTB year overwrites, and volume
mismatches, leaving ONLY genuinely defective filenames fixed cleanly.

Strictly read-only on Google Drive. Writes:
- `reports/renamer/safe_stage_d_plan.json`
- `reports/renamer/SAFE_STAGE_D_PREVIEW.md`
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

REPORT_FILES = [
    "reports/renamer/rename_report_english_books.json",
    "reports/renamer/rename_report_reference_research.json",
    "reports/renamer/rename_report_series_collections.json",
    "reports/renamer/rename_report_authors_scholars.json",
    "reports/renamer/rename_report_education_textbooks.json",
    "reports/renamer/rename_report_religion_books.json",
    "reports/renamer/rename_report_bangla_books.json",
]

HAS_BN_RE = re.compile(r"[\u0980-\u09ff]")
HAS_LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")
MOJIBAKE_CHAR_RE = re.compile(r"[\x00-\x1f\u0080-\u00ff\ufffd]")
BN_LEADING_MATRA_RE = re.compile(r"(?:^|\s)[\u09be-\u09cd\u09d7]")
RANDOM_ID_RE = re.compile(r"^(?:[0-9A-Za-z_-]{16,}|local media\d*|untitled.*|compressed.*|document\d*|\d+|(?:ml|pdf|doc|eng|english|bn)[-_ ]?\d+[a-z0-9]*)$", re.I)
SITE_SPAM_RE = re.compile(
    r"(?:\([^)]*(?:\.(?:com|org|net|info|xyz|tk|bd)|blogspot|unknown author|copy)[^)]*\)"
    r"|\[[^\]]*(?:\.(?:com|org|net|info|xyz|tk|bd)|bdebooks|porageducation|boighar|amarboi|murchona|muminbd)[^\]]*\]"
    r"|bdebooks|porageducation|boighar|amarboi|murchona|muminbd|granthaagar|bengaliebook|pdfboi|almodina)",
    re.I,
)
WELL_FORMED_SEP_RE = re.compile(r"\s+[—–-]\s+")
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
BN_YEAR_RE = re.compile(r"(?:১৯|২০)[০-৯]{2}")
REVERSED_AUTHOR_RE = re.compile(r"[A-Za-z][A-Za-z.'\- ]{1,30},\s*[A-Za-z][A-Za-z.'\- ]{1,30}")
DIRTY_CHARS_RE = re.compile(
    r"[;?\ufffd\x00-\x1f]|,\s*$|\{\s*[^}]+\s*\}|Ed\.\s*\d|\b\w+,\w+\b|\((?:Author|Ed\.?|Editor|Translator)\)|[A-Za-z]\d+$|Guiadance",
    re.I,
)
SERIES_PREFIX_RE = re.compile(r"^(\[\d+(?:-\d+)?\]\s*[^—–-]+?)\s*[—–-]\s*(.+)$")
VOLUME_ONLY_SEGMENT_RE = re.compile(
    r"^(?:\d{1,2}|[১-৯][০-৯]?|.*(?:খন্ড|খণ্ড|পর্ব|অধ্যায়|অধ্যায়|\bpart\b|\bvol\b|\bvolume\b).*)$",
    re.I,
)

BAD_AUTHOR_HANDLES = {
    "sumon",
    "admin",
    "user",
    "pc",
    "owner",
    "scanner",
    "anonymous",
    "unknown",
    "dell",
    "hp",
    "lenovo",
    "asus",
    "acer",
    "microsoft",
    "adobe",
    "windows",
    "bdebooks",
    "porageducation",
    "zakir naik bangla",
    "muminbd",
    "sunnah trust",
    "scc",
    "joy",
    "hira",
    "john",
    "nirzhar",
    "alamgir",
}

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
ORDINAL_MAP = {
    "১ম": 1, "প্রথম": 1, "i": 1,
    "২য়": 2, "২য়": 2, "দ্বিতীয়": 2, "দ্বিতীয়": 2, "ii": 2,
    "৩য়": 3, "৩য়": 3, "তৃতীয়": 3, "তৃতীয়": 3, "iii": 3,
    "৪র্থ": 4, "চতুর্থ": 4, "iv": 4,
    "৫ম": 5, "পঞ্চম": 5, "v": 5,
    "৬ষ্ঠ": 6, "ষষ্ঠ": 6, "vi": 6,
    "৭ম": 7, "সপ্তম": 7, "vii": 7,
    "৮ম": 8, "অষ্টম": 8, "viii": 8,
    "৯ম": 9, "নবম": 9, "ix": 9,
    "১০ম": 10, "দশম": 10, "x": 10,
    "১১তম": 11, "একাদশ": 11, "xi": 11,
    "১২তম": 12, "দ্বাদশ": 12, "xii": 12,
    "১৩তম": 13, "ত্রয়োদশ": 13, "ত্রয়োদশ": 13, "xiii": 13,
    "১৪তম": 14, "চতুর্দশ": 14, "xiv": 14,
    "১৫তম": 15, "পঞ্চদশ": 15, "xv": 15,
    "১৬তম": 16, "ষষ্ঠদশ": 16, "ষোড়শ": 16, "ষোড়শ": 16, "xvi": 16,
    "১৭তম": 17, "সপ্তদশ": 17, "xvii": 17,
    "১৮তম": 18, "অষ্টাদশ": 18, "xviii": 18,
    "১৯তম": 19, "ঊনবিংশ": 19, "xix": 19,
    "২০তম": 20, "বিংশ": 20, "xx": 20,
}
VOL_TOKEN_RE = re.compile(
    r"(?:(?:part|vol\.?|volume|খন্ড|খণ্ড|পর্ব|অধ্যায়|অধ্যায়)\s*[-.:#]*\s*"
    r"(\d{1,2}|[১-৯][০-৯]?|\d+তম|১ম|২য়|২য়|৩য়|৩য়|৪র্থ|৫ম|৬ষ্ঠ|৭ম|৮ম|৯ম|১০ম|"
    r"১১তম|১২তম|১৩তম|১৪তম|১৫তম|১৬তম|১৭তম|১৮তম|১৯তম|২০তম|"
    r"প্রথম|দ্বিতীয়|দ্বিতীয়|তৃতীয়|তৃতীয়|চতুর্থ|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম|"
    r"একাদশ|দ্বাদশ|ত্রয়োদশ|ত্রয়োদশ|চতুর্দশ|পঞ্চদশ|ষষ্ঠদশ|ষোড়শ|ষোড়শ|সপ্তদশ|অষ্টাদশ|ঊনবিংশ|বিংশ)\b)"
    r"|(?:^|\s|[-–])(\d+তম|১ম|২য়|২য়|৩য়|৩য়|৪র্থ|৫ম|৬ষ্ঠ|৭ম|৮ম|৯ম|১০ম|"
    r"১১তম|১২তম|১৩তম|১৪তম|১৫তম|১৬তম|১৭তম|১৮তম|১৯তম|২০তম|"
    r"প্রথম|দ্বিতীয়|দ্বিতীয়|তৃতীয়|তৃতীয়|চতুর্থ|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম|"
    r"একাদশ|দ্বাদশ|ত্রয়োদশ|ত্রয়োদশ|চতুর্দশ|পঞ্চদশ|ষষ্ঠদশ|ষোড়শ|ষোড়শ|সপ্তদশ|অষ্টাদশ)\s*(?:খন্ড|খণ্ড|পর্ব)"
    r"|(?:[-–])(\d{1,2})(?=[-–]|$)"
    r"|(?:^|\s)(\d{1,2}|[১-৯][০-৯]?)$",
    re.I,
)


def parse_vol_number(tok: str) -> int | None:
    t = unicodedata.normalize("NFC", tok or "").strip().lower()
    if t in ORDINAL_MAP:
        return ORDINAL_MAP[t]
    t = re.sub(r"তম$", "", t)
    t_ascii = t.translate(BN_DIGITS)
    if t_ascii.isdigit():
        n = int(t_ascii)
        if 1 <= n <= 99:
            return n
    return None


def extract_volumes(stem: str) -> set[int]:
    vols: set[int] = set()
    clean = re.sub(r"\s*\((?:\d+|v\d+)\)\s*$", "", stem, flags=re.I)
    clean = re.sub(r"\s*\[(?:19|20)\d{2}\]\s*", " ", clean)
    for m in VOL_TOKEN_RE.finditer(clean):
        for g in m.groups():
            if g:
                val = parse_vol_number(g)
                if val is not None:
                    vols.add(val)
    return vols


def clean_proposed_filename(name: str) -> str:
    """Fix benign spacing/empty-bracket artifacts from site-spam removal."""
    p = Path(name)
    stem = re.sub(r"\s*[\[(]\s*[\])]", "", p.stem)
    stem = re.sub(r"\s{2,}", " ", stem).strip(" -.")
    return f"{stem}{p.suffix}" if stem else name


def norm_cosmetic(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def uppercase_ratio(s: str) -> tuple[int, float]:
    letters = [ch for ch in s if "A" <= ch <= "Z" or "a" <= ch <= "z"]
    if not letters:
        return 0, 0.0
    upper = sum(1 for ch in letters if "A" <= ch <= "Z")
    return len(letters), upper / len(letters)


def is_all_caps_downgrade(old_stem: str, new_stem: str) -> bool:
    old_title = WELL_FORMED_SEP_RE.split(old_stem)[0]
    new_title = WELL_FORMED_SEP_RE.split(new_stem)[0]
    n_cnt, n_ratio = uppercase_ratio(new_title)
    o_cnt, o_ratio = uppercase_ratio(old_title)
    if n_cnt >= 6 and n_ratio >= 0.72 and (o_cnt == 0 or o_ratio <= 0.55):
        return True
    if re.search(r"\b[A-Z]{4,}\b", new_title) and not re.search(r"\b[A-Z]{4,}\b", old_title):
        return True
    return False


def has_unbalanced_brackets(s: str) -> bool:
    for op, cl in [("(", ")"), ("[", "]"), ("{", "}")]:
        if s.count(op) != s.count(cl):
            return True
    return False


def evaluate_candidate(
    folder: str,
    rec: dict[str, Any],
    occupied_in_parent: set[str],
    planned_targets_in_parent: set[str],
) -> tuple[bool, str, str, str]:
    """Return (keep, defect_or_reject_category, reason_detail, cleaned_new_name)."""
    old = rec.get("name") or ""
    raw_new = rec.get("proposed_filename") or ""
    conf = (rec.get("confidence") or "").upper()
    if conf != "HIGH" or not raw_new or raw_new == old:
        return False, "not_high_or_unchanged", "", raw_new

    new = clean_proposed_filename(raw_new)
    if new == old:
        return False, "not_high_or_unchanged", "", new

    old_ext = Path(old).suffix.lower()
    new_ext = Path(new).suffix.lower()
    if old_ext != new_ext:
        return False, "ext_mismatch", "", new

    old_stem = Path(old).stem
    new_stem = Path(new).stem
    if len(new_stem.strip()) < 4:
        return False, "too_short", "", new

    # Reject pure punctuation/whitespace/em-dash churn
    if norm_cosmetic(old_stem) == norm_cosmetic(new_stem):
        return False, "cosmetic_only", "", new

    # Reject Unicode/mojibake/OCR matra corruption or dirty punctuation in new name
    if MOJIBAKE_CHAR_RE.search(new_stem) or BN_LEADING_MATRA_RE.search(new_stem) or DIRTY_CHARS_RE.search(new_stem):
        return False, "dirty_new_chars", "", new
    if has_unbalanced_brackets(new_stem):
        return False, "unbalanced_brackets", "", new
    if re.search(r"\s+by\s+", new_stem, re.I):
        return False, "leftover_by_connector", "", new
    if old_stem.lower() != new_stem.lower() and new_stem.islower() and not HAS_BN_RE.search(new_stem):
        return False, "lowercase_downgrade", "", new

    # Reject Bangla -> Latin downgrade
    if HAS_BN_RE.search(old_stem) and not HAS_BN_RE.search(new_stem):
        return False, "bn_to_latin_downgrade", "", new

    # Reject mixed-script CAPS downgrade or title replacement on already clean Bengali titles
    if HAS_BN_RE.search(old_stem) and not MOJIBAKE_CHAR_RE.search(old_stem):
        o_title = WELL_FORMED_SEP_RE.split(old_stem)[0]
        n_title = WELL_FORMED_SEP_RE.split(new_stem)[0]
        if HAS_BN_RE.search(o_title) and not HAS_BN_RE.search(n_title):
            return False, "bn_title_lost", "", new
        old_bn_words = [w for w in re.findall(r"[\u0980-\u09ff]{3,}", unicodedata.normalize("NFC", o_title))]
        new_bn_text = unicodedata.normalize("NFC", new_stem)
        if len(old_bn_words) >= 2:
            kept = sum(1 for w in old_bn_words if w[:3] in new_bn_text)
            if kept == 0 or (len(old_bn_words) >= 4 and kept / len(old_bn_words) <= 0.5):
                return False, "unrelated_bn_title_replacement", "", new

    if is_all_caps_downgrade(old_stem, new_stem):
        return False, "all_caps_downgrade", "", new

    # Reject scanner/uploader handle or reversed "Last, First" author
    new_parts = WELL_FORMED_SEP_RE.split(new_stem)
    if len(new_parts) >= 2:
        new_author = new_parts[-1].strip()
        if new_author.lower() in BAD_AUTHOR_HANDLES:
            return False, "bad_uploader_handle", new_author, new
        if re.fullmatch(r"[A-Za-z]{2,8}", new_author) and (new_author.isupper() or new_author.islower()):
            return False, "short_ambiguous_handle", new_author, new
        if REVERSED_AUTHOR_RE.search(new_author) and not REVERSED_AUTHOR_RE.search(old_stem):
            return False, "reversed_author_format", new_author, new

    # Reject Education year overwrites or NCTB author stripping
    if "Education & Textbooks" in folder:
        old_years = set(YEAR_RE.findall(old_stem)) | set(BN_YEAR_RE.findall(old_stem))
        new_years = set(YEAR_RE.findall(new_stem)) | set(BN_YEAR_RE.findall(new_stem))
        if old_years != new_years:
            return False, "education_year_changed", "", new
        if ("এনসিটিবি" in old_stem or "nctb" in old_stem.lower()) and (
            "এনসিটিবি" not in new_stem and "nctb" not in new_stem.lower()
        ):
            return False, "nctb_author_stripped", "", new

    # Reject [number] Series - Subtitle overwrites
    m_series = SERIES_PREFIX_RE.match(old_stem)
    if m_series:
        old_sub = m_series.group(2)
        m_new = SERIES_PREFIX_RE.match(new_stem)
        if not m_new:
            return False, "series_subtitle_lost", "", new
        old_sub_clean = SITE_SPAM_RE.sub("", old_sub).strip().lower()
        new_sub_lower = m_new.group(2).strip().lower()
        old_sub_words = {w for w in re.findall(r"[a-z]{3,}", old_sub_clean)}
        if old_sub_words and not any(w in new_sub_lower for w in old_sub_words):
            return False, "series_subtitle_overwritten", "", new

    # Reject volume/part number mismatches or dropped part markers
    old_vols = extract_volumes(old_stem)
    new_vols = extract_volumes(new_stem)
    if old_vols and new_vols and old_vols != new_vols:
        return False, "volume_number_mismatch", f"{old_vols} != {new_vols}", new
    if old_vols and not new_vols:
        return False, "volume_number_dropped", f"{old_vols}", new

    # Determine real defect in old filename
    defect = ""
    if MOJIBAKE_CHAR_RE.search(old_stem) or RANDOM_ID_RE.match(old_stem.strip()):
        defect = "mojibake_or_garbled"
    elif SITE_SPAM_RE.search(old_stem):
        if len(new_stem) < max(6, len(SITE_SPAM_RE.sub("", old_stem).strip()) - 15) and not HAS_BN_RE.search(new_stem):
            return False, "excessive_truncation", "", new
        defect = "site_spam"
    elif not HAS_BN_RE.search(old_stem) and HAS_BN_RE.search(new_stem):
        defect = "banglish_to_bangla"
    elif WELL_FORMED_SEP_RE.search(old_stem):
        return False, "already_well_formed", "", new
    elif len(new_parts) >= 2 and not VOLUME_ONLY_SEGMENT_RE.match(new_parts[-1].strip()):
        # Ensure clean author was genuinely added (not merely moving part/volume behind '-')
        if not HAS_BN_RE.search(old_stem) and HAS_LATIN_WORD_RE.search(old_stem):
            old_tokens = {
                t.lower()
                for t in re.findall(r"[A-Za-z]{4,}", old_stem)
                if t.lower() not in {"book", "part", "bangla", "pdf", "vol"}
            }
            new_lower = new_stem.lower()
            if old_tokens and not any(t in new_lower for t in old_tokens) and len(old_tokens) >= 2:
                return False, "unrelated_latin_title_replacement", "", new
        defect = "missing_author_or_formatting"
    else:
        return False, "no_clear_defect", "", new

    # Same-folder collision check
    target_key = new.lower()
    if target_key in occupied_in_parent or target_key in planned_targets_in_parent:
        return False, "same_folder_collision", "", new

    return True, defect, rec.get("reason", ""), new


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    occupied_by_parent: dict[str, set[str]] = collections.defaultdict(set)
    candidates_by_folder: list[tuple[str, dict[str, Any]]] = []

    for rel in REPORT_FILES:
        p = repo / rel
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        folder = data.get("target_folder") or p.stem
        for r in data.get("results", []):
            pid = r.get("parentId") or ""
            nm = (r.get("name") or "").lower()
            if pid and nm:
                occupied_by_parent[pid].add(nm)
            if (r.get("confidence") or "").upper() == "HIGH" and r.get("proposed_filename"):
                candidates_by_folder.append((folder, r))

    planned_targets: dict[str, set[str]] = collections.defaultdict(set)
    accepted: list[dict[str, Any]] = []
    rejected_counts = collections.Counter()
    accepted_by_folder = collections.Counter()
    accepted_by_defect = collections.Counter()

    for folder, rec in candidates_by_folder:
        pid = rec.get("parentId") or ""
        old_lower = (rec.get("name") or "").lower()
        other_occupied = occupied_by_parent[pid] - {old_lower}
        keep, tag, detail, clean_new = evaluate_candidate(
            folder, rec, other_occupied, planned_targets[pid]
        )
        if keep:
            planned_targets[pid].add(clean_new.lower())
            accepted.append(
                {
                    "id": rec.get("id"),
                    "parentId": pid,
                    "top_folder": folder,
                    "folder": rec.get("folder") or folder,
                    "old_name": rec.get("name"),
                    "new_name": clean_new,
                    "defect_type": tag,
                    "reason": detail,
                    "category": rec.get("category") or "",
                    "drive_url": f"https://drive.google.com/file/d/{rec.get('id')}/view",
                }
            )
            accepted_by_folder[folder] += 1
            accepted_by_defect[tag] += 1
        else:
            rejected_counts[tag] += 1

    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    plan_payload = {
        "generated_at": generated_at,
        "total_raw_high": len(candidates_by_folder),
        "total_safe_accepted": len(accepted),
        "total_rejected": sum(rejected_counts.values()),
        "accepted_by_folder": dict(accepted_by_folder),
        "accepted_by_defect": dict(accepted_by_defect),
        "rejected_breakdown": dict(rejected_counts.most_common()),
        "renames": accepted,
    }

    json_out = repo / "reports/renamer/safe_stage_d_plan.json"
    md_out = repo / "reports/renamer/SAFE_STAGE_D_PREVIEW.md"
    json_out.write_text(
        json.dumps(plan_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Safe Stage D Rename Preview (Strictly Filtered — Dry Run)",
        "",
        f"- **Generated (UTC):** `{generated_at}`",
        f"- **Raw Stage C HIGH Candidates Evaluated:** `{len(candidates_by_folder)}`",
        f"- **Strictly Approved Safe Renames:** `{len(accepted)}`",
        f"- **Rejected / Skipped:** `{sum(rejected_counts.values())}`",
        "",
        "## Breakdown by Folder",
        "",
        "| Folder | Safe Renames |",
        "|---|---:|",
    ]
    for fld, cnt in sorted(accepted_by_folder.items(), key=lambda x: -x[1]):
        lines.append(f"| {fld} | {cnt} |")

    lines.extend(
        [
            "",
            "## Breakdown by Defect Type",
            "",
            "| Defect Fixed | Count |",
            "|---|---:|",
        ]
    )
    for dtag, cnt in sorted(accepted_by_defect.items(), key=lambda x: -x[1]):
        lines.append(f"| `{dtag}` | {cnt} |")

    lines.extend(
        [
            "",
            "## Rejected Raw Proposals Summary",
            "",
            "| Reject Reason | Count |",
            "|---|---:|",
        ]
    )
    for rtag, cnt in rejected_counts.most_common():
        lines.append(f"| `{rtag}` | {cnt} |")

    lines.extend(
        [
            "",
            f"## Full List of {len(accepted)} Safe Stage D Renames",
            "",
            "| # | Defect | Folder | Current Filename | Proposed Safe Filename | File |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for idx, item in enumerate(accepted, start=1):
        old_esc = item["old_name"].replace("|", "\\|")
        new_esc = item["new_name"].replace("|", "\\|")
        fld_esc = item["folder"].replace("|", "\\|")
        lines.append(
            f"| {idx} | `{item['defect_type']}` | `{fld_esc}` | {old_esc} | {new_esc} | [Open]({item['drive_url']}) |"
        )
    lines.append("")
    md_out.write_text("\n".join(lines), encoding="utf-8")

    print(
        f"Raw HIGH={len(candidates_by_folder)} | Safe Accepted={len(accepted)} | Rejected={sum(rejected_counts.values())}"
    )
    print("By Folder:", dict(accepted_by_folder))
    print("By Defect:", dict(accepted_by_defect))
    print("Rejected Top:", rejected_counts.most_common(16))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
