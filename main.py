"""
Bangladesh Biggest eBook Library — Intelligent Drive Organizer & Manager
Unified Automation & CLI Interface
Commands:
  python main.py scan        - Recursive Drive inventory scanning
  python main.py extract     - Intelligent metadata extraction & normalization
  python main.py duplicates  - Multi-stage duplicate detection
  python main.py catalog     - Google Sheets Master Catalog generation & upload
  python main.py doc         - START HERE Google Doc generation & upload
  python main.py index       - Searchable JSON index generation
  python main.py plan        - Proposed reorganization plan generation
  python main.py verify      - Automated QA verification
  python main.py sync        - Full end-to-end sync across all stages
"""

import sys
import os
import argparse
import json
import yaml

from src.drive_scanner import build_inventory
from src.metadata_extractor import process_catalog
from src.duplicate_detector import detect_duplicates
from src.index_generator import build_search_index
from src.sheets_manager import create_master_spreadsheet, upload_catalog_to_drive
from src.docs_manager import generate_start_here_doc, upload_doc_to_drive
from src.drive_organizer import generate_organization_plan
from src.verifier import run_verification

def load_settings(base_dir: str):
    settings_file = os.path.join(base_dir, "config", "settings.yaml")
    if os.path.exists(settings_file):
        with open(settings_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "project": {
            "root_folder_id": "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
        }
    }

def cmd_scan(base_dir: str):
    print("▶ Running Drive Inventory Scan...")
    stats = build_inventory(base_dir)
    print(f"✓ Scan completed: {stats['total_files']:,} files, {stats['total_storage_formatted']} storage.")
    return stats

def cmd_extract(base_dir: str):
    print("▶ Running Metadata Extraction & Subject Classification...")
    catalog = process_catalog(base_dir)
    print(f"✓ Extraction completed: {len(catalog):,} books cataloged.")
    return catalog

def cmd_duplicates(base_dir: str):
    print("▶ Running Duplicate Detection...")
    cat_path = os.path.join(base_dir, "data", "book_catalog.json")
    if not os.path.exists(cat_path):
        catalog = process_catalog(base_dir)
    else:
        with open(cat_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    dups = detect_duplicates(catalog, base_dir)
    print(f"✓ Duplicate check completed: {len(dups):,} duplicate candidates identified.")
    return dups

def cmd_index(base_dir: str):
    print("▶ Building Search Index...")
    cat_path = os.path.join(base_dir, "data", "book_catalog.json")
    if not os.path.exists(cat_path):
        catalog = process_catalog(base_dir)
    else:
        with open(cat_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    idx = build_search_index(catalog, base_dir)
    print(f"✓ Search index built: {len(idx['books']):,} books indexed across {len(idx['tokens']):,} tokens.")
    return idx

def cmd_catalog(base_dir: str, upload: bool = True):
    print("▶ Generating Google Sheets Master Catalog...")
    cat_path = os.path.join(base_dir, "data", "book_catalog.json")
    if not os.path.exists(cat_path):
        catalog = process_catalog(base_dir)
    else:
        with open(cat_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
            
    dup_path = os.path.join(base_dir, "data", "duplicate_report.json")
    if not os.path.exists(dup_path):
        dups = detect_duplicates(catalog, base_dir)
    else:
        with open(dup_path, "r", encoding="utf-8") as f:
            dups = json.load(f)
            
    xlsx_path = create_master_spreadsheet(catalog, dups, base_dir)
    print(f"✓ Master spreadsheet saved locally: {xlsx_path}")
    
    if upload:
        settings = load_settings(base_dir)
        root_id = settings.get("project", {}).get("root_folder_id", "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq")
        print(f"▶ Uploading Master Catalog to Google Drive folder {root_id}...")
        drive_res = upload_catalog_to_drive(xlsx_path, root_id)
        print(f"✓ Google Sheets Master Catalog Live at: {drive_res['sheet_url']}")
        return drive_res
    return {"sheet_path": xlsx_path}

def cmd_doc(base_dir: str, sheet_url: str = "", upload: bool = True):
    print("▶ Generating '00 - START HERE' Google Doc...")
    settings = load_settings(base_dir)
    root_id = settings.get("project", {}).get("root_folder_id", "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq")
    
    html_path = generate_start_here_doc(sheet_url or "https://docs.google.com", base_dir)
    print(f"✓ Document prepared locally: {html_path}")
    
    if upload:
        print(f"▶ Uploading START HERE document to Google Drive folder {root_id}...")
        doc_res = upload_doc_to_drive(html_path, root_id)
        print(f"✓ Google Doc Live at: {doc_res['doc_url']}")
        return doc_res
    return {"doc_path": html_path}

def cmd_plan(base_dir: str):
    print("▶ Generating Reorganization Plan...")
    cat_path = os.path.join(base_dir, "data", "book_catalog.json")
    if not os.path.exists(cat_path):
        catalog = process_catalog(base_dir)
    else:
        with open(cat_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    plan = generate_organization_plan(catalog, base_dir)
    print("✓ Proposed plan generated. All original files preserved; awaiting user review.")
    return plan

def cmd_verify(base_dir: str, sheet_url: str = "", doc_url: str = ""):
    print("▶ Running Quality Assurance Verification...")
    rep = run_verification(base_dir, sheet_url, doc_url)
    print(f"✓ Verification {rep['overall_status']}: {rep['passed_checks']}/{rep['total_checks']} checks passed.")
    return rep

def cmd_sync(base_dir: str):
    print("=== STARTING FULL RE-SYNCHRONIZATION ===")
    cmd_scan(base_dir)
    catalog = cmd_extract(base_dir)
    dups = cmd_duplicates(base_dir)
    cmd_index(base_dir)
    cmd_plan(base_dir)
    sheet_info = cmd_catalog(base_dir, upload=True)
    doc_info = cmd_doc(base_dir, sheet_url=sheet_info.get("sheet_url", ""), upload=True)
    cmd_verify(base_dir, sheet_url=sheet_info.get("sheet_url", ""), doc_url=doc_info.get("doc_url", ""))
    print("=== FULL SYNCHRONIZATION COMPLETE ===")

def main():
    parser = argparse.ArgumentParser(description="Bangladesh eBook Library Manager")
    parser.add_argument("command", choices=["scan", "extract", "duplicates", "index", "catalog", "doc", "plan", "verify", "sync"], help="Action to execute")
    parser.add_argument("--no-upload", action="store_true", help="Skip Google Drive upload")
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if args.command == "scan":
        cmd_scan(base_dir)
    elif args.command == "extract":
        cmd_extract(base_dir)
    elif args.command == "duplicates":
        cmd_duplicates(base_dir)
    elif args.command == "index":
        cmd_index(base_dir)
    elif args.command == "catalog":
        cmd_catalog(base_dir, upload=not args.no_upload)
    elif args.command == "doc":
        cmd_doc(base_dir, upload=not args.no_upload)
    elif args.command == "plan":
        cmd_plan(base_dir)
    elif args.command == "verify":
        cmd_verify(base_dir)
    elif args.command == "sync":
        cmd_sync(base_dir)

if __name__ == "__main__":
    main()
