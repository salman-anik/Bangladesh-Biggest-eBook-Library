#!/usr/bin/env python3
"""
Stage 5: Rebuild AnaBook compact catalogs (books.json, visualize/public/books.json,
and App/assets/starter_books.json) directly from live Google Drive without double-counting
Google Drive shortcuts.
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

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import drive_utils as du  # noqa: E402

BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")

KNOWN_SERIES_PATTERNS = [
    ("মাসুদ রানা সিরিজ", "মাসুদ রানা"),
    ("হিমু সিরিজ", "হিমু"),
    ("মিসির আলি সিরিজ", "মিসির আলি"),
    ("শুভ্র সিরিজ", "শুভ্র"),
    ("ফেলুদা সিরিজ", "ফেলুদা"),
    ("প্রফেসর শঙ্কু সিরিজ", "শঙ্কু"),
    ("তিন গোয়েন্দা সিরিজ", "তিন গোয়েন্দা"),
    ("কাকাবাবু সিরিজ", "কাকাবাবু"),
    ("তাফসীর ইবনে কাসীর", "ইবনে কাসীর"),
    ("ফী যিলালিল কুরআন", "যিলালিল কুরআন"),
    ("আল-বিদায়া ওয়ান নিহায়া", "বিদায়া ওয়ান নিহায়া"),
]


def parse_title_author(filename: str, sub_path: str, cat_name: str, prev_author: str) -> tuple[str, str]:
    stem = os.path.splitext(filename or "")[0].strip()
    title = stem
    author = prev_author or "Unknown"

    if " - " in stem:
        left, right = stem.rsplit(" - ", 1)
        if right.strip() and not re.search(r"খন্ড|খণ্ড|পর্ব|\b(vol|volume|part|edition)\b", right, re.I):
            title = left.strip()
            author = right.strip()

    if (not author or author in ("Unknown", "Unknown Author")) and cat_name == "Authors & Scholars" and sub_path:
        parts = [p for p in sub_path.split("/") if p]
        if len(parts) >= 2 and parts[0] in ("Bangladeshi Authors", "International Authors"):
            author = parts[1]
        elif len(parts) >= 3 and parts[0] == "Islamic Scholars":
            author = parts[2]

    return title, author


def detect_lang(title: str, sub_path: str, cat_name: str, prev_lang: str) -> str:
    if prev_lang and prev_lang not in ("", "Unknown"):
        return prev_lang
    if BENGALI_RE.search(title) or BENGALI_RE.search(sub_path) or cat_name == "Bangla Books":
        return "Bangla"
    if ARABIC_RE.search(title):
        return "Arabic"
    if cat_name == "English Books":
        return "English"
    return "Bangla/English"


def detect_series(sub_path: str, title: str, prev_series: str) -> str:
    if "Series & Collections" in sub_path or sub_path:
        parts = [p for p in sub_path.split("/") if p]
        if parts and parts[-1].endswith("সিরিজ"):
            return parts[-1]
    for s_label, kw in KNOWN_SERIES_PATTERNS:
        if kw in title or kw in sub_path:
            return s_label
    return prev_series or ""


def rebuild_catalog(repo_dir: Path) -> dict[str, Any]:
    root_books_path = repo_dir / "books.json"
    old_cat = json.loads(root_books_path.read_text(encoding="utf-8"))
    old_cats = old_cat.get("cats", [])
    old_subs = old_cat.get("subs", [])
    old_langs = old_cat.get("langs", [])
    old_fmts = old_cat.get("fmts", [])

    prev_by_id: dict[str, dict[str, Any]] = {}
    for b in old_cat.get("books", []):
        fid = b[0]
        prev_by_id[fid] = {
            "title": b[1],
            "author": b[2],
            "lang": old_langs[b[5]] if 0 <= b[5] < len(old_langs) else "",
            "coverId": b[8] or "",
            "series": b[9] or "",
        }

    print(f"[CatalogSync] Walking live Drive root {du.ROOT_ID} (shortcuts excluded from book count)...", flush=True)
    tree = du.walk_drive_tree(du.ROOT_ID, skip_top_folders=du.SKIP_TOP_FOLDERS)

    drive_roots = dict(old_cat.get("drive_roots", {}))
    for fp, fid in tree["folders_by_path"].items():
        if "/" not in fp and fp:
            drive_roots[fp] = fid

    cats_list = list(old_cats)
    subs_list: list[str] = [""]
    langs_list: list[str] = []
    fmts_list = list(old_fmts) if old_fmts else ["PDF"]

    def _idx(arr: list[str], val: str) -> int:
        if val not in arr:
            arr.append(val)
        return arr.index(val)

    compact_books: list[list[Any]] = []
    total_bytes = 0
    covers_count = 0
    unique_authors: set[str] = set()

    for f in tree["files"]:
        if f["ext"] not in du.BOOK_EXTS:
            continue
        fid = f["id"]
        fpath = f["folder"]
        parts = [p for p in fpath.split("/") if p]
        cat_name = parts[0] if parts else "Review & Unclassified"
        sub_path = "/".join(parts[1:]) if len(parts) > 1 else ""
        prev = prev_by_id.get(fid, {})

        title, author = parse_title_author(f["name"], sub_path, cat_name, prev.get("author", ""))
        lang = detect_lang(title, sub_path, cat_name, prev.get("lang", ""))
        fmt = f["ext"].lstrip(".").upper() or "PDF"
        cover_id = prev.get("coverId", "")
        series = detect_series(sub_path, title, prev.get("series", ""))
        size = int(f.get("size") or 0)

        if cover_id:
            covers_count += 1
        if author and author not in ("Unknown", "Unknown Author"):
            unique_authors.add(author.lower())
        total_bytes += size

        compact_books.append(
            [
                fid,
                title,
                author,
                _idx(cats_list, cat_name),
                _idx(subs_list, sub_path),
                _idx(langs_list, lang),
                _idx(fmts_list, fmt),
                size,
                cover_id,
                series,
            ]
        )

    compact_books.sort(key=lambda row: (row[3], row[4], row[1].lower()))

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out_catalog = {
        "v": old_cat.get("v", 1),
        "generated_at": today,
        "total": len(compact_books),
        "total_bytes": total_bytes,
        "covers_count": covers_count,
        "authors_count": len(unique_authors),
        "drive_roots": drive_roots,
        "cats": cats_list,
        "subs": subs_list,
        "langs": langs_list,
        "fmts": fmts_list,
        "books": compact_books,
    }

    payload = json.dumps(out_catalog, ensure_ascii=False, separators=(",", ":"))
    root_books_path.write_text(payload, encoding="utf-8")
    vis_books_path = repo_dir / "visualize" / "public" / "books.json"
    vis_books_path.parent.mkdir(parents=True, exist_ok=True)
    vis_books_path.write_text(payload, encoding="utf-8")

    # Refresh starter_books.json entries cleanly from live compact_books
    starter_path = repo_dir / "App" / "assets" / "starter_books.json"
    if starter_path.exists():
        starter_old = json.loads(starter_path.read_text(encoding="utf-8"))
        starter_ids = [b[0] for b in starter_old.get("books", [])]
        live_by_id = {b[0]: b for b in compact_books}
        starter_rows = [live_by_id[bid] for bid in starter_ids if bid in live_by_id]
        if starter_rows:
            starter_out = {
                **out_catalog,
                "total": len(starter_rows),
                "total_bytes": sum(r[7] for r in starter_rows),
                "covers_count": sum(1 for r in starter_rows if r[8]),
                "books": starter_rows,
            }
            starter_path.write_text(json.dumps(starter_out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    summary = {
        "generated_at": today,
        "total_books": len(compact_books),
        "shortcuts_on_drive": len(tree["shortcuts"]),
        "total_bytes": total_bytes,
        "covers_count": covers_count,
        "authors_count": len(unique_authors),
        "subfolders_count": len(subs_list) - 1,
    }
    print("[CatalogSync] Done:", json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-dir", default=".")
    args = ap.parse_args()
    rebuild_catalog(Path(args.repo_dir).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
