"""
Drive Organizer for Bangladesh eBook Library.
Generates proposed file-to-folder mapping and migration plan.
Enforces strict non-destructive policy and awaits user approval before moving any file.
"""

import os
import json
from typing import Dict, Any, List

def generate_organization_plan(catalog: List[Dict[str, Any]], base_dir: str) -> Dict[str, Any]:
    """
    Analyzes existing folder structure against proposed logical structure:
      00 - START HERE
      01 - MASTER BOOK CATALOG
      02 - BROWSE BY SUBJECT/
      03 - BROWSE BY LANGUAGE/
      04 - BROWSE BY AUTHOR/
      05 - BROWSE BY PUBLICATION YEAR/
      06 - COLLECTIONS AND DOWNLOADS/
      99 - ARCHIVE AND UNSORTED/
    """
    reusable_folders = set()
    proposed_mappings = []
    
    for b in catalog:
        current_folder = b.get("original_folder", "Unsorted")
        reusable_folders.add(current_folder)
        
        target_subject_path = f"02 - BROWSE BY SUBJECT/{b['subject']}/{b['subcategory']}"
        target_lang_path = f"03 - BROWSE BY LANGUAGE/{b['language']}"
        target_author_path = f"04 - BROWSE BY AUTHOR/{b['author'][:1] if b['author'] else 'Other'}/{b['author']}"
        
        proposed_mappings.append({
            "book_id": b["book_id"],
            "title": b["title"],
            "file_id": b["drive_file_id"],
            "current_path": current_folder,
            "primary_target_path": target_subject_path,
            "virtual_language_path": target_lang_path,
            "virtual_author_path": target_author_path,
            "action_type": "Retain Original / Link Catalog",
            "approval_status": "Awaiting User Approval"
        })
        
    plan = {
        "summary": {
            "total_files_analyzed": len(catalog),
            "reusable_existing_folders": len(reusable_folders),
            "proposed_new_structure": [
                "00 - START HERE",
                "01 - MASTER BOOK CATALOG",
                "02 - BROWSE BY SUBJECT/",
                "03 - BROWSE BY LANGUAGE/",
                "04 - BROWSE BY AUTHOR/",
                "05 - BROWSE BY PUBLICATION YEAR/",
                "06 - COLLECTIONS AND DOWNLOADS/",
                "99 - ARCHIVE AND UNSORTED/"
            ],
            "recommendation": "Preserve original file locations in Google Drive to keep existing external links intact; use Google Sheets Master Catalog and Web Search Explorer to provide Subject, Language, Author, and Year browsing without risk of file corruption or duplicate storage."
        },
        "sample_mappings": proposed_mappings[:50]
    }
    
    os.makedirs(os.path.join(base_dir, "reports"), exist_ok=True)
    plan_path = os.path.join(base_dir, "reports", "proposed_organization_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
        
    return plan
