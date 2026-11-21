"""
Generate Bangladesh eBook Library Master Navigator & Placement Spreadsheet
Creates a high-performance, beautifully styled multi-sheet Excel workbook (.xlsx)
and UTF-8 BOM CSV for navigating all 12,060+ books and organizing them into folders.
"""

import csv
import json
import os
import re
import unicodedata
from pathlib import Path
from collections import defaultdict, Counter

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

def clean_str(val):
    if not isinstance(val, str):
        return val
    return ILLEGAL_CHARACTERS_RE.sub("", val).strip()

def format_size_mb(num_bytes):
    try:
        b = float(num_bytes)
        return round(b / (1024 * 1024), 2)
    except Exception:
        return 0.0

def main():
    repo_dir = Path(r'C:\Users\USER\.gemini\antigravity\scratch\Bangladesh-Biggest-eBook-Library')
    catalog_path = repo_dir / 'catalog' / 'master_catalog.json'
    drive_map_path = Path(r'C:\Users\USER\.gemini\antigravity\brain\59b32550-005f-4ecb-a6cd-d10a6f15189e\scratch\drive_folders_map.json')
    author_map_path = Path(r'C:\Users\USER\.gemini\antigravity\brain\59b32550-005f-4ecb-a6cd-d10a6f15189e\scratch\live_author_folders_map.json')

    xlsx_output_path = repo_dir / 'catalog' / 'Bangladesh_eBook_Library_Master_Navigator.xlsx'
    csv_output_path = repo_dir / 'catalog' / 'Bangladesh_eBook_Library_Master_Navigator.csv'

    print("Loading catalog and mappings...")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    with open(drive_map_path, 'r', encoding='utf-8') as f:
        folders_map = json.load(f)

    with open(author_map_path, 'r', encoding='utf-8') as f:
        author_map = json.load(f)

    print(f"Loaded {len(catalog)} books. Processing folder placement and links...")

    # Helper to resolve folder ID and link
    def get_folder_info(category, subcategory):
        folder_id = None
        folder_link = ""
        c_info = folders_map.get(category, {})
        
        # Check nested subfolders first (e.g. School/Class_05)
        if subcategory and 'nested_subfolders' in c_info and subcategory in c_info['nested_subfolders']:
            folder_id = c_info['nested_subfolders'][subcategory]
        elif subcategory and subcategory in c_info.get('subfolders', {}):
            folder_id = c_info['subfolders'][subcategory]
        elif subcategory and '/' in subcategory and subcategory.split('/')[0] in c_info.get('subfolders', {}):
            folder_id = c_info['subfolders'][subcategory.split('/')[0]]
        elif c_info.get('id'):
            folder_id = c_info['id']

        if folder_id:
            folder_link = f"https://drive.google.com/drive/folders/{folder_id}"
        return folder_id, folder_link

    # Analyze and enhance records
    enhanced_books = []
    category_counts = Counter()
    format_counts = Counter()
    status_counts = Counter()
    author_counts = Counter()
    total_bytes = 0

    for b in catalog:
        cat = clean_str(b.get('category', '08_Review_and_Unclassified'))
        sub = clean_str(b.get('subcategory', ''))
        title = clean_str(b.get('title', 'Untitled'))
        author = clean_str(b.get('author', 'Unknown'))
        fmt = clean_str(b.get('format', 'PDF'))
        size_bytes = b.get('file_size', 0)
        total_bytes += size_bytes
        file_id = clean_str(b.get('drive_file_id', ''))
        cur_path = clean_str(b.get('drive_path', ''))
        ver_status = clean_str(b.get('verification_status', 'Needs Review'))

        category_counts[cat] += 1
        format_counts[fmt] += 1
        status_counts[ver_status] += 1
        if author and author not in ('Unknown', 'NCTB', 'এনসিটিবি'):
            author_counts[author] += 1

        # Target full path
        if sub:
            target_path = f"{cat}/{sub}/"
        else:
            target_path = f"{cat}/"

        # Standardized proposed filename
        ext = fmt.lower()
        if author and author != 'Unknown':
            std_filename = f"{title} — {author}.{ext}"
        else:
            std_filename = f"{title}.{ext}"

        # Resolve target folder Drive info
        t_fid, t_link = get_folder_info(cat, sub)

        # Placement status & notes
        norm_cur = cur_path.replace('\\', '/')
        norm_target = target_path.replace('\\', '/')
        
        if cat == '08_Review_and_Unclassified':
            placement_status = "⚠️ Unclassified / Review Required"
            placement_action = "Move to 01_Bangla, 02_English, or 04_Religion_Books once verified."
        elif norm_cur.startswith(norm_target):
            placement_status = "✅ Correctly Placed in Folder"
            placement_action = "Already organized in designated target folder."
        elif norm_cur:
            placement_status = "📁 Move Required"
            placement_action = f"Move file from current folder to target: {target_path}"
        else:
            placement_status = "⚠️ Missing Current Path"
            placement_action = f"Place into target folder: {target_path}"

        # Author folder link
        auth_link = ""
        auth_fid = ""
        if author in author_map:
            auth_fid = author_map[author]['id']
            auth_link = author_map[author]['link']

        book_link = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""

        enhanced_books.append({
            'book_id': clean_str(b.get('book_id', '')),
            'title': title,
            'author': author,
            'language': clean_str(b.get('language', 'Bangla')),
            'category': cat,
            'subcategory': sub,
            'series': clean_str(b.get('series', '')),
            'publication_year': clean_str(str(b.get('publication_year', ''))),
            'format': fmt,
            'size_mb': format_size_mb(size_bytes),
            'size_bytes': size_bytes,
            'target_path': target_path,
            'current_path': cur_path,
            'placement_status': placement_status,
            'placement_action': placement_action,
            'target_folder_link': t_link,
            'book_drive_link': book_link,
            'author_folder_link': auth_link,
            'standardized_filename': clean_str(std_filename),
            'original_filename': clean_str(b.get('original_filename', '')),
            'verification_status': ver_status,
            'drive_file_id': file_id,
            'source_url': clean_str(b.get('source_url', '')),
        })

    # Arrange all books ascending by book name (title)
    enhanced_books.sort(key=lambda x: (
        unicodedata.normalize("NFC", str(x['title'])).strip().casefold(),
        unicodedata.normalize("NFC", str(x['author'])).strip().casefold(),
        str(x['drive_file_id'])
    ))

    print("Generating CSV export...")
    # Write CSV version (universal UTF-8 with BOM)
    csv_fields = [
        'Book ID', 'Title', 'Author', 'Language', 'Target Main Category',
        'Target Subcategory', 'Series / Collection', 'Publication Year', 'Format',
        'File Size (MB)', 'Target Folder Path', 'Current Drive Path',
        'Placement Status', 'Placement Instructions', 'Target Folder Drive URL',
        'Book Direct Drive URL', 'Author Folder Drive URL', 'Standardized Filename',
        'Original Filename', 'Verification Status', 'Google Drive File ID'
    ]

    with open(csv_output_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(csv_fields)
        for item in enhanced_books:
            w.writerow([
                item['book_id'], item['title'], item['author'], item['language'],
                item['category'], item['subcategory'], item['series'], item['publication_year'],
                item['format'], item['size_mb'], item['target_path'], item['current_path'],
                item['placement_status'], item['placement_action'], item['target_folder_link'],
                item['book_drive_link'], item['author_folder_link'], item['standardized_filename'],
                item['original_filename'], item['verification_status'], item['drive_file_id']
            ])

    print(f"Saved CSV: {csv_output_path}")

    # Build OpenPyXL Workbook
    print("Building OpenPyXL Workbook with 5 interactive sheets...")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet

    # Common Styles
    font_family = "Segoe UI"
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
    
    kpi_title_font = Font(name=font_family, size=10, color="595959", bold=True)
    kpi_val_font = Font(name=font_family, size=18, bold=True, color="1F4E79")
    kpi_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")

    zebra_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    border_thin = Border(
        left=Side(style='thin', color='E0E0E0'),
        right=Side(style='thin', color='E0E0E0'),
        top=Side(style='thin', color='E0E0E0'),
        bottom=Side(style='thin', color='E0E0E0')
    )
    link_font = Font(name=font_family, size=10, color="0563C1", underline="single")
    regular_font = Font(name=font_family, size=10)
    bold_font = Font(name=font_family, size=10, bold=True)

    # -------------------------------------------------------------
    # SHEET 1: 📊 Dashboard & Navigator
    # -------------------------------------------------------------
    ws_dash = wb.create_sheet(title="📊 Dashboard & Navigator")
    ws_dash.views.sheetView[0].showGridLines = True

    # Title Block
    ws_dash.merge_cells("A1:H1")
    ws_dash["A1"] = "📚 Bangladesh Biggest eBook Library — Master Navigator & Placement Workbench"
    ws_dash["A1"].font = Font(name=font_family, size=16, bold=True, color="1F4E79")
    ws_dash["A1"].alignment = Alignment(vertical="center")
    ws_dash.row_dimensions[1].height = 35

    ws_dash.merge_cells("A2:H2")
    ws_dash["A2"] = f"Complete catalog of {len(catalog):,} eBooks (sorted ascending by title) with direct Google Drive links, folder placement guidelines, and navigation indexes."
    ws_dash["A2"].font = Font(name=font_family, size=10, italic=True, color="595959")
    ws_dash.row_dimensions[2].height = 20

    # KPI Summary Cards (Row 4 to 5)
    kpis = [
        ("Total Books", f"{len(catalog):,}", "A", "B"),
        ("Storage Volume", f"{total_bytes / (1024**3):.1f} GB", "C", "D"),
        ("Unique Authors", f"{len(author_counts):,}", "E", "F"),
        ("Catalog Categories", f"{len(category_counts)} Folders", "G", "H"),
    ]

    for title, val, start_col, end_col in kpis:
        cell_t = f"{start_col}4"
        cell_v = f"{start_col}5"
        ws_dash.merge_cells(f"{start_col}4:{end_col}4")
        ws_dash.merge_cells(f"{start_col}5:{end_col}5")
        ws_dash[cell_t] = title.upper()
        ws_dash[cell_t].font = kpi_title_font
        ws_dash[cell_t].alignment = Alignment(horizontal="center", vertical="center")
        ws_dash[cell_t].fill = kpi_fill
        ws_dash[cell_v] = val
        ws_dash[cell_v].font = kpi_val_font
        ws_dash[cell_v].alignment = Alignment(horizontal="center", vertical="center")
        ws_dash[cell_v].fill = kpi_fill
        for row in range(4, 6):
            for col_letter in [start_col, end_col]:
                ws_dash[f"{col_letter}{row}"].border = border_thin

    ws_dash.row_dimensions[4].height = 20
    ws_dash.row_dimensions[5].height = 32

    # Section 1: Main Category Direct Navigation
    ws_dash["A7"] = "📂 Main Library Branches & Google Drive Links"
    ws_dash["A7"].font = Font(name=font_family, size=12, bold=True, color="1F4E79")
    ws_dash.row_dimensions[7].height = 25

    cat_headers = ["Category Folder", "Folder Name / Purpose", "Book Count", "Format Types", "Subfolders", "Direct Google Drive Link"]
    ws_dash.row_dimensions[8].height = 24
    for col_idx, h in enumerate(cat_headers, start=1):
        c = ws_dash.cell(row=8, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center" if col_idx in (3, 5) else "left", vertical="center")
        c.border = border_thin

    category_info = [
        ("01_Bangla_Books", "বাংলা সাহিত্য, উপন্যাস, গল্প, কবিতা, প্রবন্ধ, ইতিহাস, নাটক", category_counts["01_Bangla_Books"], "PDF, EPUB", 15),
        ("02_English_Books", "English Classic & Modern Literature, Fiction, Science, Non-Fiction", category_counts["02_English_Books"], "PDF, EPUB, MOBI", 8),
        ("03_Education_and_Textbooks", "NCTB School Textbooks (Class 1-10), HSC, Admission, Madrasa, BCS", category_counts["03_Education_and_Textbooks"], "PDF", 8),
        ("04_Religion_Books", "ইসলামিক, হিন্দু, বৌদ্ধ, খ্রিস্টান ও তুলনামূলক ধর্মগ্রন্থ (Islamic/Hindu/Buddhist/Christian)", category_counts["04_Religion_Books"], "PDF, EPUB", len(folders_map.get("04_Religion_Books", {}).get("subfolders", {}))),
        ("05_Authors_and_Scholars", "লেখক কেন্দ্রিক ফোল্ডার (বাংলা বর্ণমালা ও A-Z Index) — 1 Author = 1 Folder", category_counts["05_Authors_and_Scholars"], "PDF, EPUB, Shortcuts", len(author_map)),
        ("06_Series_and_Collections", "জনপ্রিয় সিরিজ (হিমু, মিসির আলি, ফেলুদা, ব্যোমকেশ, মাসুদ রানা)", category_counts["06_Series_and_Collections"], "PDF, EPUB, Shortcuts", len(folders_map.get("06_Series_and_Collections", {}).get("subfolders", {}))),
        ("07_Reference_and_Research", "Dictionaries, Encyclopedias, Research Papers, Journals", category_counts["07_Reference_and_Research"], "PDF", 5),
        ("08_Review_and_Unclassified", "Manual Review, Quarantine, Duplicates, Uncertain Authors", category_counts["08_Review_and_Unclassified"], "All Formats", len(folders_map.get("08_Review_and_Unclassified", {}).get("subfolders", {}))),
    ]

    for idx, (cat_id, desc, b_count, f_types, subs) in enumerate(category_info, start=9):
        ws_dash.row_dimensions[idx].height = 22
        fill = zebra_fill if idx % 2 == 0 else white_fill
        fid = folders_map.get(cat_id, {}).get('id', '')
        link = f"https://drive.google.com/drive/folders/{fid}" if fid else ""

        ws_dash.cell(row=idx, column=1, value=cat_id).font = bold_font
        ws_dash.cell(row=idx, column=2, value=desc).font = regular_font
        ws_dash.cell(row=idx, column=3, value=b_count).font = regular_font
        ws_dash.cell(row=idx, column=3).alignment = Alignment(horizontal="right")
        ws_dash.cell(row=idx, column=4, value=f_types).font = regular_font
        ws_dash.cell(row=idx, column=5, value=subs).font = regular_font
        ws_dash.cell(row=idx, column=5).alignment = Alignment(horizontal="center")
        
        c_link = ws_dash.cell(row=idx, column=6)
        if link:
            c_link.value = f'=HYPERLINK("{link}", "📂 Open in Google Drive")'
            c_link.font = link_font
        else:
            c_link.value = "—"
            c_link.font = regular_font

        for c_i in range(1, 7):
            ws_dash.cell(row=idx, column=c_i).fill = fill
            ws_dash.cell(row=idx, column=c_i).border = border_thin

    # Section 2: Instructions on How to Navigate & Put in Folders
    instr_row = 19
    ws_dash.cell(row=instr_row, column=1, value="📖 How to Use This Spreadsheet to Put Books into Folders").font = Font(name=font_family, size=12, bold=True, color="1F4E79")
    ws_dash.row_dimensions[instr_row].height = 25

    all_sheet_title = f"📚 All Books ({len(catalog):,})"
    instructions = [
        ("1. Find & Filter:", f"Go to the '{all_sheet_title}' tab (arranged ascending by Book Title). Use Excel's filter dropdowns on 'Title', 'Author', 'Category', or 'Subcategory' to locate books."),
        ("2. Check Placement Status:", "Look at the 'Placement Status' column. Green (✅) books are already organized in their target folder. Yellow/Orange (📁) books need moving."),
        ("3. Open Target Folder:", "Click the link in 'Target Folder Drive URL' to open the exact destination folder directly in Google Drive."),
        ("4. Move File in Drive:", "Click 'Book Direct Drive URL' to view the file. Use Google Drive's 'Move' (Shift + Z or right-click 'Organize' > 'Move') to move it to the target folder."),
        ("5. Review & Triage:", "Check the '⚠️ Review & Placement Tasks' tab for unclassified books or books with unknown authors that need manual assignment."),
        ("6. Author Shortcuts:", "In '05_Authors_and_Scholars', never create duplicate physical PDF copies! Always create Google Drive shortcuts referencing the primary book file."),
        ("7. Naming Conventions:", "Follow the clean format: 'বইয়ের নাম — লেখকের নাম.pdf' for Bangla and 'Book Title — Author Name.pdf' for English."),
    ]

    for idx, (step, detail) in enumerate(instructions, start=instr_row+1):
        ws_dash.row_dimensions[idx].height = 20
        ws_dash.cell(row=idx, column=1, value=step).font = bold_font
        ws_dash.cell(row=idx, column=2, value=detail).font = regular_font
        ws_dash.merge_cells(start_row=idx, start_column=2, end_row=idx, end_column=6)

    # Adjust Dashboard column widths
    dash_widths = [26, 45, 14, 16, 12, 26]
    for i, w in enumerate(dash_widths, start=1):
        ws_dash.column_dimensions[get_column_letter(i)].width = w

    # -------------------------------------------------------------
    # SHEET 2: 📚 All Books (Master Catalog)
    # -------------------------------------------------------------
    print(f"Generating Sheet 2: {all_sheet_title}...")
    ws_all = wb.create_sheet(title=all_sheet_title)
    ws_all.views.sheetView[0].showGridLines = True
    ws_all.freeze_panes = "A2"

    all_headers = [
        "Book ID", "Title", "Author", "Language", "Target Category",
        "Target Subfolder", "Series / Collection", "Year", "Format",
        "Size (MB)", "Target Folder Path", "Current Drive Path",
        "Placement Status", "Placement Instructions", "Target Folder Link",
        "Open Book Link", "Author Folder Link", "Standardized Filename",
        "Original Filename", "Verification Status", "Google Drive File ID"
    ]

    ws_all.row_dimensions[1].height = 28
    for col_idx, h in enumerate(all_headers, start=1):
        c = ws_all.cell(row=1, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center" if col_idx in (1, 4, 8, 9, 10, 13) else "left", vertical="center")
        c.border = border_thin

    for row_idx, item in enumerate(enhanced_books, start=2):
        fill = zebra_fill if row_idx % 2 == 0 else white_fill
        ws_all.row_dimensions[row_idx].height = 20

        # Book ID
        c = ws_all.cell(row=row_idx, column=1, value=item['book_id'])
        c.alignment = Alignment(horizontal="center")
        c.font = bold_font
        
        # Title, Author, Language, Category, Subcategory, Series, Year, Format
        ws_all.cell(row=row_idx, column=2, value=item['title']).font = regular_font
        ws_all.cell(row=row_idx, column=3, value=item['author']).font = regular_font
        ws_all.cell(row=row_idx, column=4, value=item['language']).font = regular_font
        ws_all.cell(row=row_idx, column=5, value=item['category']).font = regular_font
        ws_all.cell(row=row_idx, column=6, value=item['subcategory']).font = regular_font
        ws_all.cell(row=row_idx, column=7, value=item['series']).font = regular_font
        
        c_yr = ws_all.cell(row=row_idx, column=8, value=item['publication_year'])
        c_yr.alignment = Alignment(horizontal="center")
        c_yr.font = regular_font

        c_fmt = ws_all.cell(row=row_idx, column=9, value=item['format'])
        c_fmt.alignment = Alignment(horizontal="center")
        c_fmt.font = bold_font

        # Size MB (numeric)
        c_sz = ws_all.cell(row=row_idx, column=10, value=item['size_mb'])
        c_sz.number_format = '#,##0.00'
        c_sz.alignment = Alignment(horizontal="right")
        c_sz.font = regular_font

        # Paths & Placement
        ws_all.cell(row=row_idx, column=11, value=item['target_path']).font = regular_font
        ws_all.cell(row=row_idx, column=12, value=item['current_path']).font = regular_font
        ws_all.cell(row=row_idx, column=13, value=item['placement_status']).font = bold_font
        ws_all.cell(row=row_idx, column=14, value=item['placement_action']).font = regular_font

        # Links
        c_tlink = ws_all.cell(row=row_idx, column=15)
        if item['target_folder_link']:
            c_tlink.value = f'=HYPERLINK("{item["target_folder_link"]}", "📂 Open Folder")'
            c_tlink.font = link_font
        else:
            c_tlink.value = "—"
            c_tlink.font = regular_font

        c_blink = ws_all.cell(row=row_idx, column=16)
        if item['book_drive_link']:
            c_blink.value = f'=HYPERLINK("{item["book_drive_link"]}", "📖 Open File")'
            c_blink.font = link_font
        else:
            c_blink.value = "—"
            c_blink.font = regular_font

        c_alink = ws_all.cell(row=row_idx, column=17)
        if item['author_folder_link']:
            c_alink.value = f'=HYPERLINK("{item["author_folder_link"]}", "✍️ Author Folder")'
            c_alink.font = link_font
        else:
            c_alink.value = "—"
            c_alink.font = regular_font

        # Filenames & metadata
        ws_all.cell(row=row_idx, column=18, value=item['standardized_filename']).font = regular_font
        ws_all.cell(row=row_idx, column=19, value=item['original_filename']).font = regular_font
        ws_all.cell(row=row_idx, column=20, value=item['verification_status']).font = regular_font
        ws_all.cell(row=row_idx, column=21, value=item['drive_file_id']).font = regular_font

        for col_i in range(1, 22):
            c_obj = ws_all.cell(row=row_idx, column=col_i)
            if col_i not in (15, 16, 17) and isinstance(c_obj.value, str) and c_obj.value.startswith("="):
                c_obj.data_type = "s"
            c_obj.fill = fill
            c_obj.border = border_thin

    # Auto-filter
    ws_all.auto_filter.ref = f"A1:U{len(enhanced_books)+1}"

    # Column widths for All Books
    all_widths = [12, 35, 25, 12, 22, 22, 18, 8, 10, 12, 30, 32, 24, 38, 18, 16, 18, 38, 32, 22, 34]
    for i, w in enumerate(all_widths, start=1):
        ws_all.column_dimensions[get_column_letter(i)].width = w

    # -------------------------------------------------------------
    # SHEET 3: 📁 Folder Placement Guide
    # -------------------------------------------------------------
    print("Generating Sheet 3: 📁 Folder Placement Guide...")
    ws_guide = wb.create_sheet(title="📁 Folder Placement Guide")
    ws_guide.views.sheetView[0].showGridLines = True
    ws_guide.freeze_panes = "A2"

    guide_headers = ["Main Category", "Subfolder / Genre", "Full Folder Path", "Direct Google Drive Link", "Books Count", "Target Contents & Placement Rules"]
    ws_guide.row_dimensions[1].height = 28
    for col_idx, h in enumerate(guide_headers, start=1):
        c = ws_guide.cell(row=1, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center" if col_idx in (1, 5) else "left", vertical="center")
        c.border = border_thin

    # Tally books per full target path
    path_counts = Counter(b['target_path'] for b in enhanced_books)

    # Compile all folders from folders_map
    guide_rows = []
    for cat_name, cat_data in folders_map.items():
        if cat_name.startswith("00"):
            continue
        c_id = cat_data.get('id', '')
        # Main category entry
        main_path = f"{cat_name}/"
        guide_rows.append({
            'main': cat_name,
            'sub': "— [Root Category]",
            'path': main_path,
            'link': f"https://drive.google.com/drive/folders/{c_id}",
            'count': path_counts[main_path],
            'rules': f"Top-level directory for {cat_name}."
        })
        # Subfolders
        for sub_name, s_id in cat_data.get('subfolders', {}).items():
            sub_path = f"{cat_name}/{sub_name}/"
            guide_rows.append({
                'main': cat_name,
                'sub': sub_name,
                'path': sub_path,
                'link': f"https://drive.google.com/drive/folders/{s_id}",
                'count': path_counts[sub_path],
                'rules': f"Books categorized under {cat_name} > {sub_name}."
            })
        # Nested subfolders (e.g. School/Class_01)
        for nest_name, n_id in cat_data.get('nested_subfolders', {}).items():
            nest_path = f"{cat_name}/{nest_name}/"
            guide_rows.append({
                'main': cat_name,
                'sub': nest_name,
                'path': nest_path,
                'link': f"https://drive.google.com/drive/folders/{n_id}",
                'count': path_counts[nest_path],
                'rules': f"Textbooks for {nest_name}."
            })

    for row_idx, r in enumerate(guide_rows, start=2):
        ws_guide.row_dimensions[row_idx].height = 20
        fill = zebra_fill if row_idx % 2 == 0 else white_fill
        ws_guide.cell(row=row_idx, column=1, value=r['main']).font = bold_font
        ws_guide.cell(row=row_idx, column=2, value=r['sub']).font = regular_font
        ws_guide.cell(row=row_idx, column=3, value=r['path']).font = regular_font
        
        c_l = ws_guide.cell(row=row_idx, column=4)
        c_l.value = f'=HYPERLINK("{r["link"]}", "📂 Open Folder in Drive")'
        c_l.font = link_font

        c_c = ws_guide.cell(row=row_idx, column=5, value=r['count'])
        c_c.font = regular_font
        c_c.alignment = Alignment(horizontal="right")

        ws_guide.cell(row=row_idx, column=6, value=r['rules']).font = regular_font

        for c_i in range(1, 7):
            ws_guide.cell(row=row_idx, column=c_i).fill = fill
            ws_guide.cell(row=row_idx, column=c_i).border = border_thin

    ws_guide.auto_filter.ref = f"A1:F{len(guide_rows)+1}"
    guide_widths = [24, 28, 36, 26, 14, 45]
    for i, w in enumerate(guide_widths, start=1):
        ws_guide.column_dimensions[get_column_letter(i)].width = w

    # -------------------------------------------------------------
    # SHEET 4: ⚠️ Review & Placement Tasks
    # -------------------------------------------------------------
    print("Generating Sheet 4: ⚠️ Review & Placement Tasks...")
    ws_rev = wb.create_sheet(title="⚠️ Review & Placement Tasks")
    ws_rev.views.sheetView[0].showGridLines = True
    ws_rev.freeze_panes = "A2"

    rev_books = [b for b in enhanced_books if "Review" in b['placement_status'] or "Move" in b['placement_status'] or "review" in b['verification_status'].lower() or b['category'].startswith('08_')]
    print(f"Items needing placement review: {len(rev_books)}")

    ws_rev.row_dimensions[1].height = 28
    for col_idx, h in enumerate(all_headers, start=1):
        c = ws_rev.cell(row=1, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center" if col_idx in (1, 4, 8, 9, 10, 13) else "left", vertical="center")
        c.border = border_thin

    for row_idx, item in enumerate(rev_books, start=2):
        fill = zebra_fill if row_idx % 2 == 0 else white_fill
        ws_rev.row_dimensions[row_idx].height = 20

        ws_rev.cell(row=row_idx, column=1, value=item['book_id']).font = bold_font
        ws_rev.cell(row=row_idx, column=1).alignment = Alignment(horizontal="center")
        ws_rev.cell(row=row_idx, column=2, value=item['title']).font = regular_font
        ws_rev.cell(row=row_idx, column=3, value=item['author']).font = regular_font
        ws_rev.cell(row=row_idx, column=4, value=item['language']).font = regular_font
        ws_rev.cell(row=row_idx, column=5, value=item['category']).font = regular_font
        ws_rev.cell(row=row_idx, column=6, value=item['subcategory']).font = regular_font
        ws_rev.cell(row=row_idx, column=7, value=item['series']).font = regular_font
        
        c_yr = ws_rev.cell(row=row_idx, column=8, value=item['publication_year'])
        c_yr.alignment = Alignment(horizontal="center")
        c_yr.font = regular_font

        c_fmt = ws_rev.cell(row=row_idx, column=9, value=item['format'])
        c_fmt.alignment = Alignment(horizontal="center")
        c_fmt.font = bold_font

        c_sz = ws_rev.cell(row=row_idx, column=10, value=item['size_mb'])
        c_sz.number_format = '#,##0.00'
        c_sz.alignment = Alignment(horizontal="right")
        c_sz.font = regular_font

        ws_rev.cell(row=row_idx, column=11, value=item['target_path']).font = regular_font
        ws_rev.cell(row=row_idx, column=12, value=item['current_path']).font = regular_font
        ws_rev.cell(row=row_idx, column=13, value=item['placement_status']).font = bold_font
        ws_rev.cell(row=row_idx, column=14, value=item['placement_action']).font = regular_font

        c_tlink = ws_rev.cell(row=row_idx, column=15)
        if item['target_folder_link']:
            c_tlink.value = f'=HYPERLINK("{item["target_folder_link"]}", "📂 Open Target Folder")'
            c_tlink.font = link_font
        else:
            c_tlink.value = "—"
            c_tlink.font = regular_font

        c_blink = ws_rev.cell(row=row_idx, column=16)
        if item['book_drive_link']:
            c_blink.value = f'=HYPERLINK("{item["book_drive_link"]}", "📖 Open File")'
            c_blink.font = link_font
        else:
            c_blink.value = "—"
            c_blink.font = regular_font

        c_alink = ws_rev.cell(row=row_idx, column=17)
        if item['author_folder_link']:
            c_alink.value = f'=HYPERLINK("{item["author_folder_link"]}", "✍️ Author Folder")'
            c_alink.font = link_font
        else:
            c_alink.value = "—"
            c_alink.font = regular_font

        ws_rev.cell(row=row_idx, column=18, value=item['standardized_filename']).font = regular_font
        ws_rev.cell(row=row_idx, column=19, value=item['original_filename']).font = regular_font
        ws_rev.cell(row=row_idx, column=20, value=item['verification_status']).font = regular_font
        ws_rev.cell(row=row_idx, column=21, value=item['drive_file_id']).font = regular_font

        for col_i in range(1, 22):
            c_obj = ws_rev.cell(row=row_idx, column=col_i)
            if col_i not in (15, 16, 17) and isinstance(c_obj.value, str) and c_obj.value.startswith("="):
                c_obj.data_type = "s"
            c_obj.fill = fill
            c_obj.border = border_thin

    ws_rev.auto_filter.ref = f"A1:U{len(rev_books)+1}"
    for i, w in enumerate(all_widths, start=1):
        ws_rev.column_dimensions[get_column_letter(i)].width = w

    # -------------------------------------------------------------
    # SHEET 5: ✍️ Author Folders Directory
    # -------------------------------------------------------------
    print("Generating Sheet 5: ✍️ Author Folders Directory...")
    ws_auth = wb.create_sheet(title="✍️ Author Folders Directory")
    ws_auth.views.sheetView[0].showGridLines = True
    ws_auth.freeze_panes = "A2"

    auth_headers = ["#", "Author Name", "Language / Index Branch", "Total Books in Library", "Direct Google Drive Folder Link"]
    ws_auth.row_dimensions[1].height = 28
    for col_idx, h in enumerate(auth_headers, start=1):
        c = ws_auth.cell(row=1, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center" if col_idx in (1, 3, 4) else "left", vertical="center")
        c.border = border_thin

    sorted_authors = sorted(author_map.items(), key=lambda kv: (-author_counts.get(kv[0], 0), kv[0]))

    for idx, (auth_name, a_info) in enumerate(sorted_authors, start=2):
        ws_auth.row_dimensions[idx].height = 20
        fill = zebra_fill if idx % 2 == 0 else white_fill
        b_count = author_counts.get(auth_name, 0)

        c_num = ws_auth.cell(row=idx, column=1, value=idx-1)
        c_num.font = regular_font
        c_num.alignment = Alignment(horizontal="center")

        ws_auth.cell(row=idx, column=2, value=clean_str(auth_name)).font = bold_font
        ws_auth.cell(row=idx, column=3, value=f"{a_info['type']} Index").font = regular_font
        
        c_bc = ws_auth.cell(row=idx, column=4, value=b_count)
        c_bc.font = regular_font
        c_bc.alignment = Alignment(horizontal="right")

        c_al = ws_auth.cell(row=idx, column=5)
        c_al.value = f'=HYPERLINK("{a_info["link"]}", "✍️ Open Author Folder in Drive")'
        c_al.font = link_font

        for col_i in range(1, 6):
            ws_auth.cell(row=idx, column=col_i).fill = fill
            ws_auth.cell(row=idx, column=col_i).border = border_thin

    ws_auth.auto_filter.ref = f"A1:E{len(sorted_authors)+1}"
    auth_widths = [8, 32, 22, 22, 35]
    for i, w in enumerate(auth_widths, start=1):
        ws_auth.column_dimensions[get_column_letter(i)].width = w

    # Save Excel Workbook
    print(f"Saving workbook to {xlsx_output_path}...")
    wb.save(xlsx_output_path)
    print("Workbook successfully saved!")

if __name__ == '__main__':
    main()
