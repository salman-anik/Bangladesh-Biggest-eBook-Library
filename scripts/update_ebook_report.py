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
    eb_meta = load_json(DATA_DIR / "ebanglalibrary_meta.json", [])
    eb_state = load_json(DATA_DIR / "eb_upload_state.json", {})
    sync_eb_state = load_json(DATA_DIR / "sync_full_eb_state.json", {})
    bde_cat = load_json(DATA_DIR / "bdebooks_catalog.json", [])
    bde_state = load_json(DATA_DIR / "bde_ingest_state.json", {})
    merged_books = load_json(DATA_DIR / "merged_books.json", [])
    rename_state = load_json(DATA_DIR / "book_rename_state.json", {})
    books_all = load_json(REPO_DIR / "books.json", [])

    # Compute breakdowns
    catalog_for_counts = books_all if books_all else merged_books
    top_counts = Counter(b.get("top_category", "Unknown") for b in catalog_for_counts)
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

    eb_complete_cnt = sum(1 for b in eb_meta if isinstance(b, dict) and b.get("full_text_complete"))
    eb_multi_cnt = sum(1 for b in eb_meta if isinstance(b, dict) and int(b.get("chapter_count") or 0) > 0)
    merged_both = sum(1 for m in merged_books if (m.get("pdf_file_id") or m.get("epub_file_id") or any(str(f.get("name", "")).lower().endswith((".pdf", ".epub", ".zip", ".docx", ".doc")) for f in (m.get("files") or []))) and m.get("text_file_id"))
    merged_with_cover = sum(1 for m in merged_books if m.get("cover_file_id") or m.get("cover_url") or m.get("thumbnail_url"))

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
        f"  - Root Layout         : Unified Per-Book Folder Structure (25 Categories directly at Root; no legacy pdf/text/covers split)",
        f"  - Merged Book Folders : {len(merged_books):,} (data/merged_books.json)",
        "  - UNTOUCHED Separate Drive Folder : 1ObOiGGQXl9B4bodcnDkx7g5yU_dc-Gol (Bangladesh-Biggest-Public-Database - DO NOT MODIFY)",
        "",
        "2. FOLDER ARCHITECTURE & NAMING CONVENTION",
        "-" * 80,
        "- Clean English Category & Subcategory Names (no numeric prefixes 01_..25_ and no Bengali suffixes):",
        "  Examples: Fiction, Literature, Religion, Education and Academics, Literature/Children's Literature",
        "- Unified Top-Level Google Drive & GitHub Layout:",
        "  Bangladesh-Biggest-eBook-Library/",
        "    └── <Clean Category>/              (25 clean-named top categories directly at Root)",
        "        └── <Clean Leaf>/              (clean-named subcategories + Class 1..Class 10, Pre-Primary)",
        "            └── <Clean Book Name>/     (1 folder per book, named by true internal title)",
        "                ├── <Clean Book Name>.<pdf|epub|zip|docx|txt>",
        "                ├── <Clean Book Name>.json     (full scraped chapters/topics + metadata)",
        "                └── <Clean Book Name>.<jpg|png|webp> (cover image)",
        f"- Mapped Category/Leaf Drive Folders in data/clean_folders.json : {len(clean_folders):,}",
        "",
        "3. PROGRESS & COLLECTION TOTALS (LIVE STATE)",
        "-" * 80,
        f"- Current Indexed Catalog (books.json)         : {len(books_all):,} records",
        f"- Merged Per-Book Folders (merged_books.json)  : {len(merged_books):,} books ({merged_both:,} with both Ebook & Text JSON | {merged_with_cover:,} with cover image/URL)",
        f"- Ingested Extra Books (data/extra_books.json) : {len(extra):,} records",
        "  Breakdown of Extra Collections:",
    ]
    for k, v in sorted(src_counts.items()):
        lines.append(f"    * {k:<45}: {v:,}")

    lines.extend([
        "",
        "- Website Collection Status:",
        f"    * kindlebangla.com   : {len(kb_cat):,} cataloged pages | {len(kb_state.get('processed_urls', {})):,} Drive processed | {len(kb_state.get('copied_covers', {})):,} Drive covers copied (note: 114 remaining entries are .kfx-only RARs + 1 upstream 404)",
        f"    * ebanglalibrary.com : {len(eb_meta):,} books ({eb_complete_cnt:,} full-text complete across all non-blank chapters; {eb_multi_cnt:,} multi-chapter) | {len(eb_state.get('uploaded', {})):,} initial Drive uploads | {len(sync_eb_state.get('synced', {})):,} full chapter+topic JSONs synced",
        f"    * bdebooks.com/bn/   : {len(bde_cat):,} cataloged books (Cloudflare Error 1006 / 403 blocked beyond initial sample; {len(bde_state.get('processed_slugs', {})):,} processed | {len(bde_state.get('covers_uploaded', {})):,} covers uploaded)",
        "",
        "- Covers & Thumbnails Registry (data/book_covers.json):",
        f"    * Total Tracked Cover/Thumbnail Entries : {len(covers):,}",
        f"    * Cover Files Stored in Drive (per-book): {cov_drive_cnt:,}",
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
        f"- Trashed Junk/Non-Book/Dupes/Legacy Folders: {len(trashed):,}",
        f"- NCTB Textbooks Moved to Class Folders   : {len(reorg.get('nctb_moved', [])):,}",
        f"- NCTB Shared 9-10 Copied to Class 10     : {len(reorg.get('nctb_copied_10', {})):,}",
        f"- Renamed Category/Leaf Folders in Drive  : {len(reorg.get('renamed_folders', {})):,}",
        f"- Book Title Rename State                 : {'Done (' + str(len(rename_state.get('renamed', rename_state))) + ' tracked)' if rename_state else 'Pending'}",
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
        "  - scripts/merge_books_by_title.py         : Merges books into <Category>/<Leaf>/<Book Name>/ & removes pdf/text/covers",
        "  - scripts/sync_full_eb_jsons_to_drive.py  : Streams 3.74 GB ebanglalibrary_raw.json into Drive per-book JSONs",
        "  - scripts/eb_stream.py                    : Streaming JSON array reader & metadata builder (avoids OOM)",
        "  - scripts/fetch_ebanglalibrary_topics.py  : Scrapes LearnDash sub-topics & rebuilds ebanglalibrary_raw.json",
        "  - scripts/build_merged_github_and_report.py: Rebuilds GitHub Markdown tree, books.json, sitemap, visualizer & report",
        "  - scripts/rename_books_by_internal_title.py: Renames books in Drive/catalog to true internal book names",
        "  - scripts/update_ebook_report.py          : Regenerates this report (uses lightweight ebanglalibrary_meta.json)",
        "  - data/merged_books.json                  : Canonical unified per-book folder catalog",
        "  - data/ebanglalibrary_meta.json           : Lightweight 4,183-book metadata index",
        "  - data/book_covers.json                   : Master cover_url, thumbnail_url, and cover_drive_id index",
        "  - data/clean_folders.json                 : Full Drive path -> folder ID map",
        "  - data/extra_books.json                   : Metadata for external collections",
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
