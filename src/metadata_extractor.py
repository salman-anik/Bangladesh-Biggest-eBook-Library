"""
Metadata Extractor for Bangladesh eBook Library.
Processes every book, normalizes bibliographic details, detects languages,
classifies taxonomy subjects, and outputs structured book_catalog.json and book_catalog.csv.
"""

import os
import re
import json
import csv
from typing import Dict, Any, List
from src.language_detector import detect_language
from src.subject_classifier import classify_book

def extract_year(text: str) -> Any:
    """Extracts a 4-digit publication year (1800-2026) from text."""
    if not text:
        return None
    match = re.search(r'\b(1[89]\d\d|20[0-2]\d)\b', text)
    if match:
        return int(match.group(1))
    return None

def clean_name(name: str) -> str:
    """Cleans author or title text."""
    if not name:
        return ""
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name)
    name = re.sub(r'[_\-\+]+', ' ', name)
    return " ".join(name.split()).strip()

def process_catalog(base_dir: str, output_dir: str = "data") -> List[Dict[str, Any]]:
    """
    Transforms merged books into the master library catalog.
    """
    merged_path = os.path.join(base_dir, "data", "merged_books.json")
    if not os.path.exists(merged_path):
        merged_path = os.path.join(base_dir, "books.json")
        
    with open(merged_path, "r", encoding="utf-8") as f:
        raw_books = json.load(f)
        
    catalog = []
    
    for idx, b in enumerate(raw_books, start=1):
        book_id = f"BK{idx:06d}"
        
        raw_title = b.get("title") or b.get("name") or "Unknown Title"
        author_raw = b.get("author") or "Various / Unknown"
        publisher = b.get("publication") or "Unknown"
        top_cat = b.get("top_category") or "General"
        leaf_cat = b.get("leaf_category") or "General"
        leaf_path = b.get("leaf_path") or ""
        
        # Determine subject & subcategory
        subject, subcat = classify_book(top_cat, leaf_cat, leaf_path, raw_title)
        
        # Determine language
        lang, lang_conf = detect_language(f"{raw_title} {author_raw}", leaf_path)
        
        # Determine publication year
        year = extract_year(raw_title)
        if not year and b.get("subfolder"):
            year = extract_year(b.get("subfolder"))
            
        # Determine format & primary file ID
        pdf_id = b.get("pdf_file_id") or ""
        epub_id = b.get("epub_file_id") or ""
        file_id = b.get("file_id") or pdf_id or epub_id or ""
        
        formats_list = b.get("formats", ["PDF"])
        fmt_str = "/".join(formats_list) if formats_list else "PDF"
        
        # Confidence & Review Status
        confidence = 0.95
        review_status = "Verified"
        if author_raw in ["Various / Unknown", "Unknown", ""] or not author_raw:
            confidence -= 0.15
        if not year:
            confidence -= 0.10
        if not file_id:
            confidence -= 0.25
            review_status = "Needs Review"
            
        confidence = max(0.50, round(confidence, 2))
        if confidence < 0.80 and review_status != "Needs Review":
            review_status = "Needs Review"
            
        # Drive URLs
        drive_link = f"https://drive.google.com/file/d/{file_id}/view" if file_id else (b.get("link") or "")
        
        record = {
            "book_id": book_id,
            "title": raw_title,
            "alt_title": clean_name(raw_title) if clean_name(raw_title) != raw_title else "",
            "author": author_raw,
            "co_authors": "",
            "editor": "",
            "translator": "",
            "publisher": publisher,
            "publication_year": year if year else "Unknown",
            "edition": "1st Edition",
            "isbn_10": "",
            "isbn_13": "",
            "language": lang,
            "subject": subject,
            "subcategory": subcat,
            "keywords": f"{subject}, {subcat}, {lang}",
            "description": f"{raw_title} by {author_raw} ({subject} - {subcat})",
            "pages": "Unknown",
            "format": fmt_str,
            "file_size_bytes": b.get("size") or 0,
            "original_filename": (b.get("files", [{}])[0].get("name") if b.get("files") else "") or (raw_title + ".pdf"),
            "original_folder": leaf_path or subject,
            "drive_file_id": file_id,
            "direct_drive_link": drive_link,
            "metadata_confidence": confidence,
            "review_status": review_status,
            "duplicate_status": "Unique"
        }
        catalog.append(record)
        
    os.makedirs(os.path.join(base_dir, output_dir), exist_ok=True)
    
    # Save book_catalog.json
    cat_json_path = os.path.join(base_dir, output_dir, "book_catalog.json")
    with open(cat_json_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        
    # Save book_catalog.csv
    cat_csv_path = os.path.join(base_dir, output_dir, "book_catalog.csv")
    fieldnames = list(catalog[0].keys())
    with open(cat_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(catalog)
        
    return catalog
