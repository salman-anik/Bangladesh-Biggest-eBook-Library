#!/usr/bin/env python3
"""
Rebuild the clean GitHub repository tree from data/merged_books.json and
data/clean_folders.json so every book lives inside its own clean folder:
  <Category>/<Leaf>/<Clean Book Name>/README.md
with direct Google Drive links to the Book Folder, PDF/EPUB, Text JSON, and Cover.

Also regenerates root README.md, AUTHORS.md, PUBLICATIONS.md, sitemap.xml,
books.json, visualize/public/books.json, and visualize/public/taxonomy.json,
while removing legacy pdf/ and text/ wrapper directories from the Git tree.
"""
from __future__ import annotations

import json
import shutil
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import clean_classifier as cc

ROOT_DRIVE_ID = "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
GITHUB_REPO = "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library"
GITHUB_PAGES = "https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library"

CANONICAL_TOP_CATS = sorted({leaf.split("/")[0] for leaf in cc.CANONICAL_LEAVES})


def fmt_size(num: int) -> str:
    if not num:
        return "—"
    v = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if v < 1024 or unit == "TB":
            return f"{int(v)} {unit}" if unit == "B" else f"{v:.1f} {unit}"
        v /= 1024
    return f"{num} B"


def gh_tree_url(rel_path: str) -> str:
    encoded = "/".join(urllib.parse.quote(seg, safe="") for seg in rel_path.strip("/").split("/"))
    return f"{GITHUB_REPO}/tree/main/{encoded}"


def gh_blob_url(rel_path: str) -> str:
    encoded = "/".join(urllib.parse.quote(seg, safe="") for seg in rel_path.strip("/").split("/"))
    return f"{GITHUB_REPO}/blob/main/{encoded}"


def drive_file_url(fid: str) -> str:
    return f"https://drive.google.com/file/d/{fid}/view"


def drive_folder_url(fid: str) -> str:
    return f"https://drive.google.com/drive/folders/{fid}"


def drive_thumb_url(fid: str) -> str:
    return f"https://drive.google.com/thumbnail?id={fid}&sz=w600"


def escape_md(text: str) -> str:
    return str(text or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def write_book_readme(book: dict[str, Any]) -> None:
    leaf = book["leaf_path"]
    cat = book["top_category"]
    bname = book["name"]
    book_dir = ROOT / leaf / bname
    book_dir.mkdir(parents=True, exist_ok=True)

    folder_id = book["folder_id"]
    pdf_id = book.get("pdf_file_id") or ""
    epub_id = book.get("epub_file_id") or ""
    text_id = book.get("text_file_id") or ""
    cov_id = book.get("cover_file_id") or ""
    cov_url = book.get("cover_url") or ""

    lines = [
        f"# 📖 {bname}",
        "",
        f"[⬅️ Back to Home]({GITHUB_REPO}/blob/main/README.md) / "
        f"[{cat}]({gh_blob_url(f'{cat}/README.md')}) / "
        f"[{book['leaf_category']}]({gh_blob_url(f'{leaf}/README.md')}) | "
        f"[📁 Open Book Folder in Google Drive]({drive_folder_url(folder_id)})",
        "",
    ]
    if cov_id:
        lines.extend([f"![{escape_md(book.get('title') or bname)}]({drive_thumb_url(cov_id)})", ""])
    elif cov_url:
        lines.extend([f"![{escape_md(book.get('title') or bname)}]({cov_url})", ""])

    lines.extend([
        "## 📦 Available Files & Links",
        "",
        "| Resource | Link |",
        "|---|---|",
        f"| 📁 **Book Folder (All Files)** | [Open Folder in Drive]({drive_folder_url(folder_id)}) |",
    ])
    if pdf_id:
        lines.append(f"| 📕 **PDF eBook** | [Open PDF in Drive]({drive_file_url(pdf_id)}) |")
    if epub_id:
        lines.append(f"| 📱 **EPUB eBook** | [Open EPUB in Drive]({drive_file_url(epub_id)}) |")
    if text_id:
        lines.append(f"| 📄 **Structured Text (JSON)** | [Open Text JSON in Drive]({drive_file_url(text_id)}) |")
    if cov_id:
        lines.append(f"| 🖼️ **Cover Image** | [View Cover in Drive]({drive_file_url(cov_id)}) |")

    lines.extend([
        "",
        "## ℹ️ Metadata",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| **Title** | {escape_md(book.get('title') or bname)} |",
        f"| **Author** | {escape_md(book.get('author') or 'Various / Unknown')} |",
        f"| **Publication / Source** | {escape_md(book.get('publication') or '—')} |",
        f"| **Category** | {escape_md(leaf)} |",
        f"| **Subfolder** | {escape_md(book.get('subfolder') or '—')} |",
        f"| **Formats** | {escape_md(', '.join(book.get('formats') or []) or '—')} |",
        f"| **Total Size** | {fmt_size(int(book.get('size') or 0))} |",
        "",
    ])
    if book.get("files"):
        lines.extend(["### 📂 Files Inside Folder", ""])
        for f in book["files"]:
            lines.append(f"- [{escape_md(f['name'])}]({drive_file_url(f['id'])}) ({fmt_size(int(f.get('size') or 0))})")
        lines.append("")

    (book_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_leaf_readme(leaf: str, leaf_books: list[dict], clean_folders: dict[str, str]) -> None:
    parts = leaf.split("/")
    top_cat = parts[0]
    leaf_dir = ROOT / leaf
    leaf_dir.mkdir(parents=True, exist_ok=True)
    drive_id = clean_folders.get(leaf, ROOT_DRIVE_ID)
    total_sz = sum(int(b.get("size") or 0) for b in leaf_books)

    lines = [
        f"# 📂 {leaf}",
        "",
        f"[⬅️ Back to Home]({GITHUB_REPO}/blob/main/README.md) / "
        f"[{top_cat}]({gh_blob_url(f'{top_cat}/README.md')}) | "
        f"[📁 Open Folder in Google Drive]({drive_folder_url(drive_id)})",
        "",
        f"**Total Books:** {len(leaf_books):,} | **Total Size:** {fmt_size(total_sz)}",
        "",
    ]
    if leaf_books:
        lines.extend([
            "## 📖 Books (Folder = PDF / EPUB + Text JSON + Cover)",
            "",
            "| # | Book Folder & Name | Author | Formats | Size | Google Drive Folder |",
            "|---:|---|---|---|---:|---|",
        ])
        for idx, b in enumerate(sorted(leaf_books, key=lambda x: x["name"].lower()), 1):
            bname = b["name"]
            book_md_url = gh_blob_url(f"{leaf}/{bname}/README.md")
            fmts = ", ".join(b.get("formats") or []) or "—"
            lines.append(
                f"| {idx} | [{escape_md(bname)}]({book_md_url}) | "
                f"{escape_md(b.get('author') or '—')} | {escape_md(fmts)} | "
                f"{fmt_size(int(b.get('size') or 0))} | "
                f"[Open Folder]({drive_folder_url(b['folder_id'])}) |"
            )
    else:
        lines.append("_No books in this subcategory yet._")
    lines.append("")
    (leaf_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_category_readme(cat: str, leaves: list[str], by_leaf: dict[str, list[dict]], clean_folders: dict[str, str]) -> None:
    cat_dir = ROOT / cat
    cat_dir.mkdir(parents=True, exist_ok=True)
    cat_books = [b for lf in leaves for b in by_leaf.get(lf, [])]
    drive_id = clean_folders.get(cat, ROOT_DRIVE_ID)
    total_sz = sum(int(b.get("size") or 0) for b in cat_books)

    lines = [
        f"# 📚 {cat}",
        "",
        f"[⬅️ Back to Home]({GITHUB_REPO}/blob/main/README.md) | "
        f"[📁 Open Category in Google Drive]({drive_folder_url(drive_id)})",
        "",
        f"**Subcategories:** {len(leaves)} | **Total Books:** {len(cat_books):,} | **Total Size:** {fmt_size(total_sz)}",
        "",
        "| Subcategory | Books | Total Size | Drive Folder |",
        "|---|---:|---:|---|",
    ]
    for lf in sorted(leaves):
        sub_label = lf[len(cat) + 1 :]
        lbs = by_leaf.get(lf, [])
        sz = sum(int(b.get("size") or 0) for b in lbs)
        fid = clean_folders.get(lf, ROOT_DRIVE_ID)
        lines.append(
            f"| [{sub_label}]({gh_blob_url(f'{lf}/README.md')}) | {len(lbs):,} | "
            f"{fmt_size(sz)} | [Open Folder]({drive_folder_url(fid)}) |"
        )
    lines.append("")
    (cat_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    merged_p = DATA / "merged_books.json"
    folders_p = DATA / "clean_folders.json"
    if not merged_p.exists():
        raise FileNotFoundError(f"Missing {merged_p}; run merge_books_by_title.py first")

    merged = json.loads(merged_p.read_text(encoding="utf-8"))
    local_added_p = DATA / "local_added_books.json"
    if local_added_p.exists():
        local_added = json.loads(local_added_p.read_text(encoding="utf-8"))
        seen_fids = {b.get("folder_id") for b in merged if b.get("folder_id")}
        added_local = 0
        for b in local_added:
            fid = b.get("folder_id")
            if fid and fid not in seen_fids:
                merged.append(b)
                seen_fids.add(fid)
                added_local += 1
        if added_local:
            merged_p.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
            print(f"Merged {added_local} books from local_added_books.json into merged_books.json", flush=True)
    clean_folders = json.loads(folders_p.read_text(encoding="utf-8"))

    # 1. Remove stale legacy pdf/ and text/ directories from Git workspace root
    for legacy_dir in ("pdf", "text"):
        lp = ROOT / legacy_dir
        if lp.exists():
            print(f"Removing stale directory {lp}...", flush=True)
            shutil.rmtree(lp)

    # Clear & index by leaf/top before creating any directories
    for cat in CANONICAL_TOP_CATS:
        cp = ROOT / cat
        if cp.exists():
            shutil.rmtree(cp)

    # Index by leaf
    by_leaf: dict[str, list[dict]] = defaultdict(list)
    by_top: dict[str, list[dict]] = defaultdict(list)
    for b in merged:
        by_leaf[b["leaf_path"]].append(b)
        by_top[b["top_category"]].append(b)

    leaves_by_top: dict[str, list[str]] = defaultdict(list)
    for lf in sorted(cc.CANONICAL_LEAVES):
        if by_leaf.get(lf):
            leaves_by_top[lf.split("/")[0]].append(lf)

    non_empty_tops = [cat for cat in CANONICAL_TOP_CATS if by_top.get(cat)]
    for cat in non_empty_tops:
        (ROOT / cat).mkdir(parents=True, exist_ok=True)

    # 2. Write per-book folder READMEs, leaf READMEs, and category READMEs (skipping empty folders)
    print(f"Writing {len(merged):,} per-book folder READMEs across {sum(len(v) for v in leaves_by_top.values())} non-empty leaves...", flush=True)
    for b in merged:
        write_book_readme(b)
    for lf in sorted(cc.CANONICAL_LEAVES):
        if by_leaf.get(lf):
            write_leaf_readme(lf, by_leaf[lf], clean_folders)
    for cat in non_empty_tops:
        write_category_readme(cat, leaves_by_top[cat], by_leaf, clean_folders)

    # Also Religion/Islam intermediate README
    islam_leaves = [lf for lf in leaves_by_top.get("Religion", []) if lf.startswith("Religion/Islam/")]
    if islam_leaves:
        (ROOT / "Religion" / "Islam").mkdir(parents=True, exist_ok=True)
        write_category_readme("Religion/Islam", islam_leaves, by_leaf, clean_folders)

    # 3. Export clean books.json, visualize/public/books.json, visualize/public/taxonomy.json
    total_size = sum(int(b.get("size") or 0) for b in merged)
    catalog_records = []
    for b in merged:
        catalog_records.append({
            "folder_id": b["folder_id"],
            "file_id": b["file_id"],
            "name": b["name"],
            "size": b["size"],
            "mimeType": "application/pdf" if b.get("pdf_file_id") else (
                "application/epub+zip" if b.get("epub_file_id") else "application/json"
            ),
            "top_category": b["top_category"],
            "leaf_path": b["leaf_path"],
            "leaf_category": b["leaf_category"],
            "subfolder": b.get("subfolder") or None,
            "author": b["author"],
            "publication": b["publication"],
            "link": b["folder_link"],
            "pdf_file_id": b.get("pdf_file_id") or "",
            "epub_file_id": b.get("epub_file_id") or "",
            "text_file_id": b.get("text_file_id") or "",
            "cover_file_id": b.get("cover_file_id") or "",
            "cover_drive_id": b.get("cover_file_id") or "",
            "cover_url": b.get("cover_url") or "",
            "thumbnail_url": b.get("thumbnail_url") or "",
            "formats": b.get("formats") or [],
            "section": "merged",
        })

    books_json_str = json.dumps(catalog_records, ensure_ascii=False)
    (ROOT / "books.json").write_text(books_json_str, encoding="utf-8")
    vis_pub = ROOT / "visualize" / "public"
    vis_pub.mkdir(parents=True, exist_ok=True)
    (vis_pub / "books.json").write_text(books_json_str, encoding="utf-8")
    tax_tree: dict[str, Any] = {}
    for cat in CANONICAL_TOP_CATS:
        if not by_top.get(cat):
            continue
        lfs = sorted(lf for lf in leaves_by_top.get(cat, []) if by_leaf.get(lf))
        if cat == "Religion":
            islam_lfs = [lf.split("/")[-1] for lf in lfs if lf.startswith("Religion/Islam/")]
            other_lfs = [lf.split("/")[-1] for lf in lfs if not lf.startswith("Religion/Islam/")]
            tax_tree[cat] = {"Islam": islam_lfs, **{o: [] for o in other_lfs}} if islam_lfs else other_lfs
        else:
            tax_tree[cat] = [lf.split("/", 1)[1] for lf in lfs]

    (vis_pub / "taxonomy.json").write_text(
        json.dumps(
            {
                "root_drive_id": ROOT_DRIVE_ID,
                "root_drive_name": "Bangladesh-Biggest-eBook-Library",
                "folders": clean_folders,
                "tree": tax_tree,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 4. Write AUTHORS.md, PUBLICATIONS.md, sitemap.xml, README.md
    author_counts = Counter(b.get("author") or "Various / Unknown" for b in merged)
    pub_counts = Counter(b.get("publication") or "General Archive" for b in merged)

    auth_lines = [
        "# ✍️ Authors Index",
        "",
        f"Total distinct authors: **{len(author_counts):,}** across **{len(merged):,}** merged book folders.",
        "",
        "| Author | Books |",
        "|---|---:|",
    ]
    for a, cnt in author_counts.most_common():
        auth_lines.append(f"| {escape_md(a)} | {cnt:,} |")
    (ROOT / "AUTHORS.md").write_text("\n".join(auth_lines) + "\n", encoding="utf-8")

    pub_lines = [
        "# 🏢 Publications & Sources Index",
        "",
        f"Total sources/publications: **{len(pub_counts):,}** across **{len(merged):,}** merged book folders.",
        "",
        "| Publication / Source | Books |",
        "|---|---:|",
    ]
    for p, cnt in pub_counts.most_common():
        pub_lines.append(f"| {escape_md(p)} | {cnt:,} |")
    (ROOT / "PUBLICATIONS.md").write_text("\n".join(pub_lines) + "\n", encoding="utf-8")

    # Root README.md
    root_lines = [
        "# 📚 Bangladesh's Biggest eBook Library",
        "",
        f"[🌐 Browse Searchable Web Explorer]({GITHUB_PAGES}/) | "
        f"[📁 Open Google Drive Root]({drive_folder_url(ROOT_DRIVE_ID)}) | "
        f"[✍️ Authors ({len(author_counts):,})](AUTHORS.md) | "
        f"[🏢 Publications ({len(pub_counts):,})](PUBLICATIONS.md)",
        "",
        f"**{len(merged):,} Unified Book Folders** organized cleanly across **25 Categories & {len(cc.CANONICAL_LEAVES)} Subcategories** (**{fmt_size(total_size)}** total).",
        "",
        "Every book resides in its own dedicated `<Category>/<Subcategory>/<Clean Book Name>/` folder containing the book's **PDF / EPUB**, **Structured Text JSON**, and **Cover Image** together.",
        "",
        "## 🗂️ Categories (25)",
        "",
        "| # | Category | Books | Total Size | Drive Folder |",
        "|---:|---|---:|---:|---|",
    ]
    for idx, cat in enumerate(non_empty_tops, 1):
        cbooks = by_top.get(cat, [])
        sz = sum(int(b.get("size") or 0) for b in cbooks)
        fid = clean_folders.get(cat, ROOT_DRIVE_ID)
        root_lines.append(
            f"| {idx} | [{cat}]({gh_blob_url(f'{cat}/README.md')}) | {len(cbooks):,} | "
            f"{fmt_size(sz)} | [Open Folder]({drive_folder_url(fid)}) |"
        )
    root_lines.append("")
    (ROOT / "README.md").write_text("\n".join(root_lines), encoding="utf-8")

    # sitemap.xml
    today = date.today().isoformat()
    sm_urls = [f"{GITHUB_PAGES}/", f"{GITHUB_REPO}/blob/main/README.md"]
    for cat in non_empty_tops:
        sm_urls.append(gh_blob_url(f"{cat}/README.md"))
    for lf in sorted(cc.CANONICAL_LEAVES):
        if by_leaf.get(lf):
            sm_urls.append(gh_blob_url(f"{lf}/README.md"))
    sm_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in sm_urls:
        sm_lines.append(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>")
    sm_lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sm_lines) + "\n", encoding="utf-8")

    # Update .gitignore to prevent >100MB local caches from blocking git push
    gi_p = ROOT / ".gitignore"
    gi_lines = [ln.strip() for ln in gi_p.read_text(encoding="utf-8").splitlines() if ln.strip()] if gi_p.exists() else []
    needed_ignores = [
        "data/ebanglalibrary_raw.json",
        "data/eb_chapters.sqlite",
        "data/*.sqlite*",
        "data/live_drive_snapshot.json",
        "data/*.tmp",
        "tmp_*/",
        "__pycache__/",
        "*.pyc",
    ]
    for ign in needed_ignores:
        if ign not in gi_lines:
            gi_lines.append(ign)
    gi_p.write_text("\n".join(gi_lines) + "\n", encoding="utf-8")
    print("Rebuilt clean GitHub repo structure, books.json, visualize JSONs, and .gitignore!", flush=True)


if __name__ == "__main__":
    main()
