import csv
import json
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, os.path.dirname(__file__))
from reorg_lib import gdrive_ls, log_op, run_gdrive

ROOT = Path(r'C:\Users\USER\.gemini\antigravity\scratch\Bangladesh-Biggest-eBook-Library')
DATA = ROOT / 'data'
REPORTS = ROOT / 'reports'

LIBRARY_ROOT_ID = '1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq'
ENGLISH_ROOT_ID = '1T250ptAUwZnv80QxH34qFApKhRZ_s4d9'
QAWMI_ROOT_ID = '1oACGk9Yf70kBJGRdsNMVPBkFLhZNJ02O'
COVERS_FOLDER_ID = '1WRjc_Jm-cx1MPUcqoF87n_bwRh7z9u57'
QAWMI_XLSX_ID = '1B-Or8excxaX7QO-TYNHjZkYRpWC6ajyY'
QAWMI_CSV_ID = '1UYmzZqXmp89WNBrgLEMll6mPTIKvUC3J'
MASTER_NAV_ID = '1PBHQfSIQvGCYinQkk6XvtjuGgixbHWbM'

LEVEL_EQ_MAP = {
    'Ibtidaiyah': ('Primary (Class 1–5)', 'ইবতিদায়িয়্যাহ / প্রাথমিক স্তর'),
    'Mutawassitah': ('Junior Secondary (Class 6–8)', 'মুতাওয়াসসিতাহ / নিম্ন মাধ্যমিক'),
    'Sanabiyah': ('Secondary & Higher Secondary (SSC/HSC)', 'সানাবিয়্যাহ (আম্মাহ ও উলইয়া)'),
    'Fazilat': ("Bachelor's Level (Approx.)", 'ফযীলত / স্নাতক সমমান'),
    'Takmil (Dawra-e-Hadith)': ("Master's Level (Approx.)", 'তাকমীল / দাওরায়ে হাদীস'),
    'Takhassus': ('Post-Graduate Specialization', 'তাখাসসুস / উচ্চতর গবেষণা'),
    'Common & Reference Books': ('Multi-Level Shared Reference', 'সকল স্তরের সহায়ক ও রেফারেন্স'),
    'Review & Unclassified (Qawmi)': ('Level Review Needed', 'পর্যালোচনা ও অশ্রেণীবদ্ধ'),
}

def verify_english_books():
    print("=== VERIFYING ENGLISH BOOKS & ROOT ARCHITECTURE ===")
    root_items = gdrive_ls(LIBRARY_ROOT_ID)
    root_folders = sorted([it['name'] for it in root_items if it.get('mimeType') == 'application/vnd.google-apps.folder'])
    print("Root top-level folders:", root_folders)

    eng_subs = gdrive_ls(ENGLISH_ROOT_ID)
    total_eng = 0
    for s in sorted([x for x in eng_subs if x.get('mimeType') == 'application/vnd.google-apps.folder'], key=lambda x: x['name']):
        items = gdrive_ls(s['id'])
        print(f"  English Books / {s['name']:35s} : {len(items)} files")
        total_eng += len(items)
    print(f"Total remaining in English Books/: {total_eng}")
    return root_folders, total_eng

def update_qawmi_catalog_and_verify():
    print("\n=== VERIFYING QAWMI MADRASA & UPDATING SPREADSHEETS ===")
    sub_map = json.loads((DATA / 'qawmi_level_subject_folders.json').read_text(encoding='utf-8'))
    covers = gdrive_ls(COVERS_FOLDER_ID)
    covers_by_stem = {Path(c['name']).stem: c['id'] for c in covers if c.get('mimeType') != 'application/vnd.google-apps.folder'}

    q_top = gdrive_ls(QAWMI_ROOT_ID)
    print("Qawmi Madrasa top-level items:", sorted([x['name'] for x in q_top]))

    # Identify leaf subject folders inside sub_map (those with '/')
    leaf_items = [(p, fid) for p, fid in sub_map.items() if '/' in p]

    def scan_one(kv):
        p, fid = kv
        return p, fid, gdrive_ls(fid)

    with ThreadPoolExecutor(max_workers=8) as ex:
        scanned = list(ex.map(scan_one, sorted(leaf_items)))

    book_rows = []
    map_rows = []
    total_books = 0
    qcat = json.loads((DATA / 'qawmimadrasa_catalog.json').read_text(encoding='utf-8'))
    cat_by_title = {it.get('title', ''): it for it in qcat}

    for path_str, fid, items in scanned:
        files = [it for it in items if it.get('mimeType') != 'application/vnd.google-apps.folder']
        if len(files) == 0:
            continue
        total_books += len(files)
        lvl, sub = path_str.split('/', 1)
        gen_eq, bn_stage = LEVEL_EQ_MAP.get(lvl, ('', ''))
        map_rows.append([lvl, sub, gen_eq, bn_stage, path_str, len(files), f"https://drive.google.com/drive/folders/{fid}"])
        print(f"  {path_str:68s} : {len(files)} books")

        for f in sorted(files, key=lambda x: x['name']):
            stem = Path(f['name']).stem
            cov_id = covers_by_stem.get(stem, '')
            if not cov_id and ' — ' in stem:
                cov_id = covers_by_stem.get(stem.rsplit(' — ', 1)[0], '')
            cat_it = cat_by_title.get(stem) or {}
            sz = round(int(f.get('size') or 0) / (1024 * 1024), 2) if f.get('size') else ''
            book_rows.append([
                f['name'],
                lvl,
                sub,
                gen_eq,
                path_str,
                cat_it.get('source_site', 'qawmimadrasa.com'),
                sz,
                f"https://drive.google.com/file/d/{f['id']}/view",
                f"https://drive.google.com/drive/folders/{fid}",
                f"https://drive.google.com/file/d/{cov_id}/view" if cov_id else "",
                f"https://drive.google.com/thumbnail?id={cov_id}&sz=w600" if cov_id else "",
                'Verified in Level -> Subject Structure',
            ])

    print(f"Total books verified inside Qawmi Madrasa Level->Subject folders: {total_books} (+ {len(covers_by_stem)} covers)")

    # Write clean updated Qawmi Category Map & Book Catalog
    xlsx_p = REPORTS / 'Qawmi Madrasa Category Map & Book Catalog.xlsx'
    csv_p = REPORTS / 'Qawmi Madrasa Category Map & Book Catalog.csv'
    wb = openpyxl.Workbook()
    ws_map = wb.active
    ws_map.title = 'Category_Map'
    hfill = PatternFill(start_color='1B5E20', end_color='1B5E20', fill_type='solid')
    hfont = Font(color='FFFFFF', bold=True, size=11)

    mheaders = ['Qawmi Level', 'Subject Category', 'General Education Equivalent', 'Bangla Stage Label', 'Folder Path', 'Books Count', 'Google Drive Folder Link']
    ws_map.append(mheaders)
    for c in range(1, len(mheaders) + 1):
        cell = ws_map.cell(1, c)
        cell.fill = hfill
        cell.font = hfont
    for r in map_rows:
        ws_map.append(r)
    ws_map.freeze_panes = 'A2'
    ws_map.auto_filter.ref = f'A1:G{len(map_rows)+1}'
    for col, w in zip('ABCDEFG', [24, 42, 32, 32, 58, 14, 56]):
        ws_map.column_dimensions[col].width = w

    ws_b = wb.create_sheet('Books_Catalog')
    bheaders = ['Book Title', 'Qawmi Level', 'Subject', 'General Education Equivalent', 'Folder Path', 'Source', 'Size (MB)', 'PDF Drive Link', 'Folder Drive Link', 'Cover Drive Link', 'Embeddable Thumbnail URL', 'Status']
    ws_b.append(bheaders)
    for c in range(1, len(bheaders) + 1):
        cell = ws_b.cell(1, c)
        cell.fill = hfill
        cell.font = hfont
    for r in book_rows:
        ws_b.append(r)
    ws_b.freeze_panes = 'A2'
    ws_b.auto_filter.ref = f'A1:L{len(book_rows)+1}'
    for col, w in zip('ABCDEFGHIJKL', [48, 24, 34, 28, 52, 22, 10, 48, 48, 48, 52, 30]):
        ws_b.column_dimensions[col].width = w
    wb.save(xlsx_p)

    with open(csv_p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(bheaders)
        w.writerows(book_rows)

    ok1, _, e1 = run_gdrive(['mutate', 'update', QAWMI_XLSX_ID, str(xlsx_p), '--json'])
    log_op('updated', {'id': QAWMI_XLSX_ID, 'name': xlsx_p.name, 'ok': ok1, 'error': e1 if not ok1 else None})
    ok2, _, e2 = run_gdrive(['mutate', 'update', QAWMI_CSV_ID, str(csv_p), '--json'])
    log_op('updated', {'id': QAWMI_CSV_ID, 'name': csv_p.name, 'ok': ok2, 'error': e2 if not ok2 else None})
    if not (ok1 and ok2):
        raise RuntimeError(f"Qawmi catalog upload failed: {e1} | {e2}")
    return total_books, len(covers_by_stem)

def update_master_navigator_for_english_moves():
    print("\n=== UPDATING LIBRARY MASTER NAVIGATOR.XLSX FOR MOVED ENGLISH BOOKS ===")
    erows = json.load(open(DATA / 'english_books_migration_plan.json', encoding='utf-8'))
    moved_by_id = {r['drive_file_id']: r for r in erows if r['action'] == 'Move' or r['proposed_destination'] != r['current_location']}
    src = DATA / 'updated_Library_Master_Navigator.xlsx'
    wb = openpyxl.load_workbook(src)

    updated_count = 0
    for sname in ['📚 All Books (18,647)', '⚠️ Review & Placement Tasks']:
        if sname not in wb.sheetnames:
            continue
        ws = wb[sname]
        headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        subj_col = headers.index('Subject') + 1 if 'Subject' in headers else None
        cls_col = headers.index('Classification Status') + 1 if 'Classification Status' in headers else None
        for row_idx in range(2, ws.max_row + 1):
            fid = ws.cell(row_idx, 21).value
            if fid in moved_by_id:
                info = moved_by_id[fid]
                dest = info['proposed_destination']
                root_cat, sub_cat = (dest.split('/', 1) + [''])[:2]
                ws.cell(row_idx, 4).value = info['language']
                ws.cell(row_idx, 5).value = root_cat
                ws.cell(row_idx, 6).value = sub_cat
                ws.cell(row_idx, 11).value = f"{dest}/"
                ws.cell(row_idx, 12).value = f"{dest}/{info['filename']}"
                if info.get('dest_folder_id'):
                    ws.cell(row_idx, 15).value = f'=HYPERLINK("https://drive.google.com/drive/folders/{info["dest_folder_id"]}", "📂 Open Folder")'
                if subj_col:
                    ws.cell(row_idx, subj_col).value = info['subject']
                if cls_col:
                    ws.cell(row_idx, cls_col).value = 'Needs Review' if 'Review' in root_cat else 'Classified & Rehomed'
                if sname == '📚 All Books (18,647)':
                    updated_count += 1

    out = DATA / 'updated_Library_Master_Navigator_v2.xlsx'
    wb.save(out)
    ok, _, err = run_gdrive(['mutate', 'update', MASTER_NAV_ID, str(out), '--json'])
    log_op('updated', {'id': MASTER_NAV_ID, 'name': 'Library Master Navigator.xlsx', 'ok': ok, 'error': err if not ok else None})
    if not ok:
        raise RuntimeError(f"Master Navigator update failed: {err}")
    print(f"Master Navigator updated in-place ({updated_count} relocated English Books rows refreshed).")

if __name__ == '__main__':
    root_folders, total_eng = verify_english_books()
    q_books, q_covs = update_qawmi_catalog_and_verify()
    update_master_navigator_for_english_moves()
    print(f"\n=== ALL POST-EXECUTION VERIFICATION & CATALOG UPDATES COMPLETE ===")
    print(f"Root Folders Count: {len(root_folders)} | English Books Remaining: {total_eng} | Qawmi Books Verified: {q_books} (+ {q_covs} covers)")
