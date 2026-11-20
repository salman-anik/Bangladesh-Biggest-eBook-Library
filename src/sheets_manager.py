"""
Google Sheets Master Catalog Manager for Bangladesh eBook Library.
Creates a professional, formatted 8-worksheet Excel spreadsheet
and uploads it to Google Drive as a native Google Spreadsheet.
"""

import os
import subprocess
import json
from collections import Counter, defaultdict
from typing import Dict, Any, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
HEADER_FONT = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
REGULAR_FONT = Font(name="Segoe UI", size=10)
LINK_FONT = Font(name="Segoe UI", size=10, color="0000EE", underline="single")
THIN_BORDER = Border(
    left=Side(style='thin', color='E2E8F0'),
    right=Side(style='thin', color='E2E8F0'),
    top=Side(style='thin', color='E2E8F0'),
    bottom=Side(style='thin', color='E2E8F0')
)

def style_header(ws, col_count: int):
    """Styles the header row of a worksheet."""
    ws.row_dimensions[1].height = 26
    for col in range(1, col_count + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

def auto_fit_columns(ws, max_cols: int, max_len_cap: int = 45):
    """Auto fits column widths based on content."""
    for col in range(1, max_cols + 1):
        col_letter = get_column_letter(col)
        max_len = 0
        for row in range(1, min(ws.max_row + 1, 150)):  # sample up to 150 rows
            val = ws.cell(row=row, column=col).value
            if val:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[col_letter].width = min(max_len_cap, max(max_len + 3, 12))

def create_master_spreadsheet(catalog: List[Dict[str, Any]], duplicates: List[Dict[str, Any]], base_dir: str) -> str:
    """
    Builds the complete 8-worksheet Excel file.
    Returns local file path.
    """
    wb = openpyxl.Workbook()
    
    # ----------------------------------------------------
    # SHEET 1: ALL BOOKS
    # ----------------------------------------------------
    ws1 = wb.active
    ws1.title = "ALL BOOKS"
    headers1 = [
        "Book ID", "Title", "Alternative Title", "Author", "Co-Authors", "Editor",
        "Translator", "Publisher", "Publication Year", "Edition", "ISBN-10", "ISBN-13",
        "Language", "Subject", "Subcategory", "Keywords", "Description", "Pages",
        "Format", "File Size", "Original Filename", "Original Folder", "Drive File ID",
        "Direct Drive Link", "Metadata Confidence", "Review Status", "Duplicate Status"
    ]
    ws1.append(headers1)
    
    # Write catalog rows
    for b in catalog:
        size_mb = f"{b['file_size_bytes'] / (1024*1024):.2f} MB" if b['file_size_bytes'] else "0 MB"
        row = [
            b["book_id"],
            b["title"],
            b.get("alt_title", ""),
            b["author"],
            b.get("co_authors", ""),
            b.get("editor", ""),
            b.get("translator", ""),
            b.get("publisher", ""),
            b["publication_year"],
            b.get("edition", "1st Edition"),
            b.get("isbn_10", ""),
            b.get("isbn_13", ""),
            b["language"],
            b["subject"],
            b["subcategory"],
            b.get("keywords", ""),
            b.get("description", ""),
            b.get("pages", "Unknown"),
            b["format"],
            size_mb,
            b.get("original_filename", ""),
            b.get("original_folder", ""),
            b["drive_file_id"],
            b["direct_drive_link"],
            b["metadata_confidence"],
            b["review_status"],
            b["duplicate_status"]
        ]
        ws1.append(row)
        
    style_header(ws1, len(headers1))
    auto_fit_columns(ws1, len(headers1))
    
    # ----------------------------------------------------
    # SHEET 2: SUBJECT INDEX
    # ----------------------------------------------------
    ws2 = wb.create_sheet("SUBJECT INDEX")
    headers2 = ["Subject", "Subcategory", "Number of Books", "Browse Link"]
    ws2.append(headers2)
    
    sub_counter = Counter((b["subject"], b["subcategory"]) for b in catalog)
    for (subj, subcat), cnt in sorted(sub_counter.items()):
        ws2.append([
            subj,
            subcat,
            cnt,
            f"https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
        ])
    style_header(ws2, len(headers2))
    auto_fit_columns(ws2, len(headers2))
    
    # ----------------------------------------------------
    # SHEET 3: LANGUAGE INDEX
    # ----------------------------------------------------
    ws3 = wb.create_sheet("LANGUAGE INDEX")
    headers3 = ["Language", "Number of Books", "Browse Link"]
    ws3.append(headers3)
    
    lang_counter = Counter(b["language"] for b in catalog)
    for lang, cnt in sorted(lang_counter.items(), key=lambda x: -x[1]):
        ws3.append([
            lang,
            cnt,
            "https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
        ])
    style_header(ws3, len(headers3))
    auto_fit_columns(ws3, len(headers3))
    
    # ----------------------------------------------------
    # SHEET 4: AUTHOR INDEX
    # ----------------------------------------------------
    ws4 = wb.create_sheet("AUTHOR INDEX")
    headers4 = ["Author", "Number of Books", "Sample Titles", "Browse Links"]
    ws4.append(headers4)
    
    author_books = defaultdict(list)
    for b in catalog:
        author_books[b["author"]].append(b)
        
    for auth, b_list in sorted(author_books.items(), key=lambda x: -len(x[1]))[:500]:
        sample_titles = ", ".join([bk["title"] for bk in b_list[:3]])
        ws4.append([
            auth,
            len(b_list),
            sample_titles,
            b_list[0]["direct_drive_link"]
        ])
    style_header(ws4, len(headers4))
    auto_fit_columns(ws4, len(headers4))
    
    # ----------------------------------------------------
    # SHEET 5: PUBLICATION YEAR INDEX
    # ----------------------------------------------------
    ws5 = wb.create_sheet("PUBLICATION YEAR INDEX")
    headers5 = ["Publication Year", "Number of Books", "Sample Book Link"]
    ws5.append(headers5)
    
    year_counter = Counter(b["publication_year"] for b in catalog)
    for yr, cnt in sorted(year_counter.items(), key=lambda x: str(x[0]), reverse=True):
        sample = next((b for b in catalog if b["publication_year"] == yr), None)
        ws5.append([
            yr,
            cnt,
            sample["direct_drive_link"] if sample else ""
        ])
    style_header(ws5, len(headers5))
    auto_fit_columns(ws5, len(headers5))
    
    # ----------------------------------------------------
    # SHEET 6: DUPLICATE REPORT
    # ----------------------------------------------------
    ws6 = wb.create_sheet("DUPLICATE REPORT")
    headers6 = [
        "Candidate Book ID", "Candidate Title", "Candidate Author", "Candidate Folder",
        "Candidate Link", "Original Book ID", "Original Title", "Match Type",
        "Similarity Score", "Reason", "Recommended Action"
    ]
    ws6.append(headers6)
    for d in duplicates[:500]:
        ws6.append([
            d["candidate_book_id"],
            d["candidate_title"],
            d["candidate_author"],
            d["candidate_folder"],
            d["candidate_drive_link"],
            d["original_book_id"],
            d["original_title"],
            d["match_type"],
            d["similarity_score"],
            d["reason"],
            d["recommended_action"]
        ])
    style_header(ws6, len(headers6))
    auto_fit_columns(ws6, len(headers6))
    
    # ----------------------------------------------------
    # SHEET 7: NEEDS REVIEW
    # ----------------------------------------------------
    ws7 = wb.create_sheet("NEEDS REVIEW")
    headers7 = [
        "Book ID", "Title", "Author", "Language", "Subject", "Subcategory",
        "Drive File ID", "Direct Drive Link", "Metadata Confidence", "Review Status"
    ]
    ws7.append(headers7)
    needs_review_count = 0
    for b in catalog:
        if b["review_status"] == "Needs Review" or b["metadata_confidence"] < 0.85:
            ws7.append([
                b["book_id"],
                b["title"],
                b["author"],
                b["language"],
                b["subject"],
                b["subcategory"],
                b["drive_file_id"],
                b["direct_drive_link"],
                b["metadata_confidence"],
                b["review_status"]
            ])
            needs_review_count += 1
            if needs_review_count >= 1000:
                break
    style_header(ws7, len(headers7))
    auto_fit_columns(ws7, len(headers7))
    
    # ----------------------------------------------------
    # SHEET 8: LIBRARY STATISTICS
    # ----------------------------------------------------
    ws8 = wb.create_sheet("LIBRARY STATISTICS")
    headers8 = ["Metric Name", "Metric Value", "Notes & Details"]
    ws8.append(headers8)
    
    total_books = len(catalog)
    total_size = sum(b.get("file_size_bytes", 0) for b in catalog)
    total_size_gb = f"{total_size / (1024**3):.2f} GB"
    
    metrics = [
        ("Total Books in Library", total_books, "Catalogued items across 25 subjects"),
        ("Total Storage Utilized", total_size_gb, "Total cumulative bytes"),
        ("Total Primary Subjects", len(set(b['subject'] for b in catalog)), "Canonical taxonomy subjects"),
        ("Total Subcategories", len(set(b['subcategory'] for b in catalog)), "Subject sub-classifications"),
        ("Total Unique Authors", len(author_books), "Unique authors or collections"),
        ("Total Languages", len(lang_counter), "Bangla, English, Arabic, etc."),
        ("Bangla Books", lang_counter.get("Bangla", 0), "Bangla literature, textbooks, and works"),
        ("English Books", lang_counter.get("English", 0), "English references and international titles"),
        ("Arabic Books", lang_counter.get("Arabic", 0), "Islamic references and grammar books"),
        ("Duplicate Candidates", len(duplicates), "Flagged for manual review, preserved safely"),
        ("Metadata Records Needing Review", needs_review_count, "Incomplete bibliographic fields"),
        ("Platform", "Google Drive + GitHub + Next.js", "Accessible worldwide with direct Drive URLs")
    ]
    for m in metrics:
        ws8.append(list(m))
    style_header(ws8, len(headers8))
    auto_fit_columns(ws8, len(headers8))
    
    # Save workbook
    os.makedirs(os.path.join(base_dir, "data"), exist_ok=True)
    out_xlsx = os.path.join(base_dir, "data", "Bangladesh_eBook_Library_Master_Catalog.xlsx")
    wb.save(out_xlsx)
    return out_xlsx

def upload_catalog_to_drive(xlsx_path: str, root_folder_id: str) -> Dict[str, str]:
    """
    Uploads the master Excel file to Google Drive and converts to Google Spreadsheet.
    """
    cmd = [
        "gdrive", "mutate", "upload", xlsx_path,
        "--parent", root_folder_id,
        "--mime-type", "application/vnd.google-apps.spreadsheet",
        "--json"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    out = res.stdout + res.stderr
    print("Drive upload response:", out)
    
    # Extract file ID
    import re
    match = re.search(r'\(ID:\s*([a-zA-Z0-9_\-]+)\)', out)
    if match:
        sheet_id = match.group(1)
        return {
            "sheet_id": sheet_id,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        }
    return {
        "sheet_id": "",
        "sheet_url": ""
    }
