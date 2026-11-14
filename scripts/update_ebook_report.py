import datetime
import json
import pathlib
import subprocess
import sys
from collections import Counter

REPO_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
REPORT_PATHS = [
    pathlib.Path(r"C:\Users\USER\Desktop\Report\ebook_report.txt"),
    pathlib.Path(r"C:\Users\USER\Desktop\ebook_report.txt"),
]


def load_json(p: pathlib.Path, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO_DIR), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")

    reorg = load_json(DATA_DIR / "reorg_state.json", {})
    clean_folders = load_json(DATA_DIR / "clean_folders.json", {})
    extra = load_json(DATA_DIR / "extra_books.json", [])
    covers = load_json(DATA_DIR / "book_covers.json", {})
    trashed = load_json(DATA_DIR / "trashed_ids.json", [])
    kb_cat = load_json(DATA_DIR / "kindlebangla_catalog.json", [])
    kb_state = load_json(DATA_DIR / "kb_ingest_state.json", {})
    eb_raw = load_json(DATA_DIR / "ebanglalibrary_raw.json", [])
    eb_state = load_json(DATA_DIR / "eb_upload_state.json", {})
    bde_cat = load_json(DATA_DIR / "bdebooks_catalog.json", [])
    bde_state = load_json(DATA_DIR / "bde_ingest_state.json", {})
    books_all = load_json(REPO_DIR / "books.json", [])

    # Compute breakdowns
    top_counts = Counter(b.get("top_category", "Unknown") for b in books_all)
    src_counts = Counter()
    for b in extra:
        sid = b.get("source_id") or ""
        pub = b.get("publication") or ""
        if sid.startswith("kb:"):
            src_counts["KindleBangla (kindlebangla.com)"] += 1
        elif sid.startswith("eb:"):
            src_counts["eBanglaLibrary JSON (ebanglalibrary.com)"] += 1
        elif sid.startswith("bde:"):
            src_counts["BDeBooks (bdebooks.com/bn)"] += 1
        elif sid.startswith("gh:"):
            src_counts["GitHub Open Collections"] += 1
        elif sid.startswith("ia:"):
            src_counts["Archive.org Bengali Verified"] += 1
        elif sid.startswith("nctb10:") or "NCTB" in (b.get("name") or "") or "nctb" in pub.lower():
            src_counts["NCTB Textbooks (Class 1-10 & Pre-Primary)"] += 1
        elif "Hadith" in pub or sid.startswith("hadith:"):
            src_counts["Hadith JSONs"] += 1
        else:
            src_counts["BD Public Shared Drive Folders"] += 1

    cls_counts = Counter()
    for b in extra:
        lp = b.get("leaf_path") or ""
        if "Education and Academics/" in lp:
            cls = lp.split("Education and Academics/")[-1].split("/")[0]
            cls_counts[cls] += 1

    cov_by_src = Counter(v.get("source", "unknown") for v in covers.values() if isinstance(v, dict))
    cov_drive_cnt = sum(1 for v in covers.values() if isinstance(v, dict) and v.get("cover_drive_id"))

    lines = [
        "=" * 80,
        "BANGLADESH BIGGEST EBOOK LIBRARY - AI HANDOFF & ARCHITECTURE REPORT",
        f"Updated: {now}",
        "=" * 80,
        "",
        "1. QUICK REFERENCE & LIVE LINKS",
        "-" * 80,
        f"- Local Repository Path : {REPO_DIR}",
        f"- GitHub Repository     : https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library (branch: main, HEAD: {git_head()})",
        f"- Live Explorer Site    : https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/",
        f"- Google Drive Root     : https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq (Name: Bangladesh-Biggest-eBook-Library)",
        f"  - Root Renamed        : {reorg.get('root_renamed', False)}",
        f"  - pdf/ Folder ID      : {clean_folders.get('pdf', reorg.get('top_created', {}).get('pdf', 'pending'))}",
        f"  - text/ Folder ID     : {clean_folders.get('text', reorg.get('top_created', {}).get('text', 'pending'))}",
        f"  - covers/ Folder ID   : {clean_folders.get('covers', reorg.get('top_created', {}).get('covers', 'pending'))}",
        "  - UNTOUCHED Separate Drive Folder : 1ObOiGGQXl9B4bodcnDkx7g5yU_dc-Gol (Bangladesh-Biggest-Public-Database - DO NOT MODIFY)",
        "",
        "2. FOLDER ARCHITECTURE & NAMING CONVENTION",
        "-" * 80,
        "- Clean English Category & Subcategory Names (no numeric prefixes 01_..25_ and no Bengali suffixes):",
        "  Examples: Fiction, Literature, Religion, Education and Academics, Literature/Children's Literature",
        "- Top-Level Google Drive Layout:",
        "  Bangladesh-Biggest-eBook-Library/",
        "    ├── pdf/       -> 25 clean-named categories + Education and Academics/{Pre-Primary, Class 1..Class 10}",
        "    ├── text/      -> 25 clean-named categories containing 1 JSON file per ebanglalibrary.com book",
        "    └── covers/    -> Cover & thumbnail image archive (KindleBangla/, BDeBooks/, eBanglaLibrary/)",
        f"- Mapped Drive Folders in data/clean_folders.json : {len(clean_folders)}",
        "",
        "3. PROGRESS & COLLECTION TOTALS (LIVE STATE)",
        "-" * 80,
        f"- Current Indexed Catalog (books.json)         : {len(books_all):,} records",
        f"- Ingested Extra Books (data/extra_books.json) : {len(extra):,} records",
        "  Breakdown of Extra Collections:",
    ]
    for k, v in sorted(src_counts.items()):
        lines.append(f"    * {k:<45}: {v:,}")

    lines.extend([
        "",
        "- Website Collection Status:",
        f"    * kindlebangla.com   : {len(kb_cat):,} cataloged pages | {len(kb_state.get('processed_urls', {})):,} Drive processed | {len(kb_state.get('copied_covers', {})):,} Drive covers copied",
        f"    * ebanglalibrary.com : {len(eb_raw):,} cataloged books | {len(eb_state.get('uploaded', {})):,} JSON files uploaded to text/",
        f"    * bdebooks.com/bn/   : {len(bde_cat):,} cataloged books | {len(bde_state.get('processed_slugs', {})):,} processed | {len(bde_state.get('covers_uploaded', {})):,} Drive covers uploaded",
        "",
        "- Covers & Thumbnails Registry (data/book_covers.json):",
        f"    * Total Tracked Cover/Thumbnail Entries : {len(covers):,}",
        f"    * Cover Files Stored in Drive covers/   : {cov_drive_cnt:,}",
    ])
    for src, cnt in sorted(cov_by_src.items()):
        lines.append(f"    * {src:<30}: {cnt:,} cover/thumbnail URLs")

    lines.extend([
        "",
        "4. EDUCATIONAL BOOKS (CLASS 1 TO 10 + PRE-PRIMARY)",
        "-" * 80,
    ])
    for cname in ["Pre-Primary"] + [f"Class {i}" for i in range(1, 11)] + ["Higher Secondary", "Primary Education"]:
        lines.append(f"  - {cname:<18}: {cls_counts.get(cname, 0):,} books")

    lines.extend([
        "",
        "5. CLEANUP, JUNK PURGE & INTERNAL TITLE RENAMING",
        "-" * 80,
        f"- Trashed Junk/Non-Book Files (IA CIA Reading Room, Sinhala, .ini, .apk): {len(trashed):,}",
        f"- NCTB Textbooks Moved to Class Folders   : {len(reorg.get('nctb_moved', [])):,}",
        f"- NCTB Shared 9-10 Copied to Class 10     : {len(reorg.get('nctb_copied_10', {})):,}",
        f"- Renamed Category/Leaf Folders in Drive  : {len(reorg.get('renamed_folders', {})):,}",
        f"- Book Title Rename State                 : {'Done' if (DATA_DIR / 'book_rename_state.json').exists() else 'Pending / Scheduled after collections'}",
        "",
        "6. TOP CATEGORIES DISTRIBUTION (FROM books.json)",
        "-" * 80,
    ])
    for tc, cnt in sorted(top_counts.items()):
        lines.append(f"  - {tc:<55}: {cnt:,}")

    lines.extend([
        "",
        "7. SCRIPTS & DATA FILES REFERENCE",
        "-" * 80,
        "  - scripts/reorganize_drive_and_clean.py   : Cleans Drive root & folder names, purges junk, creates Class 1-10",
        "  - scripts/collect_kindlebangla.py         : Crawls kindlebangla.com, copies ebooks & covers into Drive",
        "  - scripts/collect_ebanglalibrary_json.py  : Crawls ebanglalibrary.com, exports 1 JSON/book to text/ & covers",
        "  - scripts/collect_bdebooks.py             : Crawls bdebooks.com/bn/, downloads PDFs/EPUBs & covers",
        "  - scripts/rename_books_by_internal_title.py: Renames all books in Drive/catalog to true internal book names",
        "  - scripts/build_25cat_library.py          : Generates clean Markdown tree, SEO FAQ README, books.json, sitemap",
        "  - scripts/update_ebook_report.py          : Regenerates this report (always run after work)",
        "  - data/book_covers.json                   : Master cover_url, thumbnail_url, and cover_drive_id index",
        "  - data/clean_folders.json                 : Full Drive path -> folder ID map for pdf/, text/, covers/",
        "  - data/extra_books.json                   : Metadata for all ingested external collections",
        "  - C:\\Users\\USER\\Desktop\\Report\\ebook_report.txt : Canonical AI handoff report",
        "",
        "=" * 80,
        "END OF REPORT",
        "=" * 80,
    ])

    content = "\n".join(lines) + "\n"
    for rp in REPORT_PATHS:
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(content, encoding="utf-8")
    print(f"Updated report: {REPORT_PATHS[0]} ({len(lines)} lines)", flush=True)


if __name__ == "__main__":
    main()
