#!/usr/bin/env python3
"""
Mirror the 9-folder Google Drive library architecture into the GitHub repository,
generate compact books.json (v2) with cover Drive IDs for the Web Explorer, and
update README.md, website/README.md, and sitemap.xml.

CRITICAL: Strictly read-only with respect to Google Drive; never mutates Drive.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_CATALOG_PATH = REPO_ROOT / "catalog" / "master_catalog.json"
BOOKS_JSON_PATH = REPO_ROOT / "books.json"
ROOT_README_PATH = REPO_ROOT / "README.md"
WEBSITE_README_PATH = REPO_ROOT / "website" / "README.md"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"

TODAY = "2026-11-23"
WEB_BASE_URL = "https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/"
GITHUB_REPO_URL = "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library"
DRIVE_ROOT_URL = "https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
START_HERE_DOC_URL = "https://docs.google.com/document/d/1dEMPkGWXWvx3vSHu708KTfpKwS7IG0Ar_ffKtA4-QDM/edit"

OBSOLETE_NUMBERED_DIRS = [
    "00_Library_Management",
    "01_Bangla_Books",
    "02_English_Books",
    "03_Education_and_Textbooks",
    "04_Religion_Books",
    "05_Authors_and_Scholars",
    "06_Series_and_Collections",
    "07_Reference_and_Research",
    "08_Review_and_Unclassified",
]

DRIVE_ROOTS: dict[str, str] = {
    "Library Management": "1GkKPJ4-Xt8dx954uMhfVZkvYpivU7ukv",
    "Bangla Books": "12SSwDn9I1QPsFynHYuPVgIbStsL-S8gs",
    "English Books": "1T250ptAUwZnv80QxH34qFApKhRZ_s4d9",
    "Education & Textbooks": "1Hoy8Zv0ObmQcGLrDUhmkGSYK_DDSK1BR",
    "Religion Books": "1feCztJCCjKkLJJxJhkN7jyGhCMJiz2K8",
    "Authors & Scholars": "1HG9mZ-FGPOydiFc8h32iIDsKYGY-j9DB",
    "Series & Collections": "1_dHgKueL1AS_EbaXUO-XWCtrgal1JZ8m",
    "Reference & Research": "1p2RgJYCjE1Z8uvIizVfMgKRYB3BFp57B",
    "Review & Unclassified": "17xG7eM-GtkED3hWMfT1riucin9fnlI2t",
}

CATEGORY_ORDER = [
    "Bangla Books",
    "English Books",
    "Education & Textbooks",
    "Religion Books",
    "Authors & Scholars",
    "Series & Collections",
    "Reference & Research",
    "Review & Unclassified",
]

CATEGORY_DESCRIPTIONS = {
    "Bangla Books": "বাংলা উপন্যাস, গল্প, কবিতা, প্রবন্ধ, থ্রিলার ও গোয়েন্দা, অনুবাদ, ইতিহাস, বিজ্ঞান ও শিশু-কিশোর সাহিত্য।",
    "English Books": "English Fiction & Literature, Science & Technology, Computer Science, History, Philosophy, Self Development & Memoirs.",
    "Education & Textbooks": "NCTB textbooks, Admission & Entrance Preparation, Alia Madrasa, University Education, and Qawmi Madrasa (Ibtidaiyah → Takhassus).",
    "Religion Books": "Islam (Quran & Tafsir, Hadith, Fiqh, Aqidah, Seerah, Islamic History, Literature, Dawah) & Other Religions.",
    "Authors & Scholars": "Dedicated author & scholar folders across Bangladeshi Authors, International Authors, and Islamic Scholars.",
    "Series & Collections": "Popular Bangla & international book series, Rachanabali, and multi-volume collections.",
    "Reference & Research": "Dictionaries, Encyclopedias, Academic Journals, Magazines & Research Papers.",
    "Review & Unclassified": "Books queued for metadata enrichment, duplicate verification, or special archival review.",
    "Library Management": "Master Catalog CSV/JSON, Library Master Navigator XLSX, Cover Images (21,627+), Metadata Guides & Reports.",
}

MGMT_LINKS = {
    "start_here": START_HERE_DOC_URL,
    "navigator_xlsx": "https://drive.google.com/file/d/1PBHQfSIQvGCYinQkk6XvtjuGgixbHWbM/view",
    "catalog_csv": "https://drive.google.com/file/d/1OxTZzaESx0WzRr2dqdE7i2LtMjE15L6N/view",
    "catalog_json": "https://drive.google.com/file/d/1qrS1Uifaka3IB2W5gSmkJAAKGJeElxP4/view",
    "qawmi_catalog": "https://drive.google.com/file/d/1B-Or8excxaX7QO-TYNHjZkYRpWC6ajyY/view",
    "cover_images": "https://drive.google.com/drive/folders/1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj",
}

COVER_ID_RE = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")


def fmt_size(num_bytes: int) -> str:
    if num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(num_bytes)
    for unit in units:
        if val < 1000.0 or unit == units[-1]:
            if unit in ("B", "KB"):
                return f"{val:.0f} {unit}"
            return f"{val:.2f} {unit}"
        val /= 1000.0
    return f"{num_bytes} B"


def sanitize_segment(seg: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", seg.strip())
    cleaned = cleaned.strip(" .")
    if not cleaned or cleaned in (".", ".."):
        return "_Other"
    # Guard against Windows reserved device names
    upper = cleaned.upper()
    if upper in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        cleaned = f"_{cleaned}"
    return cleaned


def extract_cover_id(cover_url: str | None) -> str:
    if not cover_url:
        return ""
    m = COVER_ID_RE.search(cover_url)
    if m:
        return m.group(1)
    if "id=" in cover_url:
        m2 = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", cover_url)
        if m2:
            return m2.group(1)
    return ""


def md_escape(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def url_encode_path(parts: list[str]) -> str:
    return "/".join(quote(p, safe="-_.~") for p in parts)


def remove_old_and_existing_root_dirs() -> list[str]:
    removed: list[str] = []
    targets = OBSOLETE_NUMBERED_DIRS + list(DRIVE_ROOTS.keys())
    for dirname in targets:
        target_path = REPO_ROOT / dirname
        if target_path.exists() and target_path.is_dir():
            shutil.rmtree(target_path)
            removed.append(dirname)
    return removed


class FolderNode:
    def __init__(self, display_name: str, fs_segment: str, logical_parts: list[str]):
        self.display_name = display_name
        self.fs_segment = fs_segment
        self.logical_parts = logical_parts  # [root_category, sub1, sub2, ...]
        self.children: dict[str, FolderNode] = {}
        self.direct_books: list[dict[str, Any]] = []
        self.recursive_count = 0
        self.recursive_bytes = 0
        self.recursive_covers = 0

    def compute_stats(self) -> tuple[int, int, int]:
        cnt = len(self.direct_books)
        total_b = sum(int(b.get("file_size") or 0) for b in self.direct_books)
        covs = sum(1 for b in self.direct_books if b.get("_cover_id"))
        for child in self.children.values():
            c_cnt, c_b, c_cov = child.compute_stats()
            cnt += c_cnt
            total_b += c_b
            covs += c_cov
        self.recursive_count = cnt
        self.recursive_bytes = total_b
        self.recursive_covers = covs
        return cnt, total_b, covs


def build_tree(books: list[dict[str, Any]]) -> dict[str, FolderNode]:
    roots: dict[str, FolderNode] = {}
    for cat in CATEGORY_ORDER:
        roots[cat] = FolderNode(cat, sanitize_segment(cat), [cat])

    for book in books:
        cat = (book.get("category") or "Review & Unclassified").strip()
        if cat not in roots:
            roots[cat] = FolderNode(cat, sanitize_segment(cat), [cat])
        node = roots[cat]
        sub = (book.get("subcategory") or "").strip()
        if sub:
            parts = [p.strip() for p in sub.split("/") if p.strip()]
            for part in parts:
                if part not in node.children:
                    # Deduplicate sanitized sibling names if two distinct logical names collapse
                    base_seg = sanitize_segment(part)
                    existing_segs = {ch.fs_segment for ch in node.children.values()}
                    fs_seg = base_seg
                    idx = 2
                    while fs_seg in existing_segs:
                        fs_seg = f"{base_seg}_{idx}"
                        idx += 1
                    node.children[part] = FolderNode(
                        part,
                        fs_seg,
                        node.logical_parts + [part],
                    )
                node = node.children[part]
        node.direct_books.append(book)

    for root in roots.values():
        root.compute_stats()
    return roots


def write_folder_readmes(roots: dict[str, FolderNode]) -> int:
    files_written = 0

    def walk_node(node: FolderNode, fs_parts: list[str], trail_nodes: list[FolderNode]) -> None:
        nonlocal files_written
        folder_dir = REPO_ROOT.joinpath(*fs_parts)
        folder_dir.mkdir(parents=True, exist_ok=True)
        depth = len(fs_parts)
        to_repo_root = "../" * depth

        # Build breadcrumb links
        crumbs = [f"[🏠 Library Home]({to_repo_root}README.md)"]
        for idx, ancestor in enumerate(trail_nodes):
            steps_up = depth - (idx + 1)
            if steps_up == 0:
                crumbs.append(f"**{ancestor.display_name}**")
            else:
                rel = ("../" * steps_up) + "README.md"
                crumbs.append(f"[{ancestor.display_name}]({rel})")

        root_cat = node.logical_parts[0]
        drive_id = DRIVE_ROOTS.get(root_cat, "")
        sub_path = "/".join(node.logical_parts[1:])

        web_params = f"?category={quote(root_cat)}"
        if sub_path:
            web_params += f"&sub={quote(sub_path)}"
        web_filter_url = f"{WEB_BASE_URL}{web_params}"

        lines: list[str] = [
            f"# {node.display_name}",
            "",
            " / ".join(crumbs),
            "",
        ]
        if depth == 1 and root_cat in CATEGORY_DESCRIPTIONS:
            lines.append(f"> {CATEGORY_DESCRIPTIONS[root_cat]}")
            lines.append("")

        meta_badges = [
            f"**Books:** `{node.recursive_count:,}`",
            f"**Total Size:** `{fmt_size(node.recursive_bytes)}`",
            f"**Covers:** `{node.recursive_covers:,}`",
        ]
        if drive_id:
            meta_badges.append(
                f"[📂 Open Root in Google Drive](https://drive.google.com/drive/folders/{drive_id})"
            )
        meta_badges.append(f"[🌐 Browse in Web Explorer]({web_filter_url})")

        lines.append(" | ".join(meta_badges))
        lines.append("")

        if node.children:
            lines.extend([
                "## Subfolders",
                "",
                "| Folder | Books | Covers | Size |",
                "|---|---:|---:|---:|",
            ])
            for child in sorted(node.children.values(), key=lambda c: c.display_name.lower()):
                link = f"{url_encode_path([child.fs_segment])}/README.md"
                lines.append(
                    f"| 📁 [{md_escape(child.display_name)}]({link}) | {child.recursive_count:,} | {child.recursive_covers:,} | {fmt_size(child.recursive_bytes)} |"
                )
            lines.append("")

        if node.direct_books:
            lines.extend([
                f"## Books ({len(node.direct_books):,})",
                "",
                "| # | Title | Author | Format | Size | Actions |",
                "|---:|---|---|---|---:|---|",
            ])
            sorted_books = sorted(
                node.direct_books,
                key=lambda b: (b.get("title") or "").lower(),
            )
            for idx, book in enumerate(sorted_books, 1):
                fid = book.get("drive_file_id") or ""
                title = md_escape(book.get("title") or book.get("original_title") or "Untitled")
                author = md_escape(book.get("author") or "Unknown")
                fmt = md_escape(book.get("format") or "PDF")
                size_str = fmt_size(int(book.get("file_size") or 0))
                read_url = f"https://drive.google.com/file/d/{fid}/preview"
                dl_url = f"https://drive.google.com/uc?export=download&id={fid}"
                actions = [
                    f"[📖 Read]({read_url})",
                    f"[⬇️ Download]({dl_url})",
                ]
                if book.get("cover_url"):
                    actions.append(f"[🖼️ Cover]({book['cover_url']})")
                lines.append(
                    f"| {idx} | {title} | {author} | {fmt} | {size_str} | {' · '.join(actions)} |"
                )
            lines.append("")

        (folder_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        files_written += 1

        for child in node.children.values():
            walk_node(child, fs_parts + [child.fs_segment], trail_nodes + [child])

    for cat in CATEGORY_ORDER:
        root_node = roots[cat]
        walk_node(root_node, [root_node.fs_segment], [root_node])

    # Write Library Management tree matching Google Drive
    mgmt_dir = REPO_ROOT / "Library Management"
    mgmt_subfolders = {
        "Cover Images": (
            "# Cover Images\n\n"
            "[🏠 Library Home](../../README.md) / [Library Management](../README.md) / **Cover Images**\n\n"
            "> Centralized archive of book cover photos organized in a mirrored category/book hierarchy.\n\n"
            f"[📂 Open Cover Images in Google Drive]({MGMT_LINKS['cover_images']}) | "
            f"[🌐 Browse Books with Covers]({WEB_BASE_URL})\n\n"
            "## Summary\n\n"
            "- All cover images are consolidated under `Library Management / Cover Images` on Google Drive.\n"
            "- Covers are matched cleanly by book title & category and linked in `master_catalog.json` and `books.json`.\n"
            "- Covered books appear directly as card thumbnails in the Web Search Explorer.\n"
        ),
        "Master Catalog": (
            "# Master Catalog\n\n"
            "[🏠 Library Home](../../README.md) / [Library Management](../README.md) / **Master Catalog**\n\n"
            "> Authoritative bilingual catalog indexes with direct Google Drive Read, Download, and Cover links.\n\n"
            f"[📊 Master Navigator (.xlsx) on Drive]({MGMT_LINKS['navigator_xlsx']}) | "
            f"[📄 Master Catalog CSV on Drive]({MGMT_LINKS['catalog_csv']}) | "
            f"[🧩 Master Catalog JSON on Drive]({MGMT_LINKS['catalog_json']})\n\n"
            "## Repository Catalog Files\n\n"
            "- [catalog/master_catalog.csv](../../catalog/master_catalog.csv)\n"
            "- [catalog/master_catalog.json](../../catalog/master_catalog.json)\n"
            "- [catalog/Bangladesh_eBook_Library_Master_Navigator.xlsx](../../catalog/Bangladesh_eBook_Library_Master_Navigator.xlsx)\n"
            "- [catalog/Bangladesh_eBook_Library_Master_Navigator.csv](../../catalog/Bangladesh_eBook_Library_Master_Navigator.csv)\n"
        ),
        "Reports": (
            "# Reports & Verification\n\n"
            "[🏠 Library Home](../../README.md) / [Library Management](../README.md) / **Reports**\n\n"
            "> Automated audit logs, verification reports, and Qawmi Madrasa catalog maps.\n\n"
            f"[📊 Qawmi Madrasa Catalog (.xlsx) on Drive]({MGMT_LINKS['qawmi_catalog']})\n\n"
            "## Repository Report Files\n\n"
            "- [reports/verification_report.md](../../reports/verification_report.md)\n"
            "- [reports/verification_report.json](../../reports/verification_report.json)\n"
            "- [reports/Qawmi Madrasa Category Map & Book Catalog.csv](../../reports/Qawmi%20Madrasa%20Category%20Map%20%26%20Book%20Catalog.csv)\n"
            "- [reports/Qawmi Madrasa Category Map & Book Catalog.xlsx](../../reports/Qawmi%20Madrasa%20Category%20Map%20%26%20Book%20Catalog.xlsx)\n"
        ),
        "Metadata": (
            "# Metadata & Guidelines\n\n"
            "[🏠 Library Home](../../README.md) / [Library Management](../README.md) / **Metadata**\n\n"
            "> Taxonomies, author/category/series indexes, and licensing/provenance documentation.\n\n"
            f"[📖 START HERE - Library Guide (Google Doc)]({MGMT_LINKS['start_here']})\n\n"
            "## Repository Index Files\n\n"
            "- [catalog/CATEGORY_INDEX.md](../../catalog/CATEGORY_INDEX.md)\n"
            "- [catalog/AUTHOR_INDEX.md](../../catalog/AUTHOR_INDEX.md)\n"
            "- [catalog/SERIES_INDEX.md](../../catalog/SERIES_INDEX.md)\n"
            "- [catalog/SOURCES_AND_LICENSES.md](../../catalog/SOURCES_AND_LICENSES.md)\n"
        ),
    }

    mgmt_dir.mkdir(parents=True, exist_ok=True)
    mgmt_readme = (
        "# Library Management\n\n"
        "[🏠 Library Home](../README.md) / **Library Management**\n\n"
        f"> {CATEGORY_DESCRIPTIONS['Library Management']}\n\n"
        f"[📂 Open Library Management in Google Drive](https://drive.google.com/drive/folders/{DRIVE_ROOTS['Library Management']}) | "
        f"[📖 START HERE - Library Guide]({MGMT_LINKS['start_here']})\n\n"
        "## Management Sections\n\n"
        "| Section | Description | Links |\n"
        "|---|---|---|\n"
        f"| 📁 [Cover Images](Cover%20Images/README.md) | 21,627+ book covers organized by category & book name | [Open Drive Folder]({MGMT_LINKS['cover_images']}) |\n"
        f"| 📁 [Master Catalog](Master%20Catalog/README.md) | Master Catalog CSV/JSON & Master Navigator XLSX | [Open Navigator XLSX]({MGMT_LINKS['navigator_xlsx']}) |\n"
        f"| 📁 [Reports](Reports/README.md) | Library verification & Qawmi Madrasa catalogs | [Open Qawmi Catalog]({MGMT_LINKS['qawmi_catalog']}) |\n"
        "| 📁 [Metadata](Metadata/README.md) | Author, Category, Series & License documentation | [START HERE Guide](" + MGMT_LINKS["start_here"] + ") |\n"
    )
    (mgmt_dir / "README.md").write_text(mgmt_readme, encoding="utf-8")
    files_written += 1

    for sub_name, content in mgmt_subfolders.items():
        sub_path = mgmt_dir / sub_name
        sub_path.mkdir(parents=True, exist_ok=True)
        (sub_path / "README.md").write_text(content, encoding="utf-8")
        files_written += 1

    return files_written


def build_books_json(books: list[dict[str, Any]]) -> dict[str, Any]:
    cats_list = list(CATEGORY_ORDER)
    cat_idx_map = {c: i for i, c in enumerate(cats_list)}

    subs_list: list[str] = []
    sub_idx_map: dict[str, int] = {}

    langs_list: list[str] = []
    lang_idx_map: dict[str, int] = {}

    fmts_list: list[str] = []
    fmt_idx_map: dict[str, int] = {}

    compact_books: list[list[Any]] = []
    total_bytes = 0
    covers_count = 0
    named_authors: set[str] = set()

    for book in books:
        fid = (book.get("drive_file_id") or "").strip()
        title = (book.get("title") or book.get("original_title") or "Untitled").strip()
        author = (book.get("author") or "Unknown").strip()
        cat = (book.get("category") or "Review & Unclassified").strip()
        sub = (book.get("subcategory") or "").strip()
        lang = (book.get("language") or "Unknown").strip()
        fmt = (book.get("format") or "PDF").strip().upper()
        size_b = int(book.get("file_size") or 0)
        cover_id = extract_cover_id(book.get("cover_url"))
        book["_cover_id"] = cover_id
        series = (book.get("series") or "").strip()

        if cat not in cat_idx_map:
            cat_idx_map[cat] = len(cats_list)
            cats_list.append(cat)

        if sub not in sub_idx_map:
            sub_idx_map[sub] = len(subs_list)
            subs_list.append(sub)

        if lang not in lang_idx_map:
            lang_idx_map[lang] = len(langs_list)
            langs_list.append(lang)

        if fmt not in fmt_idx_map:
            fmt_idx_map[fmt] = len(fmts_list)
            fmts_list.append(fmt)

        total_bytes += size_b
        if cover_id:
            covers_count += 1
        if author and author.lower() not in {"unknown", "various", "various / unknown", "n/a", "-"}:
            named_authors.add(author)

        compact_books.append([
            fid,
            title,
            author,
            cat_idx_map[cat],
            sub_idx_map[sub],
            lang_idx_map[lang],
            fmt_idx_map[fmt],
            size_b,
            cover_id,
            series,
        ])

    payload = {
        "v": 2,
        "generated_at": TODAY,
        "total": len(compact_books),
        "total_bytes": total_bytes,
        "covers_count": covers_count,
        "authors_count": len(named_authors),
        "drive_roots": DRIVE_ROOTS,
        "cats": cats_list,
        "subs": subs_list,
        "langs": langs_list,
        "fmts": fmts_list,
        "books": compact_books,
    }
    BOOKS_JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return payload


def update_root_readme(roots: dict[str, FolderNode], payload: dict[str, Any]) -> None:
    total_books = payload["total"]
    total_size = fmt_size(payload["total_bytes"])
    covers_count = payload["covers_count"]
    cover_pct = (covers_count / total_books * 100) if total_books else 0.0
    subcat_count = len([s for s in payload["subs"] if s])

    rows_md = [
        f"| [`Library Management/`](Library%20Management/README.md) | Catalog, Covers ({covers_count:,}) & Reports | — | [Open Folder](https://drive.google.com/drive/folders/{DRIVE_ROOTS['Library Management']}) | [START HERE Guide]({MGMT_LINKS['start_here']}) |"
    ]
    for cat in CATEGORY_ORDER:
        node = roots[cat]
        gh_link = f"[`{cat}/`]({url_encode_path([node.fs_segment])}/README.md)"
        drive_link = f"[Open Folder](https://drive.google.com/drive/folders/{DRIVE_ROOTS[cat]})"
        web_link = f"[Browse on Web]({WEB_BASE_URL}?category={quote(cat)})"
        rows_md.append(
            f"| {gh_link} | {node.recursive_count:,} | {fmt_size(node.recursive_bytes)} | {drive_link} | {web_link} |"
        )

    readme = f"""# Bangladesh's Biggest eBook Library (বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি)

[🌐 Web Search Explorer]({WEB_BASE_URL}) | [📂 Google Drive Library]({DRIVE_ROOT_URL}) | [📖 START HERE Guide]({MGMT_LINKS['start_here']}) | [📊 Master Navigator XLSX](catalog/Bangladesh_eBook_Library_Master_Navigator.xlsx) | [📄 Master Catalog CSV](catalog/master_catalog.csv) | [🧩 Master Catalog JSON](catalog/master_catalog.json) | [🖼️ Cover Images Archive]({MGMT_LINKS['cover_images']})

**{total_books:,} verified eBooks** (**{total_size}**) with **{covers_count:,} book covers ({cover_pct:.1f}%)** organized across **9 clean top-level folders** mirrored 1:1 with Google Drive (zero numbered root prefixes, full Qawmi Madrasa Level → Subject hierarchy, reorganized English Books, and structured Admission & Entrance Preparation collections).

## Mirrored Folder Architecture (GitHub ⇄ Google Drive)

| Folder | Books | Size | Google Drive | Web Explorer |
|---|---:|---:|---|---|
{chr(10).join(rows_md)}

## Web Search Explorer & Indexes

- **Interactive Web Explorer:** [{WEB_BASE_URL}]({WEB_BASE_URL}) — Browse the mirrored 9-folder Google Drive tree, view book covers, preview/read PDFs & EPUBs in-page, or download directly with one click.
- **Directory Indexes:** [Categories ({subcat_count})](catalog/CATEGORY_INDEX.md) · [Authors ({payload['authors_count']:,}+)](catalog/AUTHOR_INDEX.md) · [Series (28)](catalog/SERIES_INDEX.md) · [Qawmi Madrasa Catalog (3,457)](reports/Qawmi%20Madrasa%20Category%20Map%20%26%20Book%20Catalog.csv) · [Sources & Licenses](catalog/SOURCES_AND_LICENSES.md)
- **Verification Reports:** [verification_report.md](reports/verification_report.md) · [verification_report.json](reports/verification_report.json)

## Catalog, Cover Archive & Organization

- **Cover Images Archive:** **{covers_count:,} / {total_books:,} ({cover_pct:.1f}%)** covers curated and arranged by category and book name in [Library Management / Cover Images](Library%20Management/Cover%20Images/README.md).
- **Qawmi Madrasa Taxonomy:** Organized by educational level (`Ibtidaiyah`, `Mutawassitah`, `Sanabiyah`, `Fazilat`, `Takmil (Dawra-e-Hadith)`, `Takhassus`, `Common & Reference Books`, `Review & Unclassified (Qawmi)`) → subject folders.
- **Admission & Entrance Preparation:** Structured under `Education & Textbooks/General Education/Admission & Entrance Preparation` across Medical & Dental, University Admission, Engineering & Technology, Agriculture, HSC & Academic, General Competitive Exams, and Publisher & Coaching Collections.
- **Zero Duplication:** Multi-category resources and publisher collections use Google Drive shortcuts instead of duplicate physical PDFs.

## Curator & Maintainer

- **Curator:** Salman Anik (সালমান অনীক)
- **Email:** [salmananik.bd@gmail.com](mailto:salmananik.bd@gmail.com)
- **GitHub:** [github.com/salman-anik](https://github.com/salman-anik)
"""
    ROOT_README_PATH.write_text(readme, encoding="utf-8")


def update_website_readme(payload: dict[str, Any]) -> None:
    content = f"""# 🌐 Bangladesh's Biggest eBook Library — Web Search Explorer

A fast, zero-dependency bilingual web application served via GitHub Pages at [{WEB_BASE_URL}]({WEB_BASE_URL}) for discovering, previewing, and downloading **{payload['total']:,}+ free eBooks** (**{fmt_size(payload['total_bytes'])}**) mirrored directly from the 9-folder Google Drive architecture.

## Key Features

- **Mirrored 9-Folder Drive Tree Sidebar:** Navigate `Bangla Books`, `English Books`, `Education & Textbooks`, `Religion Books`, `Authors & Scholars`, `Series & Collections`, `Reference & Research`, `Review & Unclassified`, and `Library Management` with live recursive book counts and direct Google Drive folder links.
- **Book Cover Art Cards:** Displays **{payload['covers_count']:,}+ curated cover thumbnails** directly from Google Drive (`Library Management / Cover Images`) with clean typographic fallback covers when an image is unavailable.
- **Instant In-Page Reader Modal (`Read`):** Preview books inside an embedded Google Drive viewer without leaving the page.
- **One-Click Direct Download (`Download`):** Download books directly from Google Drive with instant toast feedback.
- **Multilingual Search & Facets:** Instant client-side search across Bangla, English, and Arabic titles, authors, categories, subcategories, and series, plus filters for Format (`PDF`, `EPUB`, `MOBI`, `DOCX`, `DOC`, `TXT`), Language, Sort order, and Cover availability.
- **Reading List & Dark/Light Mode:** Bookmark favorite books locally (`localStorage`) and toggle between dark and light themes.

## Architecture

- [`../index.html`](../index.html) — Semantic explorer shell, SEO metadata, Drive tree sidebar, reader modal, and bookmarks drawer.
- [`../styles.css`](../styles.css) — Responsive dark/light theme styling and 2:3 cover card layout.
- [`../app.js`](../app.js) — Compact catalog loader (`books.json` v2), interactive tree builder, search/filter engine, Drive preview & download handlers.
- [`../books.json`](../books.json) — Compact columnar JSON index generated from `catalog/master_catalog.json` via [`../scripts/sync_github_architecture_and_web.py`](../scripts/sync_github_architecture_and_web.py).
"""
    WEBSITE_README_PATH.write_text(content, encoding="utf-8")


def update_sitemap() -> None:
    urls = [
        WEB_BASE_URL,
        f"{GITHUB_REPO_URL}/blob/main/README.md",
    ]
    for root_name in list(DRIVE_ROOTS.keys()):
        seg = sanitize_segment(root_name)
        urls.append(f"{GITHUB_REPO_URL}/blob/main/{quote(seg, safe='-_.~')}/README.md")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        lines.append(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>")
    lines.append("</urlset>")
    SITEMAP_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not MASTER_CATALOG_PATH.exists():
        raise FileNotFoundError(f"Missing {MASTER_CATALOG_PATH}")

    books: list[dict[str, Any]] = json.loads(MASTER_CATALOG_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(books):,} books from {MASTER_CATALOG_PATH.name}")

    removed = remove_old_and_existing_root_dirs()
    print(f"Cleaned {len(removed)} directories: {', '.join(removed) if removed else 'none'}")

    payload = build_books_json(books)
    json_size = BOOKS_JSON_PATH.stat().st_size
    print(
        f"Wrote {BOOKS_JSON_PATH.name}: {payload['total']:,} books, "
        f"{payload['covers_count']:,} covers, {len(payload['subs'])} subcats, "
        f"{fmt_size(json_size)}"
    )

    roots = build_tree(books)
    readme_count = write_folder_readmes(roots)
    print(f"Generated {readme_count} folder README.md files across 9 clean Drive-mirrored roots")

    update_root_readme(roots, payload)
    update_website_readme(payload)
    update_sitemap()
    print("Updated README.md, website/README.md, and sitemap.xml successfully")


if __name__ == "__main__":
    main()
