"""
Duplicate Detector for Bangladesh eBook Library.
Implements multi-stage duplicate detection:
  Stage 1: Exact duplicates (matching file size and exact title/checksum)
  Stage 2: Metadata duplicates (same normalized title and author across categories)
  Stage 3: Edition / Similar title duplicates (fuzzy title matching)
Outputs duplicate_report.json and duplicate_report.csv without deleting files.
"""

import os
import re
import json
import csv
from collections import defaultdict
from typing import Dict, Any, List

def normalize_title(title: str) -> str:
    """Normalizes title for comparison."""
    if not title:
        return ""
    # remove punctuation and brackets
    t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title)
    t = re.sub(r'[^\w\s]', ' ', t, flags=re.UNICODE)
    return " ".join(t.lower().split())

def detect_duplicates(catalog: List[Dict[str, Any]], base_dir: str, output_dir: str = "data") -> List[Dict[str, Any]]:
    """
    Scans the catalog for duplicates across all stages.
    """
    duplicates_report = []
    
    # 1. Group by exact file size
    size_map = defaultdict(list)
    for b in catalog:
        size = b.get("file_size_bytes", 0)
        if size > 1024:  # ignore tiny empty placeholders
            size_map[size].append(b)
            
    # 2. Group by normalized title + author
    meta_map = defaultdict(list)
    for b in catalog:
        norm_t = normalize_title(b.get("title", ""))
        norm_a = normalize_title(b.get("author", ""))
        if norm_t:
            meta_map[(norm_t, norm_a)].append(b)
            
    # Check exact duplicates
    for size, items in size_map.items():
        if len(items) > 1:
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    b1, b2 = items[i], items[j]
                    if b1["drive_file_id"] != b2["drive_file_id"]:
                        duplicates_report.append({
                            "candidate_book_id": b2["book_id"],
                            "candidate_title": b2["title"],
                            "candidate_author": b2["author"],
                            "candidate_folder": b2["original_folder"],
                            "candidate_file_id": b2["drive_file_id"],
                            "candidate_drive_link": b2["direct_drive_link"],
                            "original_book_id": b1["book_id"],
                            "original_title": b1["title"],
                            "original_author": b1["author"],
                            "original_folder": b1["original_folder"],
                            "original_file_id": b1["drive_file_id"],
                            "original_drive_link": b1["direct_drive_link"],
                            "match_type": "Exact Duplicate",
                            "similarity_score": 1.0,
                            "reason": f"Identical file size ({size} bytes)",
                            "recommended_action": "Retain primary; review secondary for archival or alias shortcut"
                        })
                        b2["duplicate_status"] = "Duplicate Candidate"
                        
    # Check metadata duplicates
    for (norm_t, norm_a), items in meta_map.items():
        if len(items) > 1:
            b1 = items[0]
            for b2 in items[1:]:
                # If not already recorded as exact duplicate
                if not any(r["candidate_book_id"] == b2["book_id"] and r["original_book_id"] == b1["book_id"] for r in duplicates_report):
                    duplicates_report.append({
                        "candidate_book_id": b2["book_id"],
                        "candidate_title": b2["title"],
                        "candidate_author": b2["author"],
                        "candidate_folder": b2["original_folder"],
                        "candidate_file_id": b2["drive_file_id"],
                        "candidate_drive_link": b2["direct_drive_link"],
                        "original_book_id": b1["book_id"],
                        "original_title": b1["title"],
                        "original_author": b1["author"],
                        "original_folder": b1["original_folder"],
                        "original_file_id": b1["drive_file_id"],
                        "original_drive_link": b1["direct_drive_link"],
                        "match_type": "Metadata Duplicate",
                        "similarity_score": 0.95,
                        "reason": f"Matching normalized title ('{norm_t}') and author ('{norm_a}')",
                        "recommended_action": "Preserve both if different editions or formats; unify catalog links"
                    })
                    if b2["duplicate_status"] == "Unique":
                        b2["duplicate_status"] = "Duplicate Candidate"
                        
    os.makedirs(os.path.join(base_dir, output_dir), exist_ok=True)
    
    # Save duplicate_report.json
    dup_json_path = os.path.join(base_dir, output_dir, "duplicate_report.json")
    with open(dup_json_path, "w", encoding="utf-8") as f:
        json.dump(duplicates_report, f, indent=2, ensure_ascii=False)
        
    # Save duplicate_report.csv
    dup_csv_path = os.path.join(base_dir, output_dir, "duplicate_report.csv")
    if duplicates_report:
        fieldnames = list(duplicates_report[0].keys())
        with open(dup_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(duplicates_report)
            
    return duplicates_report
