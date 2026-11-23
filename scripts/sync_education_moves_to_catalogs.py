#!/usr/bin/env python3
"""
Sync moved Google Drive folders under Education & Textbooks to all local
catalogs, indexes, Excel workbooks, and Qawmi reports (strictly Drive-readonly).

Verified Drive moves under `Education & Textbooks`:
1. `Alia Madrasa/...` -> `Madrasa/Alia Madrasa/...`
2. `Qawmi Madrasa/...` -> `Madrasa/Qawmi Madrasa/...`
3. `General Education/Professional & Job Exams (BCS)/...` -> `Professional & Job Exams (BCS)/...`
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parent.parent

MASTER_JSON = REPO_ROOT / "catalog" / "master_catalog.json"
MASTER_CSV = REPO_ROOT / "catalog" / "master_catalog.csv"
CAT_INDEX_MD = REPO_ROOT / "catalog" / "CATEGORY_INDEX.md"
NAV_CSV = REPO_ROOT / "catalog" / "Bangladesh_eBook_Library_Master_Navigator.csv"
NAV_XLSX = REPO_ROOT / "catalog" / "Bangladesh_eBook_Library_Master_Navigator.xlsx"
QAWMI_CSV = REPO_ROOT / "reports" / "Qawmi Madrasa Category Map & Book Catalog.csv"
QAWMI_XLSX = REPO_ROOT / "reports" / "Qawmi Madrasa Category Map & Book Catalog.xlsx"

RE_FULL_MADRASA = re.compile(
    r"Education & Textbooks/(?!Madrasa/)(Alia Madrasa|Qawmi Madrasa)(?=/|$)"
)
RE_FULL_BCS = re.compile(
    r"Education & Textbooks/General Education/Professional & Job Exams \(BCS\)(?=/|$)"
)
RE_SUB_MADRASA = re.compile(r"^(Alia Madrasa|Qawmi Madrasa)(?=/|$)")
RE_SUB_BCS = re.compile(r"^General Education/Professional & Job Exams \(BCS\)(?=/|$)")


def transform_subcat(sub: str) -> str:
    if not sub:
        return sub
    if RE_SUB_MADRASA.match(sub):
        return f"Madrasa/{sub}"
    if RE_SUB_BCS.match(sub):
        return sub[len("General Education/"):]
    return sub


def transform_text(val: str) -> str:
    if not val:
        return val
    out = RE_FULL_MADRASA.sub(r"Education & Textbooks/Madrasa/\1", val)
    out = RE_FULL_BCS.sub("Education & Textbooks/Professional & Job Exams (BCS)", out)
    return out


def update_master_json() -> int:
    rows = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
    changed = 0
    for row in rows:
        row_changed = False
        if row.get("category") == "Education & Textbooks":
            old_sub = row.get("subcategory") or ""
            new_sub = transform_subcat(old_sub)
            if new_sub != old_sub:
                row["subcategory"] = new_sub
                row_changed = True
        old_dp = row.get("drive_path") or ""
        new_dp = transform_text(old_dp)
        if new_dp != old_dp:
            row["drive_path"] = new_dp
            row_changed = True
        if row_changed:
            changed += 1

    MASTER_JSON.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    edu_top = Counter(
        (r.get("subcategory") or "").split("/")[0]
        for r in rows
        if r.get("category") == "Education & Textbooks"
    )
    covers = sum(1 for r in rows if r.get("cover_url"))
    print(f"master_catalog.json: {changed} rows updated (total={len(rows)}, covers={covers})")
    print(f"  Education & Textbooks top folders: {dict(edu_top)}")
    return changed


def update_master_csv() -> int:
    with MASTER_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    changed = 0
    for row in rows:
        row_changed = False
        if row.get("category") == "Education & Textbooks":
            old_sub = row.get("subcategory") or ""
            new_sub = transform_subcat(old_sub)
            if new_sub != old_sub:
                row["subcategory"] = new_sub
                row_changed = True
        old_dp = row.get("drive_path") or ""
        new_dp = transform_text(old_dp)
        if new_dp != old_dp:
            row["drive_path"] = new_dp
            row_changed = True
        if row_changed:
            changed += 1

    with MASTER_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"master_catalog.csv: {changed} rows updated")
    return changed


def update_category_index() -> int:
    text = CAT_INDEX_MD.read_text(encoding="utf-8")
    new_lines = []
    changed = 0
    for line in text.splitlines(keepends=True):
        nl = transform_text(line)
        if nl != line:
            changed += 1
        new_lines.append(nl)
    CAT_INDEX_MD.write_text("".join(new_lines), encoding="utf-8")
    print(f"CATEGORY_INDEX.md: {changed} lines updated")
    return changed


def transform_navigator_cell(val: str, is_sub_col: bool = False) -> str:
    out = transform_text(val)
    if is_sub_col:
        out = transform_subcat(out)
    return out


def update_csv_generic(path: Path, has_sub_col: bool = False) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return 0
    headers = rows[0]
    sub_cols = {
        idx
        for idx, h in enumerate(headers)
        if has_sub_col and h.strip() in {"Target Subfolder", "Subcategory"}
    }

    changed = 0
    for r_idx in range(1, len(rows)):
        row = rows[r_idx]
        for c_idx, cell in enumerate(row):
            if not isinstance(cell, str):
                continue
            new_val = transform_navigator_cell(cell, is_sub_col=(c_idx in sub_cols))
            if new_val != cell:
                row[c_idx] = new_val
                changed += 1

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"{path.name}: {changed} cells updated")
    return changed


def update_xlsx_generic(path: Path, has_sub_col: bool = False) -> int:
    wb = openpyxl.load_workbook(path)
    changed = 0
    for ws in wb.worksheets:
        header_row = [
            str(ws.cell(row=1, column=c).value or "").strip()
            for c in range(1, ws.max_column + 1)
        ]
        sub_cols = {
            c
            for c, h in enumerate(header_row, start=1)
            if has_sub_col and h in {"Target Subfolder", "Subcategory"}
        }
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    new_val = transform_navigator_cell(
                        cell.value,
                        is_sub_col=(cell.column in sub_cols and cell.row > 1),
                    )
                    if new_val != cell.value:
                        cell.value = new_val
                        changed += 1
    wb.save(path)
    print(f"{path.name}: {changed} cells updated across {len(wb.worksheets)} sheets")
    return changed


def main() -> None:
    update_master_json()
    update_master_csv()
    update_category_index()
    update_csv_generic(NAV_CSV, has_sub_col=True)
    update_xlsx_generic(NAV_XLSX, has_sub_col=True)
    if QAWMI_CSV.exists():
        update_csv_generic(QAWMI_CSV, has_sub_col=False)
    if QAWMI_XLSX.exists():
        update_xlsx_generic(QAWMI_XLSX, has_sub_col=False)


if __name__ == "__main__":
    main()
