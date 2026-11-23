#!/usr/bin/env python3
"""Deep audit & complete reorganization plan for all 8,020 existing covers inside
Library Management/Cover Images (1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj).
Also extracts clean metadata-based cover URLs from local catalogs for Part 2.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CATALOG = ROOT / "catalog"
REPORTS = ROOT / "reports"

PLACEHOLDER_COVER_IDS = {"11RaIVAsz_JCw6s-XhL7bZ_cg776z6VtK"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", str(s or ""))
    s = s.replace("য়", "য়").replace("ড়", "ড়").replace("ঢ়", "ঢ়")
    s = re.sub(r"\.[a-z0-9]{2,4}$", "", s, flags=re.I)
    s = re.sub(r"[\W_]+", " ", s, flags=re.U).strip().casefold()
    return s


def norm_noparens(s: str) -> str:
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", str(s or ""))
    return norm(s)


def sanitize_filename(s: str, max_len: int = 180) -> str:
    s = unicodedata.normalize("NFC", str(s or "")).strip()
    s = re.sub(r'[<>:"/\\|?*\r\n\t\x00-\x1f]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    return s[:max_len].strip() if len(s) > max_len else s


def canonical_book_stem(mc_rec: dict) -> str:
    dp = mc_rec.get("drive_path") or mc_rec.get("original_filename") or mc_rec.get("title") or "Untitled"
    stem = Path(dp).stem
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4]
    return sanitize_filename(stem or mc_rec.get("title") or "Untitled")


def main() -> None:
    mc = json.loads((CATALOG / "master_catalog.json").read_text(encoding="utf-8"))
    mc_by_id = {b["drive_file_id"]: b for b in mc}
    mb = json.loads((DATA / "merged_books.json").read_text(encoding="utf-8"))
    bc = json.loads((DATA / "book_covers.json").read_text(encoding="utf-8"))

    covers = json.loads((DATA / "all_8020_covers_ls.json").read_text(encoding="utf-8-sig"))
    covers_by_id = {c["id"]: c for c in covers}
    qawmi_ls_ids = {x["id"] for x in json.loads((DATA / "qawmi_covers_ls.json").read_text(encoding="utf-8-sig"))}

    # Build mc lookup maps (exact stems, stripped parentheticals, split 'Author - Title' / 'Title — Author')
    mc_by_key: dict[str, list[dict]] = defaultdict(list)
    mc_by_src_url: dict[str, list[dict]] = defaultdict(list)

    for b in mc:
        if b.get("source_url"):
            mc_by_src_url[b["source_url"].rstrip("/")].append(b)
        t = b.get("title") or ""
        stem = Path(b.get("drive_path") or "").stem
        ori = Path(b.get("original_filename") or "").stem
        author = b.get("author") or ""
        keys: set[str] = set()
        for val in (t, stem, ori):
            if val:
                keys.add(norm(val))
                keys.add(norm_noparens(val))
            for sep in (" — ", " - ", " – "):
                if sep in val:
                    p0, p1 = val.split(sep, 1)
                    if len(norm(p0)) >= 3:
                        keys.add(norm(p0))
                    if len(norm(p1)) >= 3:
                        keys.add(norm(p1))
        if author and author not in ("Unknown", "Various / Unknown", "NCTB", "এনসিটিবি"):
            keys.add(norm(f"{t} {author}"))
        for k in keys:
            if k and len(k) >= 3:
                mc_by_key[k].append(b)

    # Bridge merged_books sibling IDs -> mc_rec
    mb_sibling_to_mc: dict[str, dict] = {}
    mb_name_to_mc: dict[str, dict] = {}
    for item in mb:
        fids = [item.get("file_id"), item.get("pdf_file_id"), item.get("epub_file_id")] + [
            f.get("id") for f in (item.get("files") or [])
        ]
        hit = next((mc_by_id[f] for f in fids if f and f in mc_by_id), None)
        if hit:
            for f in fids:
                if f:
                    mb_sibling_to_mc[f] = hit
            if item.get("name"):
                mb_name_to_mc[norm(item["name"])] = hit

    cov_to_mc: dict[str, list[dict]] = defaultdict(list)
    cov_seen: set[tuple[str, str]] = set()
    cid_to_bc_meta: dict[str, list[dict]] = defaultdict(list)

    def add_match(cid: str, b: dict) -> None:
        if cid in covers_by_id and cid not in PLACEHOLDER_COVER_IDS and b:
            pair = (cid, b["drive_file_id"])
            if pair not in cov_seen:
                cov_seen.add(pair)
                cov_to_mc[cid].append(b)

    # 1. Qawmi progress & CSV
    qp = json.loads((DATA / "qawmimadrasa_progress.json").read_text(encoding="utf-8"))
    for item in qp.values():
        if isinstance(item, dict):
            for f in (item.get("files") or []):
                if f.get("cover_id") and f.get("id") in mc_by_id:
                    add_match(f["cover_id"], mc_by_id[f["id"]])

    with open(REPORTS / "Qawmi Madrasa Category Map & Book Catalog.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            cm = re.search(r"/file/d/([^/]+)/", row.get("Cover Drive Link", ""))
            bm = re.search(r"/file/d/([^/]+)/", row.get("PDF Drive Link", ""))
            if cm and bm and bm.group(1) in mc_by_id:
                add_match(cm.group(1), mc_by_id[bm.group(1)])

    # 2. book_covers.json (ID, sibling ID, source_url, exact & split Bangla title)
    for bfid, info in bc.items():
        cid = info.get("cover_drive_id")
        if not cid or cid in PLACEHOLDER_COVER_IDS or cid not in covers_by_id:
            continue
        cid_to_bc_meta[cid].append(info)
        if bfid in mc_by_id:
            add_match(cid, mc_by_id[bfid])
        if bfid in mb_sibling_to_mc:
            add_match(cid, mb_sibling_to_mc[bfid])
        burl = (info.get("book_url") or "").rstrip("/")
        if burl and burl in mc_by_src_url:
            for b in mc_by_src_url[burl]:
                add_match(cid, b)
        bt = info.get("title") or ""
        auth = info.get("author") or ""
        t_parts = [norm(bt), norm_noparens(bt)]
        for sep in (" — ", " - ", " – "):
            if sep in bt:
                p0, p1 = bt.split(sep, 1)
                t_parts.extend([norm(p0), norm_noparens(p0), norm(p1)])
        for tk in t_parts:
            if len(tk) < 3:
                continue
            hits = mc_by_key.get(tk)
            if hits and len(hits) <= 5:
                for b in hits:
                    # Prefer author check if short title
                    if len(hits) == 1 or not auth or norm(auth) in norm(f"{b.get('author','')} {b.get('drive_path','')}"):
                        add_match(cid, b)

    # 3. master_catalog cover_url direct Drive IDs
    for b in mc:
        cu = b.get("cover_url") or ""
        m = re.search(r"/file/d/([^/]+)/", cu) or re.search(r"id=([^&]+)", cu)
        if m and m.group(1) not in PLACEHOLDER_COVER_IDS:
            add_match(m.group(1), b)

    # 4. Remaining pre-Qawmi covers matched by stem / prefix against mb_name & mc_by_key
    for c in covers:
        cid = c["id"]
        if cid in PLACEHOLDER_COVER_IDS or cid in cov_to_mc:
            continue
        st = Path(c["name"]).stem
        if norm(st) in mb_name_to_mc:
            add_match(cid, mb_name_to_mc[norm(st)])
            continue
        cand_keys = [norm(st), norm_noparens(st)]
        for sep in (" - ", " — ", "_"):
            if sep in st:
                p0, p1 = st.split(sep, 1)
                cand_keys.extend([norm(p0), norm_noparens(p0)])
        for ck in cand_keys:
            if len(ck) < 3:
                continue
            hits = mc_by_key.get(ck)
            if hits and len(hits) <= 4:
                for b in hits:
                    add_match(cid, b)
                break

    # Resolve primary cover per book (if multiple cover IDs exist for same book, keep largest/cleanest, quarantine extras)
    book_to_cids: dict[str, list[str]] = defaultdict(list)
    for cid, bs in cov_to_mc.items():
        for b in bs:
            book_to_cids[b["drive_file_id"]].append(cid)

    chosen_cid_for_book: dict[str, str] = {}
    for bfid, cids in book_to_cids.items():
        if len(cids) == 1:
            chosen_cid_for_book[bfid] = cids[0]
        else:
            cids_sorted = sorted(
                cids,
                key=lambda x: (
                    1 if x in qawmi_ls_ids else 0,
                    int(covers_by_id[x].get("size") or 0),
                    x,
                ),
                reverse=True,
            )
            chosen_cid_for_book[bfid] = cids_sorted[0]

    # Track seen (name, size) for unmatched covers to also catch duplicate uploads (like 12 copies of Ami Bibekanond)
    seen_unmatched_sig: set[tuple[str, str]] = set()
    used_target_paths: dict[str, str] = {}
    cid_assignments: dict[str, dict] = {}
    stats: Counter[str] = Counter()

    for c in sorted(covers, key=lambda x: (-int(x.get("size") or 0), x["name"], x["id"])):
        cid = c["id"]
        ext = Path(c["name"]).suffix.lower() or ".jpg"
        if cid in PLACEHOLDER_COVER_IDS:
            stats["placeholder_logo"] += 1
            cid_assignments[cid] = {
                "status": "placeholder",
                "target_folder": "Review & Unclassified/Placeholder Logo",
                "new_name": f"eBanglaLibrary Placeholder Logo{ext}",
            }
            continue

        linked = cov_to_mc.get(cid, [])
        primary = [b for b in linked if chosen_cid_for_book.get(b["drive_file_id"]) == cid]

        if linked and not primary:
            stats["duplicate_for_covered_book"] += 1
            cid_assignments[cid] = {
                "status": "duplicate",
                "target_folder": "Review & Unclassified/Duplicate Legacy Covers",
                "new_name": c["name"],
            }
            continue

        if primary:
            b0 = sorted(primary, key=lambda b: (b["category"], b["subcategory"], b["drive_path"]))[0]
            stem = canonical_book_stem(b0)
            if len(primary) > 1 and cid in qawmi_ls_ids:
                orig_stem = sanitize_filename(Path(c["name"]).stem)
                if not any(x in orig_stem.lower() for x in (".com", "mt-")):
                    stem = orig_stem
            cat_folder = f"{b0['category']}/{b0['subcategory']}" if b0.get("subcategory") else b0["category"]
            cand_name = f"{stem}{ext}"
            full_key = f"{cat_folder}/{cand_name}".casefold()
            if full_key in used_target_paths:
                cand_name = f"{stem} [{cid[:6]}]{ext}"
                full_key = f"{cat_folder}/{cand_name}".casefold()
            used_target_paths[full_key] = cid
            stats["matched_to_catalog_books"] += 1
            if cand_name != c["name"]:
                stats["renamed_to_book_name"] += 1
            cid_assignments[cid] = {
                "status": "matched",
                "target_folder": cat_folder,
                "new_name": cand_name,
                "book_ids": [b["drive_file_id"] for b in primary],
            }
            continue

        # Not linked to a book in master_catalog -> check if duplicate of an earlier unmatched cover or eBanglaLibrary JSON archive
        sig = (norm(c["name"]), str(c.get("size") or ""))
        if sig in seen_unmatched_sig:
            stats["duplicate_unmatched_cover"] += 1
            cid_assignments[cid] = {
                "status": "duplicate",
                "target_folder": "Review & Unclassified/Duplicate Legacy Covers",
                "new_name": c["name"],
            }
            continue
        seen_unmatched_sig.add(sig)

        # Check book_covers.json for clean Bangla JSON title rename
        bc_list = cid_to_bc_meta.get(cid, [])
        if bc_list:
            binfo = bc_list[0]
            bt = sanitize_filename(binfo.get("title") or "")
            ba = sanitize_filename(binfo.get("author") or "")
            if bt:
                stem = bt if (not ba or ba in bt or ba in ("Unknown", "Various / Unknown")) else f"{bt} — {ba}"
                cand_name = f"{stem}{ext}"
                cat_folder = "Bangla Books/eBanglaLibrary JSON Archive Covers"
                full_key = f"{cat_folder}/{cand_name}".casefold()
                if full_key in used_target_paths:
                    cand_name = f"{stem} [{cid[:6]}]{ext}"
                    full_key = f"{cat_folder}/{cand_name}".casefold()
                used_target_paths[full_key] = cid
                stats["ebanglalibrary_json_covers_renamed"] += 1
                if cand_name != c["name"]:
                    stats["renamed_to_book_name"] += 1
                cid_assignments[cid] = {
                    "status": "json_archive",
                    "target_folder": cat_folder,
                    "new_name": cand_name,
                }
                continue

        stats["unmatched_legacy"] += 1
        cat_folder = "Review & Unclassified/Unmatched Legacy Covers"
        cand_name = c["name"]
        full_key = f"{cat_folder}/{cand_name}".casefold()
        if full_key in used_target_paths:
            cand_name = f"{Path(c['name']).stem} [{cid[:6]}]{ext}"
            full_key = f"{cat_folder}/{cand_name}".casefold()
        used_target_paths[full_key] = cid
        cid_assignments[cid] = {
            "status": "unmatched",
            "target_folder": cat_folder,
            "new_name": cand_name,
        }

    books_covered = set(chosen_cid_for_book.keys())
    books_missing = [b for b in mc if b["drive_file_id"] not in books_covered]

    summary = {
        "total_existing_covers": len(covers),
        "stats": dict(stats),
        "unique_target_folders_for_existing": len({a["target_folder"] for a in cid_assignments.values()}),
        "total_catalog_books": len(mc),
        "books_already_covered": len(books_covered),
        "books_needing_cover": len(books_missing),
        "missing_by_category": dict(Counter(b["category"] for b in books_missing)),
    }
    (DATA / "existing_covers_audit_plan.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "assignments": cid_assignments,
                "chosen_cover_by_book": chosen_cid_for_book,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print("=== UPDATED EXISTING COVERS AUDIT SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
