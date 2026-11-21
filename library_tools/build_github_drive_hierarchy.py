"""
Build GitHub Folder Hierarchy Matching Google Drive Architecture 1:1.
Generates clean markdown navigators (README.md) for all categories,
subcategories, author collections, and series collections, complete with
direct Google Drive links and interactive book listing tables.
"""

import json
import os
import re
import shutil
from pathlib import Path
from collections import defaultdict, Counter

def fmt_size(n_bytes):
    try:
        n = float(n_bytes)
        if n >= 1e9:
            return f"{n / (1024**3):.2f} GB"
        if n >= 1e6:
            return f"{n / (1024**2):.1f} MB"
        if n >= 1e3:
            return f"{n / 1024:.0f} KB"
        return f"{int(n)} B"
    except Exception:
        return "—"

def clean_val(v):
    if not v or v == "Unknown":
        return "—"
    return str(v).strip()

def main():
    repo_dir = Path(r'C:\Users\USER\.gemini\antigravity\scratch\Bangladesh-Biggest-eBook-Library')
    catalog_path = repo_dir / 'catalog' / 'master_catalog.json'
    drive_map_path = Path(r'C:\Users\USER\.gemini\antigravity\brain\fc64da93-615a-4dd3-b630-983a9609f78a\scratch\drive_folders_map.json')
    author_map_path = Path(r'C:\Users\USER\.gemini\antigravity\brain\fc64da93-615a-4dd3-b630-983a9609f78a\scratch\live_author_folders_map.json')

    print("Loading data...")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    with open(drive_map_path, 'r', encoding='utf-8') as f:
        folders_map = json.load(f)

    with open(author_map_path, 'r', encoding='utf-8') as f:
        author_map = json.load(f)

    print(f"Loaded {len(catalog)} books. Grouping by category & subcategory...")

    # Group books by Category -> Subcategory
    cat_tree = defaultdict(lambda: defaultdict(list))
    author_books = defaultdict(list)
    series_books = defaultdict(list)

    for b in catalog:
        c = b.get('category', '08_Review_and_Unclassified')
        s = b.get('subcategory', '')
        cat_tree[c][s].append(b)

        auth = b.get('author')
        if auth and auth not in ('Unknown', 'NCTB', 'এনসিটিবি'):
            author_books[auth].append(b)

        ser = b.get('series')
        if ser:
            series_books[ser].append(b)

    def get_drive_link(cat, sub=""):
        c_info = folders_map.get(cat, {})
        fid = None
        if sub and 'nested_subfolders' in c_info and sub in c_info['nested_subfolders']:
            fid = c_info['nested_subfolders'][sub]
        elif sub and sub in c_info.get('subfolders', {}):
            fid = c_info['subfolders'][sub]
        elif sub and '/' in sub and sub.split('/')[0] in c_info.get('subfolders', {}):
            fid = c_info['subfolders'][sub.split('/')[0]]
        elif c_info.get('id'):
            fid = c_info['id']

        if fid:
            return f"https://drive.google.com/drive/folders/{fid}"
        return ""

    excel_link = "https://drive.google.com/file/d/1PBHQfSIQvGCYinQkk6XvtjuGgixbHWbM/view"
    root_drive = "https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"

    # Helper to generate book markdown table
    def build_book_table(book_list):
        lines = [
            "| # | Title | Author | Year | Format | Size | Google Drive |",
            "|---:|---|---|:---:|:---:|---:|:---:|"
        ]
        # Sort by title
        sorted_books = sorted(book_list, key=lambda x: x.get('title', ''))
        for idx, b in enumerate(sorted_books, start=1):
            t = b.get('title', 'Untitled').replace('|', '/')
            a = clean_val(b.get('author', '—')).replace('|', '/')
            y = clean_val(b.get('publication_year', '—'))
            fmt = clean_val(b.get('format', 'PDF'))
            sz = fmt_size(b.get('file_size', 0))
            fid = b.get('drive_file_id', '')
            blink = f"[📖 Open Book](https://drive.google.com/file/d/{fid}/view)" if fid else "—"
            lines.append(f"| {idx} | **{t}** | {a} | {y} | {fmt} | {sz} | {blink} |")
        return "\n".join(lines)

    # 1. GENERATE PRIMARY CATEGORIES & SUBCATEGORIES
    primary_categories = [
        ('01_Bangla_Books', 'বাংলা বই (Bangla Books)', 'বাংলা সাহিত্য, উপন্যাস, ছোটগল্প, কবিতা, নাটক, ইতিহাস ও প্রবন্ধের সমৃদ্ধ ভাণ্ডার।'),
        ('02_English_Books', 'English Books', 'Classic & modern English literature, science, technology, history, and philosophy.'),
        ('03_Education_and_Textbooks', 'শিক্ষা ও পাঠ্যবই (Education and Textbooks)', 'NCTB জাতীয় শিক্ষাক্রম ও পাঠ্যপুস্তক বোর্ডের সকল শ্রেণির বই (১ম-১০ম শ্রেণি), এইচএসসি ও ভর্তি পরীক্ষার সহায়িকা।'),
        ('04_Islamic_Books', 'ইসলামিক বই (Islamic Books)', 'কুরআন ও তাফসির, হাদিস, ফিকহ, আকিদা, সীরাত ও ইসলামিক ইতিহাসের নির্ভরযোগ্য গ্রন্থাবলী।'),
        ('07_Reference_and_Research', 'রেফারেন্স ও গবেষণা (Reference and Research)', 'অভিধান, বিশ্বকোষ, গবেষণাপত্র ও সাময়িকী সংগ্রহ।'),
        ('08_Review_and_Unclassified', 'রিভিউ ও অসংজ্ঞায়িত (Review and Unclassified)', 'পর্যালোচনা ও পুনঃশ্রেণিবিভাগের জন্য সংরক্ষিত বই ও ফাইল।'),
    ]

    for cat_name, cat_title, cat_desc in primary_categories:
        cat_dir = repo_dir / cat_name
        cat_dir.mkdir(parents=True, exist_ok=True)
        cat_link = get_drive_link(cat_name)

        subs = cat_tree.get(cat_name, {})
        total_cat_books = sum(len(b_l) for b_l in subs.values())
        total_cat_size = sum(sum(b.get('file_size', 0) for b in b_l) for b_l in subs.values())

        # Build subfolder table for category README
        sub_table_lines = [
            "| Subcategory / Genre | Books | Size | Local Navigator | Google Drive |",
            "|---|---:|---:|:---:|:---:|"
        ]

        for sub_name, b_list in sorted(subs.items(), key=lambda kv: -len(kv[1])):
            if not sub_name:
                continue
            s_link = get_drive_link(cat_name, sub_name)
            s_size = sum(b.get('file_size', 0) for b in b_list)
            # Safe sub path
            s_rel = f"[{sub_name}]({sub_name}/README.md)"
            d_rel = f"[📂 Open Folder]({s_link})" if s_link else "—"
            sub_table_lines.append(f"| {s_rel} | {len(b_list):,} | {fmt_size(s_size)} | [Browse]({sub_name}/README.md) | {d_rel} |")

            # Generate Subcategory Directory & README.md
            sub_dir = cat_dir / sub_name
            sub_dir.mkdir(parents=True, exist_ok=True)

            # Check nesting depth for relative link back
            depth = len(Path(sub_name).parts)
            back_to_cat = "../" * depth
            back_to_root = "../" * (depth + 1)

            sub_readme_lines = [
                f"# 📖 {Path(sub_name).name}",
                "",
                f"[🏠 Home]({back_to_root}README.md) / [{cat_name}]({back_to_cat}README.md) / **{Path(sub_name).name}**",
                "",
                f"> **📂 Google Drive:** [Open in Google Drive]({s_link})  ",
                f"> **📊 Master Spreadsheet:** [Open Excel Navigator]({excel_link})  ",
                f"> **Total Books:** **{len(b_list):,}** | **Total Size:** **{fmt_size(s_size)}**",
                "",
                "---",
                "",
                "## 📚 Books in this Section",
                "",
                build_book_table(b_list),
                "",
                "---",
                f"[⬅️ Back to {cat_name}]({back_to_cat}README.md) | [🏠 Back to Library Home]({back_to_root}README.md)"
            ]

            with open(sub_dir / "README.md", "w", encoding="utf-8") as sf:
                sf.write("\n".join(sub_readme_lines) + "\n")

        # Category README.md
        cat_readme_lines = [
            f"# 📂 {cat_title}",
            "",
            f"[🏠 Home](../README.md) / **{cat_name}**",
            "",
            f"> {cat_desc}",
            "",
            f"> **📂 Google Drive Folder:** [Open in Google Drive]({cat_link})  ",
            f"> **📊 Master Spreadsheet:** [Open Excel Navigator]({excel_link})  ",
            f"> **Total Holdings:** **{total_cat_books:,} books** ({fmt_size(total_cat_size)}) across **{len(subs)} subcategories**",
            "",
            "---",
            "",
            "## 📁 Subcategories & Sections",
            "",
            "\n".join(sub_table_lines),
            "",
            "---",
            "[🏠 Back to Library Home](../README.md)"
        ]

        with open(cat_dir / "README.md", "w", encoding="utf-8") as cf:
            cf.write("\n".join(cat_readme_lines) + "\n")

        print(f"Generated {cat_name}: {total_cat_books} books, {len(subs)} subcategories.")

    # 2. GENERATE 00_Library_Management
    mgmt_dir = repo_dir / "00_Library_Management"
    mgmt_dir.mkdir(parents=True, exist_ok=True)
    mgmt_link = get_drive_link("00_Library_Management")

    mgmt_subs = [
        ("Master_Catalog", "Master Catalog, Spreadsheet & Exports", "https://drive.google.com/drive/folders/1xzoJhv6-mxQ_I25MUH2abKNzEUXpnAd4"),
        ("Reports", "Verification, Audit & Organization Reports", "https://drive.google.com/drive/folders/1jdKRqfUfxyv78EfCZnv8A_CTQnDN_Lp_"),
        ("Metadata", "Raw Metadata Extraction & eBanglaLibrary JSON", "https://drive.google.com/drive/folders/1f9zNvH6WonF-70DPnHIYy3CmoRX1dV9L"),
        ("Cover_Images", "Extracted Book Cover Images", "https://drive.google.com/drive/folders/1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj"),
    ]

    for m_sub, m_desc, m_link in mgmt_subs:
        s_d = mgmt_dir / m_sub
        s_d.mkdir(parents=True, exist_ok=True)
        with open(s_d / "README.md", "w", encoding="utf-8") as f:
            f.write(f"# 📂 {m_sub}\n\n[🏠 Home](../../README.md) / [00_Library_Management](../README.md) / **{m_sub}**\n\n> {m_desc}\n\n[📂 Open in Google Drive]({m_link})\n")

    mgmt_readme = [
        "# ⚙️ 00_Library_Management",
        "",
        "[🏠 Home](../README.md) / **00_Library_Management**",
        "",
        "> Administrative management, metadata catalogs, master spreadsheets, and audit verification reports.",
        "",
        f"[📂 Open in Google Drive]({mgmt_link}) | [📊 Master Spreadsheet]({excel_link})",
        "",
        "## Sections",
        "",
        "| Section | Description | Drive Folder |",
        "|---|---|:---:|",
        "| [Master_Catalog](Master_Catalog/README.md) | Official Master Spreadsheet, CSV, and JSON database | [Open Folder](https://drive.google.com/drive/folders/1xzoJhv6-mxQ_I25MUH2abKNzEUXpnAd4) |",
        "| [Reports](Reports/README.md) | Audit logs, verification reports, and duplicates analysis | [Open Folder](https://drive.google.com/drive/folders/1jdKRqfUfxyv78EfCZnv8A_CTQnDN_Lp_) |",
        "| [Metadata](Metadata/README.md) | Scraped metadata and eBanglaLibrary JSON backups | [Open Folder](https://drive.google.com/drive/folders/1f9zNvH6WonF-70DPnHIYy3CmoRX1dV9L) |",
        "| [Cover_Images](Cover_Images/README.md) | Book covers archive | [Open Folder](https://drive.google.com/drive/folders/1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj) |",
        "",
        "---",
        "[🏠 Back to Library Home](../README.md)"
    ]
    with open(mgmt_dir / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(mgmt_readme) + "\n")

    # 3. GENERATE 05_Authors_and_Scholars
    auth_dir = repo_dir / "05_Authors_and_Scholars"
    auth_dir.mkdir(parents=True, exist_ok=True)
    auth_link = get_drive_link("05_Authors_and_Scholars")

    bn_auth_dir = auth_dir / "বাংলা বর্ণমালা"
    az_auth_dir = auth_dir / "A-Z"
    bn_auth_dir.mkdir(parents=True, exist_ok=True)
    az_auth_dir.mkdir(parents=True, exist_ok=True)

    bn_auth_link = "https://drive.google.com/drive/folders/12hrCkJA6ABOYu5LlETm8cuOxu7ZkktGM"
    az_auth_link = "https://drive.google.com/drive/folders/1t4sbTJRytV1btgWIJrqosHuXstIaEAtx"

    # Bangla authors table
    bn_rows = [
        "| # | Author Name | Books in Library | Drive Folder | Navigator |",
        "|---:|---|---:|:---:|:---:|"
    ]
    az_rows = [
        "| # | Author Name | Books in Library | Drive Folder | Navigator |",
        "|---:|---|---:|:---:|:---:|"
    ]

    bn_idx = 1
    az_idx = 1

    sorted_canonical_authors = sorted(author_map.items(), key=lambda kv: (-len(author_books.get(kv[0], [])), kv[0]))

    for auth_name, a_info in sorted_canonical_authors:
        b_list = author_books.get(auth_name, [])
        d_link = a_info['link']
        a_type = a_info['type']

        # Create author folder with README if author has books
        if b_list:
            if a_type == 'Bangla':
                target_sub = bn_auth_dir / auth_name
            else:
                target_sub = az_auth_dir / auth_name

            target_sub.mkdir(parents=True, exist_ok=True)

            # Group author books by genre / series
            a_genres = defaultdict(list)
            for b in b_list:
                g = b.get('series') or b.get('subcategory') or 'অন্যান্য'
                a_genres[g].append(b)

            a_readme_lines = [
                f"# ✍️ {auth_name}",
                "",
                f"[🏠 Home](../../../README.md) / [05_Authors_and_Scholars](../../README.md) / [{a_type} Index](../README.md) / **{auth_name}**",
                "",
                f"> **📂 Google Drive Author Folder:** [Open in Drive]({d_link})  ",
                f"> **Total Books in Library:** **{len(b_list)} books** across {len(a_genres)} genres/series",
                "",
                "---",
                "",
                "## 📚 Collections & Genres",
                ""
            ]

            for g_name, g_books in sorted(a_genres.items(), key=lambda kv: -len(kv[1])):
                a_readme_lines.append(f"### 📂 {g_name} ({len(g_books)} books)")
                a_readme_lines.append(build_book_table(g_books))
                a_readme_lines.append("")

            a_readme_lines.append("---")
            a_readme_lines.append(f"[⬅️ Back to {a_type} Index](../README.md) | [🏠 Back to Library Home](../../../README.md)")

            with open(target_sub / "README.md", "w", encoding="utf-8") as af:
                af.write("\n".join(a_readme_lines) + "\n")

        # Add to index table
        if a_type == 'Bangla':
            nav_link = f"[View Works]({auth_name}/README.md)" if b_list else "—"
            bn_rows.append(f"| {bn_idx} | **{auth_name}** | {len(b_list)} | [📂 Open Folder]({d_link}) | {nav_link} |")
            bn_idx += 1
        else:
            nav_link = f"[View Works]({auth_name}/README.md)" if b_list else "—"
            az_rows.append(f"| {az_idx} | **{auth_name}** | {len(b_list)} | [📂 Open Folder]({d_link}) | {nav_link} |")
            az_idx += 1

    # Write বাংলা বর্ণমালা README
    with open(bn_auth_dir / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join([
            "# ✍️ বাংলা বর্ণমালা লেখক ইনডেক্স (Bangla Authors)",
            "",
            "[🏠 Home](../../README.md) / [05_Authors_and_Scholars](../README.md) / **বাংলা বর্ণমালা**",
            "",
            f"> **📂 Google Drive Folder:** [Open in Google Drive]({bn_auth_link})",
            "",
            f"**Total Canonical Authors:** **{bn_idx - 1} authors** (One author = One folder)",
            "",
            "---",
            "",
            "\n".join(bn_rows),
            "",
            "---",
            "[🏠 Back to Library Home](../../README.md)"
        ]) + "\n")

    # Write A-Z README
    with open(az_auth_dir / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join([
            "# ✍️ English Authors Index (A-Z)",
            "",
            "[🏠 Home](../../README.md) / [05_Authors_and_Scholars](../README.md) / **A-Z**",
            "",
            f"> **📂 Google Drive Folder:** [Open in Google Drive]({az_auth_link})",
            "",
            f"**Total Canonical English Authors:** **{az_idx - 1} authors**",
            "",
            "---",
            "",
            "\n".join(az_rows),
            "",
            "---",
            "[🏠 Back to Library Home](../../README.md)"
        ]) + "\n")

    # Write 05_Authors_and_Scholars README
    with open(auth_dir / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join([
            "# ✍️ 05_Authors_and_Scholars (লেখক ও গবেষকবৃন্দ)",
            "",
            "[🏠 Home](../README.md) / **05_Authors_and_Scholars**",
            "",
            "> **Architecture Principle:** **One author = One folder**, with clean genre/series subfolders and no year-based fragmentation. Zero physical PDF duplication (shortcuts reference primary category storage).",
            "",
            f"[📂 Open in Google Drive]({auth_link}) | [📊 Master Spreadsheet]({excel_link})",
            "",
            "## Author Indices",
            "",
            "| Index Branch | Authors | Description | Drive Folder |",
            "|---|---:|---|:---:|",
            f"| [বাংলা বর্ণমালা](বাংলা বর্ণমালা/README.md) | {bn_idx - 1} | বাংলা সাহিত্যের সকল প্রথিতযশা লেখক ও গবেষক | [Open in Drive]({bn_auth_link}) |",
            f"| [A-Z](A-Z/README.md) | {az_idx - 1} | International & English classic authors | [Open in Drive]({az_auth_link}) |",
            "",
            "---",
            "[🏠 Back to Library Home](../README.md)"
        ]) + "\n")

    print(f"Generated 05_Authors_and_Scholars: {bn_idx - 1} Bangla authors, {az_idx - 1} English authors.")

    # 4. GENERATE 06_Series_and_Collections
    series_dir = repo_dir / "06_Series_and_Collections"
    series_dir.mkdir(parents=True, exist_ok=True)
    series_link = get_drive_link("06_Series_and_Collections")

    series_subfolders = folders_map.get("06_Series_and_Collections", {}).get("subfolders", {})
    series_table_lines = [
        "| Series Name | Books | Google Drive Link | Local Navigator |",
        "|---|---:|:---:|:---:|"
    ]

    for s_name, s_fid in sorted(series_subfolders.items()):
        s_dlink = f"https://drive.google.com/drive/folders/{s_fid}"
        s_books = series_books.get(s_name, [])
        # If not direct match, search by substring
        if not s_books:
            s_base = s_name.replace(" সিরিজ", "").replace(" কমিক্স", "").strip()
            s_books = [b for b in catalog if s_base in (b.get('series') or '') or s_base in (b.get('title') or '')]

        series_table_lines.append(f"| **[{s_name}]({s_name}/README.md)** | {len(s_books)} | [📂 Open Drive]({s_dlink}) | [Browse]({s_name}/README.md) |")

        # Create series subfolder & README
        s_path = series_dir / s_name
        s_path.mkdir(parents=True, exist_ok=True)

        with open(s_path / "README.md", "w", encoding="utf-8") as sf:
            sf.write("\n".join([
                f"# 📚 {s_name}",
                "",
                f"[🏠 Home](../../README.md) / [06_Series_and_Collections](../README.md) / **{s_name}**",
                "",
                f"> **📂 Google Drive Folder:** [Open in Google Drive]({s_dlink})  ",
                f"> **Total Titles:** **{len(s_books)} books**",
                "",
                "---",
                "",
                "## 📖 Series Volumes & Books",
                "",
                build_book_table(s_books),
                "",
                "---",
                "[⬅️ Back to Series & Collections](../README.md) | [🏠 Back to Library Home](../../README.md)"
            ]) + "\n")

    with open(series_dir / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join([
            "# 📚 06_Series_and_Collections (সিরিজ ও রচনাসমগ্র)",
            "",
            "[🏠 Home](../README.md) / **06_Series_and_Collections**",
            "",
            "> বিখ্যাত সাহিত্য, গোয়েন্দা, থ্রিলার ও ইসলামিক গ্রন্থ সিরিজ।",
            "",
            f"[📂 Open in Google Drive]({series_link}) | [📊 Master Spreadsheet]({excel_link})",
            "",
            "## Available Series",
            "",
            "\n".join(series_table_lines),
            "",
            "---",
            "[🏠 Back to Library Home](../README.md)"
        ]) + "\n")

    print(f"Generated 06_Series_and_Collections: {len(series_subfolders)} series.")

    # 5. REMOVE LEGACY SCATTERED DIRECTORIES
    legacy_dirs = [
        'Agriculture and Nature', 'Arts and Culture', 'Biography and Autobiography',
        'Business and Finance', 'Children and Young Adult', 'Computer and Technology',
        'Education and Academics', 'Engineering', 'Fiction', 'History',
        'Language and Linguistics', 'Law and Legal', 'Literature',
        'Magazines and Periodicals', 'Medicine and Health', 'Philosophy',
        'Politics and Government', 'Reference Books', 'Religion', 'Science',
        'Self Development', 'Social Science', 'Travel and Geography'
    ]

    print("Cleaning up legacy scattered folders...")
    for ld in legacy_dirs:
        lp = repo_dir / ld
        if lp.exists() and lp.is_dir():
            shutil.rmtree(lp, ignore_errors=True)
            print(f"Removed legacy folder: {ld}")

    print("Hierarchy successfully generated!")

if __name__ == '__main__':
    main()
