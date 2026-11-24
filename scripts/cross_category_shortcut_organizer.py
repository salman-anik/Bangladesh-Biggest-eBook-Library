#!/usr/bin/env python3
"""
Stage 4: Google Drive Cross-Category Book Collection & Shortcut Organization.

Strictly executes non-destructive Drive organization under root 1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq:
- Keeps every original file in its single canonical primary folder.
- Creates native Google Drive shortcuts (`application/vnd.google-apps.shortcut`) across genuinely
  related categories (Islamic sub-subjects <-> Series <-> Scholars; Authors <-> Genres <-> Series;
  Education Classes/Madrasa <-> Subject/Reference folders) without duplicating any files or creating
  duplicate shortcuts in any destination folder.
- Preserves complete multi-volume series intact.
- Leaves uncertain classifications in place and lists them for manual review.
- Verifies every created shortcut points to the exact original targetId and that originals stay intact.
- Logs all shortcut creations into Library Management/Reports/rename_changelog.{json,csv,md}.
- Produces the 7-part Final Report in reports/cross_category_shortcuts_report.{json,md}.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import drive_utils as du  # noqa: E402

# Known multi-volume series / collection signatures (series_label, optional_existing_series_folder_path, keywords)
SERIES_SIGNATURES: list[tuple[str, str, list[str]]] = [
    ("তাফসীর ইবনে কাসীর", "Series & Collections/Special Collections/তাফসীর ইবনে কাসীর", ["তাফসীর ইবনে কাসীর", "তাফসীরে ইবনে কাসীর", "তাফসীরে ইবনে কাসির", "ibn kathir", "tafsir ibn k"]),
    ("ফী যিলালিল কুরআন", "Series & Collections/Special Collections/ফী যিলালিল কুরআন", ["ফী যিলালিল", "ফি যিলালিল", "ফি জিলালিল", "zilalil quran"]),
    ("তাফসীরে মারেফুল কোরআন", "", ["মারেফুল কোরআন", "মাআরেফুল কুরআন", "মা'আরেফুল কুরআন", "মাআরিফুল কুরআন", "maariful quran"]),
    ("তাফহীমুল কুরআন", "", ["তাফহীমুল কুরআন", "তাফহীমুল কোরআন", "tafhimul quran"]),
    ("আল-বিদায়া ওয়ান নিহায়া", "Series & Collections/Special Collections/আল-বিদায়া ওয়ান নিহায়া", ["আল বিদায়া", "আল-বিদায়া", "বিদায়া ওয়ান নিহায়া", "bidaya wan nihaya"]),
    ("সহীহ বুখারী", "", ["সহীহ বুখারী", "সহিহ বুখারি", "বোখারী শরীফ", "sahih al-bukhari", "sahih bukhari"]),
    ("সহীহ মুসলিম", "", ["সহীহ মুসলিম", "সহিহ মুসলিম", "মুসলিম শরীফ", "sahih muslim"]),
    ("সুনানে তিরমিযী", "", ["তিরমিযী", "তিরমিযি", "জামে তিরমিযী", "tirmidhi"]),
    ("হিমু সিরিজ", "Series & Collections/Book Series/হিমু সিরিজ", ["হিমু", "himu", "ময়ূরাক্ষী", "moyurakkhi", "দরজার ওপাশে", "আঙুল কাটা জগলু", "মজার ভূত"]),
    ("মিসির আলি সিরিজ", "Series & Collections/Book Series/মিসির আলি সিরিজ", ["মিসির আলি", "misir ali", "দেবী", "নিশীথিনী", "বৃহন্নলা", "তন্দ্রাবিলাস", "কহেন কবি কালিদাস", "যখন নামিবে আঁধার"]),
    ("মাসুদ রানা সিরিজ", "Series & Collections/Book Series/মাসুদ রানা সিরিজ", ["মাসুদ রানা", "masud rana"]),
    ("ফেলুদা সিরিজ", "Series & Collections/Book Series/ফেলুদা সিরিজ", ["ফেলুদা", "feluda", "সোনার কেল্লা", "জয় বাবা ফেলুনাথ"]),
    ("প্রফেসর শঙ্কু সিরিজ", "Series & Collections/Book Series/প্রফেসর শঙ্কু সিরিজ", ["শঙ্কু", "shonku"]),
    ("কাকাবাবু সিরিজ", "", ["কাকাবাবু", "kakababu"]),
    ("তিন গোয়েন্দা সিরিজ", "", ["তিন গোয়েন্দা", "tin goyenda"]),
    ("ব্যোমকেশ বক্সী সিরিজ", "Series & Collections/Book Series/ব্যোমকেশ বক্সী সিরিজ", ["ব্যোমকেশ", "byomkesh"]),
    ("ঘনাদা সিরিজ", "Series & Collections/Book Series/ঘনাদা সিরিজ", ["ঘনাদা", "ghanada"]),
    ("টেনিদা সিরিজ", "Series & Collections/Book Series/টেনিদা সিরিজ", ["টেনিদা", "tenida"]),
    ("শার্লক হোমস সিরিজ", "Series & Collections/Book Series/শার্লক হোমস সিরিজ", ["শার্লক হোমস", "sherlock holmes"]),
    ("হ্যারি পটার সিরিজ", "Series & Collections/Book Series/হ্যারি পটার সিরিজ", ["হ্যারি পটার", "harry potter"]),
    ("টিনটিন কমিক্স", "Series & Collections/Book Series/টিনটিন কমিক্স", ["টিনটিন", "tintin"]),
]

# Complete intact folder -> secondary destination folder shortcut links (preserves full series/collection as 1 folder shortcut!)
FOLDER_SHORTCUT_LINKS: list[tuple[str, str, str]] = [
    (
        "Series & Collections/Special Collections/তাফসীর ইবনে কাসীর",
        "Religion Books/Islam/Quran & Tafsir (কুরআন ও তাফসির)",
        "তাফসীর ইবনে কাসীর (সম্পূর্ণ সিরিজ)",
    ),
    (
        "Series & Collections/Special Collections/ফী যিলালিল কুরআন",
        "Religion Books/Islam/Quran & Tafsir (কুরআন ও তাফসির)",
        "ফী যিলালিল কুরআন (সম্পূর্ণ সিরিজ)",
    ),
    (
        "Series & Collections/Special Collections/আল-বিদায়া ওয়ান নিহায়া",
        "Religion Books/Islam/Islamic History (ইসলামিক ইতিহাস)",
        "আল-বিদায়া ওয়ান নিহায়া (সম্পূর্ণ সিরিজ)",
    ),
    (
        "Education & Textbooks/Madrasa/Qawmi Madrasa/Takmil (Dawra-e-Hadith)/Sahih Al-Bukhari & Shuruh",
        "Religion Books/Islam/Hadith & Hadith Sciences (হাদিস)",
        "Sahih Al-Bukhari & Shuruh (Dawra-e-Hadith Series)",
    ),
    (
        "Education & Textbooks/Madrasa/Qawmi Madrasa/Takmil (Dawra-e-Hadith)/Sahih Muslim & Shuruh",
        "Religion Books/Islam/Hadith & Hadith Sciences (হাদিস)",
        "Sahih Muslim & Shuruh (Dawra-e-Hadith Series)",
    ),
    (
        "Education & Textbooks/Madrasa/Qawmi Madrasa/Takmil (Dawra-e-Hadith)/Jami At-Tirmidhi & Shuruh",
        "Religion Books/Islam/Hadith & Hadith Sciences (হাদিস)",
        "Jami At-Tirmidhi & Shuruh (Dawra-e-Hadith Series)",
    ),
    (
        "Education & Textbooks/Madrasa/Qawmi Madrasa/Common & Reference Books/Tafseer & Al-Quran",
        "Religion Books/Islam/Quran & Tafsir (কুরআন ও তাফসির)",
        "Qawmi Tafseer & Al-Quran Collection",
    ),
    (
        "Education & Textbooks/Madrasa/Qawmi Madrasa/Common & Reference Books/Fiqh & Madhhab",
        "Religion Books/Islam/Fiqh & Islamic Jurisprudence (ফিকহ)",
        "Qawmi Fiqh & Madhhab Collection",
    ),
    (
        "Education & Textbooks/Madrasa/Qawmi Madrasa/Common & Reference Books/Aqeedah & Beliefs",
        "Religion Books/Islam/Aqidah & Theology (আকিদা)",
        "Qawmi Aqeedah & Beliefs Collection",
    ),
    (
        "Education & Textbooks/Madrasa/Qawmi Madrasa/Common & Reference Books/Seerah, Akabir Biographies & Islamic History",
        "Religion Books/Islam/Seerah & Biography (সীরাত)",
        "Qawmi Seerah & Islamic History Collection",
    ),
    (
        "Series & Collections/Book Series/হিমু সিরিজ",
        "Authors & Scholars/Bangladeshi Authors/হুমায়ূন আহমেদ",
        "হিমু সিরিজ (সম্পূর্ণ সংগ্রহ)",
    ),
    (
        "Series & Collections/Book Series/মিসির আলি সিরিজ",
        "Authors & Scholars/Bangladeshi Authors/হুমায়ূন আহমেদ",
        "মিসির আলি সিরিজ (সম্পূর্ণ সংগ্রহ)",
    ),
    (
        "Series & Collections/Book Series/ফেলুদা সিরিজ",
        "Authors & Scholars/Bangladeshi Authors/সত্যজিৎ রায়",
        "ফেলুদা সিরিজ (সম্পূর্ণ সংগ্রহ)",
    ),
    (
        "Series & Collections/Book Series/প্রফেসর শঙ্কু সিরিজ",
        "Authors & Scholars/Bangladeshi Authors/সত্যজিৎ রায়",
        "প্রফেসর শঙ্কু সিরিজ (সম্পূর্ণ সংগ্রহ)",
    ),
    (
        "Series & Collections/Book Series/মাসুদ রানা সিরিজ",
        "Bangla Books/Thriller, Mystery & Detective (থ্রিলার ও গোয়েন্দা)",
        "মাসুদ রানা সম্পূর্ণ সিরিজ (Series Collection)",
    ),
    (
        "Series & Collections/Book Series/শার্লক হোমস সিরিজ",
        "Bangla Books/Thriller, Mystery & Detective (থ্রিলার ও গোয়েন্দা)",
        "শার্লক হোমস সিরিজ (সম্পূর্ণ সংগ্রহ)",
    ),
    (
        "Series & Collections/Book Series/ব্যোমকেশ বক্সী সিরিজ",
        "Bangla Books/Thriller, Mystery & Detective (থ্রিলার ও গোয়েন্দা)",
        "ব্যোমকেশ বক্সী সিরিজ (সম্পূর্ণ সংগ্রহ)",
    ),
]

ISLAMIC_SUBJECT_RULES: list[tuple[str, list[str]]] = [
    (
        "Religion Books/Islam/Quran & Tafsir (কুরআন ও তাফসির)",
        ["তাফসীর", "তাফসির", "tafsir", "tafseer", "কুরআন", "কোরআন", "quran", "qur'an", "শানে নুযূল", "তাজবীদ", "উলূমুল কুরআন"],
    ),
    (
        "Religion Books/Islam/Hadith & Hadith Sciences (হাদিস)",
        ["হাদীস", "হাদিস", "hadith", "বুখারী", "বুখারি", "মুসলিম শরীফ", "তিরমিযী", "তিরমিযি", "আবু দাউদ", "নাসাঈ", "ইবনে মাজাহ", "রিয়াদুস সালেহীন", "মিশকাত", "মুয়াত্তা"],
    ),
    (
        "Religion Books/Islam/Fiqh & Islamic Jurisprudence (ফিকহ)",
        ["ফিকহ", "fiqh", "ফাতাওয়া", "ফতোয়া", "masail", "মাসআলা", "মাসায়িল", "নামায", "নামাজ", "সালাত", "যাকাত", "হজ্জ", "রোযা", "রোজা", "নিকাহ", "বিবাহ", "তালাক", "উত্তরাধিকার", "ফারায়েজ"],
    ),
    (
        "Religion Books/Islam/Seerah & Biography (সীরাত)",
        ["সীরাত", "সীরাতে", "seerah", "sirah", "নবীজী", "নবীজি", "রাসূলুল্লাহ", "মহানবী", "রাহীকুল মাখতূম", "আসহাবে", "সাহাবী", "জীবনী"],
    ),
    (
        "Religion Books/Islam/Aqidah & Theology (আকিদা)",
        ["আকীদা", "আকিদা", "aqeedah", "aqidah", "তাওহীদ", "তৌহিদ", "তাকদীর", "শিরক", "বিদআত", "ঈমান"],
    ),
    (
        "Religion Books/Islam/Islamic History (ইসলামিক ইতিহাস)",
        ["ইসলামের ইতিহাস", "ইসলামিক ইতিহাস", "খিলাফত", "আন্দালুস", "ক্রুসেড", "উসমানীয়", "সালতানাত"],
    ),
]

BANGLA_GENRE_SHORTCUT_RULES: list[tuple[str, list[str]]] = [
    ("Bangla Books/Thriller, Mystery & Detective (থ্রিলার ও গোয়েন্দা)", ["থ্রিলার", "গোয়েন্দা", "রহস্য", "ফেলুদা", "কাকাবাবু", "মাসুদ রানা", "তিন গোয়েন্দা", "কিরীটী", "ব্যোমকেশ", "শবর", "মিসির আলি"]),
    ("Bangla Books/Poetry (কবিতা)", ["কবিতা", "কাব্য", "সনেট", "গীতাঞ্জলি", "সঞ্চয়িতা", "সঞ্চিতা", "অগ্নিবীণা", "বলাকা"]),
    ("Bangla Books/Drama & Plays (নাটক)", ["নাটক", "প্রহসন", "নাট্যসমগ্র", "রক্তকরবী", "ডাকঘর"]),
    ("Bangla Books/Science & Technology (বিজ্ঞান ও প্রযুক্তি)", ["সায়েন্স ফিকশন", "কল্পবিজ্ঞান", "বৈজ্ঞানিক কল্পকাহিনী", "কোয়ান্টাম", "বিজ্ঞান"]),
    ("Bangla Books/History & Culture (ইতিহাস)", ["মুক্তিযুদ্ধ", "১৯৭১", "জোছনা ও জননী", "শ্যামল ছায়া", "আগুনের পরশমণি", "একাত্তর", "ইতিহাস"]),
    ("Bangla Books/Stories & Short Stories (গল্প ও ছোটগল্প)", ["গল্পগুচ্ছ", "ছোটগল্প", "শ্রেষ্ঠ গল্প", "গল্পসমগ্র"]),
    ("Bangla Books/Children & Teen Literature (শিশু-কিশোর সাহিত্য)", ["কিশোর", "শিশু", "হাবলু", "দীপু নাম্বার", "আমার বন্ধু রাশেদ", "টিনটিন"]),
]


def has_keyword(text: str, kw: str) -> bool:
    k = kw.lower().strip()
    t = text.lower()
    if not k or k not in t:
        return False
    # Enforce token boundaries on short/root words so substrings like 'হিমু' in 'তাফহীমুল' never match
    if len(k) <= 6 and " " not in k:
        return bool(re.search(rf"(?:^|[\s\-—–_.,()\[\]/|]){re.escape(k)}(?:$|[\s\-—–_.,()\[\]/|]|ের|ে|র)", t))
    return True


def norm_title_key(name: str) -> str:
    stem = os.path.splitext(name or "")[0].lower()
    stem = re.sub(r"\s*\[[^\]]*\]\s*", " ", stem)
    stem = re.sub(r"\s*[-—–]\s*.*$", "", stem)
    stem = re.sub(r"[^\w\u0980-\u09FF]+", " ", stem)
    return re.sub(r"\s+", " ", stem).strip()


def extract_explicit_author_from_name(filename: str) -> str:
    stem = os.path.splitext(filename or "")[0].strip()
    if " - " in stem:
        parts = [p.strip() for p in stem.rsplit(" - ", 1)]
        if len(parts) == 2 and len(parts[1]) >= 4 and not re.search(r"খন্ড|খণ্ড|পর্ব|\b(vol|part|book|series)\b", parts[1], re.I):
            return parts[1]
    return ""


def build_author_lookup(folders_by_id: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Map full author folder names -> author folder metadata under Authors & Scholars."""
    by_token_name: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for fid, info in folders_by_id.items():
        parts = [p for p in info["path"].split("/") if p]
        if not parts or parts[0] != "Authors & Scholars":
            continue
        author_name = ""
        if len(parts) == 3 and parts[1] in ("Bangladeshi Authors", "International Authors"):
            author_name = parts[2]
        elif len(parts) == 4 and parts[1] == "Islamic Scholars":
            author_name = parts[3]
        if not author_name or len(author_name) < 5:
            continue
        by_token_name[author_name.lower()].append(info)
    return dict(by_token_name)


def build_cross_category_plan(
    files: list[dict[str, Any]],
    shortcuts: list[dict[str, Any]],
    folders_by_id: dict[str, dict[str, Any]],
    folders_by_path: dict[str, str],
) -> dict[str, Any]:
    """
    Compute verified non-destructive shortcut plan + series inventory + uncertain manual-review items.
    """
    author_lookup = build_author_lookup(folders_by_id)

    # Track what already lives inside each folder (id, md5, normalized stem, existing shortcut targets)
    folder_file_ids: dict[str, set[str]] = collections.defaultdict(set)
    folder_md5s: dict[str, set[str]] = collections.defaultdict(set)
    folder_stems: dict[str, set[str]] = collections.defaultdict(set)
    folder_shortcut_targets: dict[str, set[str]] = collections.defaultdict(set)
    folder_names: dict[str, set[str]] = collections.defaultdict(set)

    # Also build recursive subtree sets for Authors so we don't place redundant author-root shortcuts
    # when the author already holds that exact book inside one of their subfolders!
    author_subtree_md5s: dict[str, set[str]] = collections.defaultdict(set)
    author_subtree_stems: dict[str, set[str]] = collections.defaultdict(set)

    for f in files:
        pid = f["parent_id"]
        folder_file_ids[pid].add(f["id"])
        folder_names[pid].add(f["name"].lower())
        if f.get("md5"):
            folder_md5s[pid].add(f["md5"])
        st = norm_title_key(f["name"])
        if st:
            folder_stems[pid].add(st)

        # Propagate into canonical author ancestor if under Authors & Scholars
        parts = [p for p in f["folder"].split("/") if p]
        if len(parts) >= 3 and parts[0] == "Authors & Scholars":
            ap = "/".join(parts[:4] if parts[1] == "Islamic Scholars" and len(parts) >= 4 else parts[:3])
            aid = folders_by_path.get(ap)
            if aid:
                if f.get("md5"):
                    author_subtree_md5s[aid].add(f["md5"])
                if st:
                    author_subtree_stems[aid].add(st)

    for sc in shortcuts:
        pid = sc["parent_id"]
        if sc.get("target_id"):
            folder_shortcut_targets[pid].add(sc["target_id"])
        folder_names[pid].add(sc["name"].lower())

    planned_shortcuts: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()  # (target_id, dest_parent_id)
    series_detected: dict[str, dict[str, Any]] = collections.defaultdict(lambda: {"count": 0, "primary_folders": set(), "sample_files": []})
    manual_classification: list[dict[str, Any]] = []

    def _queue_shortcut(
        target_id: str,
        target_name: str,
        target_mime: str,
        primary_folder: str,
        dest_path: str,
        reason: str,
        md5: str = "",
        is_author_dest: bool = False,
        shortcut_display_name: str | None = None,
    ) -> bool:
        dest_id = folders_by_path.get(dest_path)
        if not dest_id:
            return False
        if (target_id, dest_id) in seen_pairs:
            return False
        if target_id in folder_file_ids[dest_id] or target_id in folder_shortcut_targets[dest_id]:
            return False
        if md5 and (md5 in folder_md5s[dest_id] or (is_author_dest and md5 in author_subtree_md5s[dest_id])):
            return False
        st = norm_title_key(target_name)
        if st and len(st) >= 5 and (st in folder_stems[dest_id] or (is_author_dest and st in author_subtree_stems[dest_id])):
            return False
        sc_name = shortcut_display_name or target_name
        if sc_name.lower() in folder_names[dest_id]:
            return False

        seen_pairs.add((target_id, dest_id))
        folder_names[dest_id].add(sc_name.lower())
        folder_shortcut_targets[dest_id].add(target_id)
        if st:
            folder_stems[dest_id].add(st)
        if md5:
            folder_md5s[dest_id].add(md5)

        planned_shortcuts.append(
            {
                "target_id": target_id,
                "target_mime": target_mime,
                "target_name": target_name,
                "shortcut_name": sc_name,
                "primary_folder": primary_folder,
                "dest_parent_id": dest_id,
                "dest_folder": dest_path,
                "reason": reason,
            }
        )
        return True

    # 1) Whole intact multi-volume series / Qawmi subject folders -> Folder Shortcuts
    for src_path, dest_path, sc_label in FOLDER_SHORTCUT_LINKS:
        src_id = folders_by_path.get(src_path)
        if src_id:
            _queue_shortcut(
                target_id=src_id,
                target_name=folders_by_id[src_id]["name"],
                target_mime=du.FOLDER_MIME,
                primary_folder=src_path,
                dest_path=dest_path,
                reason="complete_series_collection_link",
                shortcut_display_name=sc_label,
            )

    # Track series counts from folder tree + filenames
    for fp, fid in folders_by_path.items():
        if fp.startswith("Series & Collections/"):
            leaf = fp.split("/")[-1]
            series_detected[leaf]["primary_folders"].add(fp)

    # 2) Individual Book Cross-Category Discovery
    for f in files:
        if f["ext"] not in du.BOOK_EXTS:
            continue
        fid = f["id"]
        fname = f["name"]
        fpath = f["folder"]
        low = fname.lower()
        top = fpath.split("/")[0] if fpath else ""
        parts = [p for p in fpath.split("/") if p]
        md5 = f.get("md5", "")

        # Series detection statistics
        for s_label, s_folder, s_kws in SERIES_SIGNATURES:
            if any(has_keyword(fname, kw) for kw in s_kws) or (s_folder and s_folder in fpath):
                series_detected[s_label]["count"] += 1
                series_detected[s_label]["primary_folders"].add(fpath)
                if len(series_detected[s_label]["sample_files"]) < 5:
                    series_detected[s_label]["sample_files"].append(fname)
                # If book is a series member sitting outside that series folder, link it INTO the series folder!
                if s_folder and s_folder in folders_by_path and not fpath.startswith("Series & Collections/"):
                    _queue_shortcut(fid, fname, f.get("mimeType", "application/pdf"), fpath, s_folder, f"series_member:{s_label}", md5=md5)

        # Skip linking individual files inside huge Madrasa folders unless matched by explicit full author/series above
        if "Qawmi Madrasa" in fpath:
            continue

        # Cross-link A: Authors & Scholars -> Subject / Genre folders
        if top == "Authors & Scholars" and len(parts) >= 3:
            if parts[1] == "Islamic Scholars":
                matched_subj = None
                for dest_subj, kws in ISLAMIC_SUBJECT_RULES:
                    if any(has_keyword(fname, kw) for kw in kws):
                        matched_subj = dest_subj
                        break
                if matched_subj:
                    _queue_shortcut(fid, fname, f.get("mimeType", "application/pdf"), fpath, matched_subj, "islamic_scholar_to_subject", md5=md5)
                else:
                    manual_classification.append({"id": fid, "name": fname, "folder": fpath, "reason": "uncertain_islamic_subject"})
            elif parts[1] in ("Bangladeshi Authors", "International Authors"):
                for dest_genre, kws in BANGLA_GENRE_SHORTCUT_RULES:
                    if any(has_keyword(fname, kw) or has_keyword(fpath, kw) for kw in kws):
                        _queue_shortcut(fid, fname, f.get("mimeType", "application/pdf"), fpath, dest_genre, "author_work_to_genre", md5=md5)
                        break

        # Cross-link B: Religion / Bangla Books / Series -> Dedicated Author folder (explicit full author match)
        if top in ("Bangla Books", "Religion Books", "Series & Collections", "Reference & Research", "Education & Textbooks"):
            explicit_auth = extract_explicit_author_from_name(fname).lower()
            for auth_low, ainfos in author_lookup.items():
                if len(auth_low) < 6:
                    continue
                if auth_low == explicit_auth or f" {auth_low}" in f" {low}" or auth_low in explicit_auth:
                    target_author_info = ainfos[0]
                    dest_p = target_author_info["path"]
                    # If target author already has a matching subfolder (e.g. হিমু / গল্প / কবিতা), prefer the top author folder or sub!
                    _queue_shortcut(
                        fid, fname, f.get("mimeType", "application/pdf"), fpath, dest_p,
                        f"book_to_author:{target_author_info['name']}", md5=md5, is_author_dest=True,
                    )
                    break

        # Cross-link C: Education Classes / NCTB shared across Computer Science / Reference
        if top == "English Books" and "Computer Science" in fpath:
            if any(k in low for k in ("ict", "programming", "python", "data structure", "algorithm", "database", "operating system")):
                for target_ref in ("Reference & Research/Academic & Research", "Education & Textbooks/General Education/Higher Secondary Education/Science"):
                    if target_ref in folders_by_path:
                        _queue_shortcut(fid, fname, f.get("mimeType", "application/pdf"), fpath, target_ref, "cs_textbook_to_education", md5=md5)
                        break

        # Report genuinely uncertain items sitting in Review & Unclassified
        if top == "Review & Unclassified" and "Pending Review" in fpath:
            manual_classification.append({"id": fid, "name": fname, "folder": fpath, "reason": "pending_review_unclassified"})

    return {
        "original_files_inspected": len(files),
        "series_detected": {
            k: {
                "count": v["count"],
                "primary_folders": sorted(v["primary_folders"])[:10],
                "sample_files": v["sample_files"],
            }
            for k, v in sorted(series_detected.items())
            if v["count"] > 0 or v["primary_folders"]
        },
        "planned_shortcuts": planned_shortcuts,
        "manual_classification": manual_classification,
    }


def _create_single_shortcut(plan_item: dict[str, Any]) -> dict[str, Any]:
    body = {
        "name": plan_item["shortcut_name"],
        "mimeType": du.SHORTCUT_MIME,
        "parents": [plan_item["dest_parent_id"]],
        "shortcutDetails": {"targetId": plan_item["target_id"]},
    }
    created = du.drive_request(
        "POST",
        "/files",
        params={"supportsAllDrives": "true", "fields": "id,name,mimeType,parents,shortcutDetails"},
        body=body,
    )
    # Verify newly created shortcut immediately resolves cleanly to the original targetId
    chk = du.drive_request(
        "GET",
        f"/files/{created['id']}",
        params={"supportsAllDrives": "true", "fields": "id,name,mimeType,parents,shortcutDetails,trashed"},
    )
    ok = (
        chk.get("mimeType") == du.SHORTCUT_MIME
        and (chk.get("shortcutDetails") or {}).get("targetId") == plan_item["target_id"]
        and plan_item["dest_parent_id"] in (chk.get("parents") or [])
        and not chk.get("trashed", False)
    )
    return {"created": created, "verified": ok, "plan": plan_item}


def run_shortcut_organizer(
    repo_dir: Path,
    dry_run: bool = False,
    local_catalog_only: bool = False,
    max_shortcuts: int = 0,
) -> dict[str, Any]:
    if local_catalog_only:
        cat = json.loads((repo_dir / "books.json").read_text(encoding="utf-8"))
        cats, subs, fmts = cat["cats"], cat["subs"], cat["fmts"]
        folders_by_id: dict[str, dict[str, Any]] = {}
        folders_by_path: dict[str, str] = {}
        for idx_c, c in enumerate(cats):
            folders_by_path[c] = f"CAT_{idx_c}"
            folders_by_id[f"CAT_{idx_c}"] = {"id": f"CAT_{idx_c}", "name": c, "path": c}
        files: list[dict[str, Any]] = []
        for idx_b, b in enumerate(cat["books"]):
            fid, title, _auth, ci, si, li, fi, sz, cov, ser = b
            c = cats[ci] if 0 <= ci < len(cats) else ""
            s = subs[si] if 0 <= si < len(subs) else ""
            fp = f"{c}/{s}".strip("/")
            parts = [p for p in fp.split("/") if p]
            for d in range(1, len(parts) + 1):
                sub_p = "/".join(parts[:d])
                if sub_p not in folders_by_path:
                    pid_fake = f"F_{len(folders_by_path)}"
                    folders_by_path[sub_p] = pid_fake
                    folders_by_id[pid_fake] = {"id": pid_fake, "name": parts[d - 1], "path": sub_p}
            ext = "." + (fmts[fi].lower() if 0 <= fi < len(fmts) else "pdf")
            files.append(
                {
                    "id": fid,
                    "name": f"{title}{ext}",
                    "ext": ext,
                    "mimeType": "application/pdf",
                    "size": sz,
                    "md5": "",
                    "parent_id": folders_by_path.get(fp, "ROOT"),
                    "folder": fp,
                }
            )
        shortcuts = []
    else:
        print(f"[Shortcuts] Walking full Drive root {du.ROOT_ID}...", flush=True)
        tree = du.walk_drive_tree(du.ROOT_ID, skip_top_folders=du.SKIP_TOP_FOLDERS)
        files = tree["files"]
        shortcuts = tree["shortcuts"]
        folders_by_id = tree["folders_by_id"]
        folders_by_path = tree["folders_by_path"]
        print(
            f"[Shortcuts] Inspected {len(files)} original files, {len(shortcuts)} existing shortcuts, {len(folders_by_id)} folders.",
            flush=True,
        )

    plan = build_cross_category_plan(files, shortcuts, folders_by_id, folders_by_path)
    planned = plan["planned_shortcuts"]
    if max_shortcuts > 0:
        planned = planned[:max_shortcuts]

    created_logs: list[dict[str, Any]] = []
    verified_count = 0
    errors: list[dict[str, Any]] = []

    if dry_run or local_catalog_only:
        created_logs = [
            {
                "id": f"DRY_SC_{i}",
                "action": "create_shortcut",
                "folder": p["dest_folder"],
                "old_parent_id": p["target_id"],
                "new_parent_id": p["dest_parent_id"],
                "old_name": p["primary_folder"],
                "new_name": p["shortcut_name"],
                "category": p["reason"],
                "primary_folder": p["primary_folder"],
                "target_name": p["target_name"],
                "target_id": p["target_id"],
            }
            for i, p in enumerate(planned, 1)
        ]
    else:
        print(f"[Shortcuts] Creating & verifying {len(planned)} native Drive shortcuts...", flush=True)
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futs = [pool.submit(_create_single_shortcut, p) for p in planned]
            for idx, fut in enumerate(concurrent.futures.as_completed(futs), 1):
                try:
                    res = fut.result()
                    p = res["plan"]
                    sc = res["created"]
                    if res["verified"]:
                        verified_count += 1
                    created_logs.append(
                        {
                            "id": sc["id"],
                            "action": "create_shortcut",
                            "folder": p["dest_folder"],
                            "old_parent_id": p["target_id"],
                            "new_parent_id": p["dest_parent_id"],
                            "old_name": p["primary_folder"],
                            "new_name": p["shortcut_name"],
                            "category": p["reason"],
                            "primary_folder": p["primary_folder"],
                            "target_name": p["target_name"],
                            "target_id": p["target_id"],
                        }
                    )
                except Exception as exc:
                    errors.append({"error": str(exc)[:220]})
                if idx % 100 == 0 or idx == len(planned):
                    print(f"  created & verified {idx}/{len(planned)} shortcuts ({time.time() - t0:.1f}s)...", flush=True)

    applied_at = dt.datetime.now(dt.timezone.utc).isoformat()
    cl_res = {"batch_id": "", "total_entries": 0}
    if not dry_run and not local_catalog_only and created_logs:
        cl_res = du.update_rename_changelog(
            repo_dir,
            created_logs,
            applied_at,
            sync_drive=True,
            batch_id=du.make_batch_id(applied_at, "shortcuts"),
            default_action="create_shortcut",
        )

    dest_counts = collections.Counter(c["folder"] for c in created_logs)
    out = {
        "applied_at": applied_at,
        "dry_run": dry_run or local_catalog_only,
        "original_files_inspected": plan["original_files_inspected"],
        "existing_shortcuts_found": len(shortcuts),
        "series_identified_count": len(plan["series_detected"]),
        "series_identified": plan["series_detected"],
        "shortcuts_planned": len(planned),
        "shortcuts_created": len(created_logs),
        "shortcuts_verified": verified_count,
        "destination_folder_counts": dict(dest_counts.most_common()),
        "manual_classification_count": len(plan["manual_classification"]),
        "manual_classification": plan["manual_classification"][:250],
        "errors_count": len(errors),
        "batch_id": cl_res["batch_id"],
        "shortcuts_created_details": created_logs,
        "errors": errors,
    }

    reports_dir = repo_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "cross_category_shortcuts_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = [
        "# Google Drive Cross-Category Book Collection & Shortcut Report",
        "",
        f"- **Timestamp (UTC):** `{applied_at}`",
        f"- **Dry Run:** `{out['dry_run']}`",
        f"- **Batch ID:** `{cl_res['batch_id']}`",
        "",
        "## Summary Metrics",
        "",
        f"1. **Number of original files inspected:** `{out['original_files_inspected']}`",
        f"2. **Number of series and collections identified:** `{out['series_identified_count']}`",
        f"3. **Number of Google Drive shortcuts created:** `{out['shortcuts_created']}` (verified target pointers: `{out['shortcuts_verified']}`, pre-existing shortcuts kept: `{len(shortcuts)}`)",
        f"4. **Errors / Inaccessible items:** `{len(errors)}`",
        f"5. **Items held for manual classification:** `{out['manual_classification_count']}`",
        "",
        "## 2. Series and Collections Identified",
        "",
        "| Series / Collection | Matched Books | Primary Folder(s) |",
        "|---|---:|---|",
    ]
    for s_name, s_info in plan["series_detected"].items():
        pfs = ", ".join(f"`{p}`" for p in s_info["primary_folders"][:3])
        md.append(f"| {s_name} | {s_info['count']} | {pfs} |")

    md += [
        "",
        "## 6. Destination Folders Where Shortcuts Were Created",
        "",
        "| Destination Folder | Shortcuts Created |",
        "|---|---:|",
    ]
    for df, cnt in dest_counts.most_common():
        md.append(f"| `{df}` | {cnt} |")

    md += [
        "",
        "## 4 & 5. Books & Collections Appearing in Multiple Categories (Primary Location -> Shortcut Destination)",
        "",
        "| Book / Collection | Primary Location | Shortcut Destination | Link Reason |",
        "|---|---|---|---|",
    ]
    for sc in created_logs[:400]:
        md.append(f"| {sc['target_name']} | `{sc['primary_folder']}` | `{sc['folder']}` | `{sc['category']}` |")
    if len(created_logs) > 400:
        md.append(f"\n_...plus {len(created_logs) - 400} additional verified entries recorded in `reports/cross_category_shortcuts_report.json`._")

    md += ["", "## 7. Items Requiring Manual Classification (Left Untouched in Place)", ""]
    for mc in plan["manual_classification"][:100]:
        md.append(f"- `{mc['folder']}` / `{mc['name']}` ({mc['reason']})")

    (reports_dir / "cross_category_shortcuts_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "original_files_inspected": out["original_files_inspected"],
                "series_identified_count": out["series_identified_count"],
                "shortcuts_created": out["shortcuts_created"],
                "shortcuts_verified": out["shortcuts_verified"],
                "manual_classification_count": out["manual_classification_count"],
                "errors_count": out["errors_count"],
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
    ap.add_argument("--max-shortcuts", type=int, default=0)
    args = ap.parse_args()
    run_shortcut_organizer(
        Path(args.repo_dir).resolve(),
        dry_run=args.dry_run,
        local_catalog_only=args.local_catalog_only,
        max_shortcuts=args.max_shortcuts,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
