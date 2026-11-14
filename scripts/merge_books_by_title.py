#!/usr/bin/env python3
"""
Merge every book across Google Drive into its own clean per-book folder:
  <ROOT>/<Clean Category>/<Clean Leaf>/<Clean Book Name>/
    ├── <Clean Book Name>.<pdf|epub|mobi|azw3>   (when ebook exists)
    ├── <Clean Book Name>.json                   (when text JSON exists)
    └── <Clean Book Name>.<jpg|webp|png>         (when cover image exists)

Also:
  - Purges non-book junk (.ini, .apk, .mp4, .avi, .gif, .mp3, .m4a, .opf, .kfx,
    author portrait thumbnails, NFD duplicate JSONs, exact duplicate files)
  - Groups multi-page scanned book image sets (Constitution 1..109, Qasida IMG_*, Ami-Bibekananda)
  - Attaches vol_N_pic.jpg covers to matching Vivekananda volumes
  - Promotes all 25 clean categories directly to Drive root & flattens legacy author folders
  - Updates data/clean_folders.json, data/merged_books.json, data/trashed_ids.json,
    and deduplicates local text/*.json cleanly in NFC
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import clean_classifier as cc
import title_cleaner as tc

GDRIVE_CLI = r"C:\Users\USER\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"
ROOT_DRIVE_ID = "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
PROTECTED_DRIVE_ID = "1ObOiGGQXl9B4bodcnDkx7g5yU_dc-Gol"

EBOOK_EXTS = {".pdf", ".epub", ".mobi", ".azw3", ".azw", ".djvu", ".doc", ".docx", ".txt", ".rtf", ".zip"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
TRASH_EXTS = {
    ".ini", ".apk", ".mp4", ".avi", ".flv", ".wmv", ".mkv", ".mov",
    ".gif", ".mp3", ".m4a", ".wav", ".aac", ".ogg",
    ".thm", ".db", ".tmp", ".part", ".crdownload", ".ds_store",
    ".url", ".lnk", ".exe", ".bat", ".sh", ".msi", ".cab",
}
COMPANION_JUNK_EXTS = {".opf", ".kfx"}

JUNK_IMAGE_PAT = re.compile(
    r"(?i)(?:asaduzzaman_nur|tv-actor|^\d+px-|^sub(?:[0-9a-f]{16,}|\d*)\.jpe?g$|^61974[\s_]|"
    r"chrome.*(?:ট্রান্সলেট|translate)|^nazrul\d*\.jpe?g$|^anisul[\s_]*haque\.jpe?g$|"
    r"^imdadul_haque_milon\.jpe?g$|^humayun.*\.jpg$|desktop\.ini|^\d{9,}\.jpe?g$)"
)
FOREIGN_SCRIPT_TRASH_RE = re.compile(r"[\u0B80-\u0DFF\u0E00-\u109F\u3040-\u30FF\uAC00-\uD7AF\u0400-\u04FF]")
WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_book_folder_name(stem: str, fallback: str) -> str:
    s = tc.sanitize_filename(stem, max_len=110).rstrip(" .")
    if not s or s.upper() in WIN_RESERVED:
        return fallback
    return s

_LOCK = threading.Lock()
CANONICAL_TOP_CATS = sorted({leaf.split("/")[0] for leaf in cc.CANONICAL_LEAVES})

# Legacy root wrappers to dissolve cleanly once empty
LEGACY_CONTAINERS = {"pdf", "text", "covers"}

# Author prefix/suffix markers to normalize book match key
VOL_PAT = re.compile(
    r"(?i)(?:part|vol(?:ume)?|খণ্ড|খন্ড|পর্ব|সংখ্যা|অধ্যায়|অধ্যায়|class|শ্রেণি|শ্রেণী|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম|একাদশ|দ্বাদশ)[\s._\-()]*[\d\u09e6-\u09ef]*"
)
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def atomic_write_json(path: Path, obj: Any, indent: int | None = None) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")
    tmp.replace(path)


def gd_run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [GDRIVE_CLI, "plugin-cli", "gdrive", *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def gd_mkdir(name: str, parent_id: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            res = gd_run(["mutate", "mkdir", name, "--parent", parent_id, "--json"], timeout=60)
            out = (res.stdout or "").strip()
            if res.returncode == 0 and out:
                try:
                    data = json.loads(out)
                    if isinstance(data, dict) and data.get("id"):
                        return data["id"]
                except json.JSONDecodeError:
                    m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", out)
                    if m:
                        return m.group(1)
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def gd_batch(ops: list[dict], timeout: int = 240, retries: int = 5) -> tuple[bool, str]:
    if not ops:
        return True, ""
    out = ""
    for attempt in range(retries):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(ops, tf, ensure_ascii=False)
            tmp_path = tf.name
        try:
            res = gd_run(["mutate", "batch", "-f", tmp_path], timeout=timeout)
            out = (res.stdout or "") + "\n" + (res.stderr or "")
            if res.returncode == 0:
                return True, out
        except subprocess.TimeoutExpired:
            out = "timeout"
        except Exception as exc:
            out = str(exc)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        low = out.lower()
        if "403" in low or "quota" in low or "429" in low or "rate" in low:
            time.sleep(min(20.0 * (attempt + 1), 65.0))
        else:
            time.sleep(2.0 * (attempt + 1))
    return False, out


def ls_full_folder(fid: str) -> list[dict]:
    """List EVERY non-trashed item in a single folder without stream-ls 1000-item cap."""
    res = gd_run(["readonly", "ls", fid, "--max", "0", "--json"], timeout=180)
    if res.returncode == 0 and res.stdout:
        try:
            data = json.loads(res.stdout)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []


def stream_ls_many(folder_ids: list[str], max_per_folder: int = 5000) -> dict[str, list[dict]]:
    if not folder_ids:
        return {}
    out_map: dict[str, list[dict]] = {}
    with tempfile.TemporaryDirectory() as td:
        in_p = Path(td) / "ls_in.jsonl"
        out_p = Path(td) / "ls_out.jsonl"
        in_p.write_text("\n".join(json.dumps({"id": fid}) for fid in folder_ids), encoding="utf-8")
        subprocess.run(
            [
                GDRIVE_CLI, "plugin-cli", "gdrive", "readonly", "stream", "ls",
                "-i", str(in_p), "-o", str(out_p), "-c", "16", "--max", str(max_per_folder),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            check=False,
        )
        if out_p.exists():
            for ln in out_p.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                row = json.loads(ln)
                if row.get("_ok"):
                    out_map[row["id"]] = row.get("data") or []
    # stream ls caps individual folders at 1,000 items; fetch full listing for any saturated folder
    saturated = [fid for fid, items in out_map.items() if len(items) >= 950]
    if saturated:
        print(f"  Paginating {len(saturated)} large (>=950-item) folders via ls --max 0...", flush=True)
        for fid in saturated:
            full = ls_full_folder(fid)
            if len(full) >= len(out_map[fid]):
                out_map[fid] = full
    return out_map


def stream_bfs_drive(root_id: str, skip_folder_ids: set[str] | None = None) -> tuple[dict[str, dict], list[dict]]:
    """Breadth-first scan of entire Drive library using parallel stream ls."""
    skip_folder_ids = skip_folder_ids or set()
    folders: dict[str, dict] = {
        root_id: {"id": root_id, "name": "", "parent_id": "", "rel_path": ""}
    }
    files: list[dict] = []
    frontier = [root_id]
    depth = 0
    while frontier:
        depth += 1
        next_frontier: list[str] = []
        ls_map = stream_ls_many(frontier)
        for pid in frontier:
            p_rel = folders[pid]["rel_path"]
            for it in ls_map.get(pid, []):
                fid = it["id"]
                if fid == PROTECTED_DRIVE_ID:
                    continue
                name = tc.fix_unicode_nfc(it.get("name") or "")
                rel = f"{p_rel}/{name}" if p_rel else name
                if it.get("mimeType") == "application/vnd.google-apps.folder":
                    folders[fid] = {"id": fid, "name": name, "parent_id": pid, "rel_path": rel}
                    if fid not in skip_folder_ids:
                        next_frontier.append(fid)
                else:
                    files.append({
                        "id": fid,
                        "name": name,
                        "raw_name": it.get("name") or "",
                        "mimeType": it.get("mimeType") or "",
                        "size": int(it.get("size") or 0),
                        "modifiedTime": it.get("modifiedTime") or "",
                        "parent_id": pid,
                        "rel_path": rel,
                    })
        print(f"  BFS depth {depth}: scanned {len(frontier)} folders -> {len(files)} files so far (next={len(next_frontier)})", flush=True)
        frontier = next_frontier
    return folders, files


def _clean_extracted_candidate(text: str) -> str:
    t = re.sub(r"^Microsoft Word\s*-\s*", "", text or "", flags=re.I).strip()
    if tc.is_likely_bijoy(t):
        t = tc.bijoy_to_unicode(t)
    t = tc.strip_watermarks_and_noise(t)
    t = tc.fix_unicode_nfc(t)
    if not t or len(t) < 3 or tc.is_opaque_stem(t) or BAD_INTERNAL_TITLE_RE.search(t):
        return ""
    if tc.is_likely_bijoy(t):
        return ""
    return t


BAD_INTERNAL_TITLE_RE = re.compile(
    r"(?i)(?:scanned\s*document|converted\s*to\s*pdf|prelim[ia]nary\s*pages|"
    r"\.pmd\b|\.dvi\b|^lw_potentials|^beard\s*final|microsoft\s*word|^untitled\b|"
    r"acrobat\s*distiller|camscanner|^img_\d+$)"
)
GENERIC_CHAPTER_STEM_RE = re.compile(
    r"(?i)^(?:ch(?:apter)?[\s._\-]*[\d\u09e6-\u09ef]+(?:\s+[\d\-–p\s]+)?|"
    r"part[\s._\-+]*[\d\u09e6-\u09ef+]+|page[\s._\-]*[\d\u09e6-\u09ef\-–]+|"
    r"vol(?:ume)?[\s._\-]*[\d\u09e6-\u09ef\-]+|"
    r"(?:খণ্ড|খন্ড|অধ্যায়|অধ্যায়|পর্ব)[\s._\-]*[\d\u09e6-\u09ef]+|"
    r"index|preface|contents|cover|appendix|[\d\u09e6-\u09ef]+(?:\s*-\s*[\d\u09e6-\u09ef]+)?|_+)$"
)
GENERIC_PARENT_DIR_RE = re.compile(
    r"(?i)^(?:নতুন|new|pdf|books?|others?|misc|0\d\s*-|islamic|হিন্দু ধর্ম|কুরআন|ইসলামিক সাহিত্য|বাংলাদেশের ইতিহাস)$"
)

_PDF_CHILD_CODE = (
    "import re, sys, pymupdf; "
    "doc = pymupdf.open(sys.argv[1]); "
    "mt = (doc.metadata or {}).get('title') or ''; "
    "out = [mt]; "
    "[out.append(ln.strip()) for p in range(min(3, len(doc))) "
    "for ln in (doc[p].get_text('text') or '').splitlines() if 3 <= len(ln.strip()) <= 120][:40]; "
    "doc.close(); "
    "print('\\n'.join(out[:25]))"
)


def extract_internal_title_from_drive(fid: str, ext: str, size: int = 0) -> str:
    """Download opaque PDF/EPUB temporarily (<=60MB) and extract internal title via isolated subprocess."""
    if size and size > 60 * 1024 * 1024:
        return ""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / f"book{ext}"
        try:
            res = gd_run(["readonly", "download", fid, "--out", str(tmp)], timeout=120)
        except Exception:
            return ""
        if res.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 200:
            return ""
        if ext == ".epub":
            try:
                with zipfile.ZipFile(tmp) as zf:
                    for n in zf.namelist():
                        if n.lower().endswith(".opf"):
                            xml = zf.read(n).decode("utf-8", errors="ignore")
                            m = re.search(r"<dc:title[^>]*>([^<]+)</dc:title>", xml, re.I)
                            if m:
                                c = _clean_extracted_candidate(m.group(1))
                                if c:
                                    return c
            except Exception:
                pass
        if ext == ".docx":
            try:
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(tmp) as zf:
                    for core_p in ("docProps/core.xml",):
                        if core_p in zf.namelist():
                            xml = zf.read(core_p).decode("utf-8", errors="ignore")
                            m = re.search(r"<dc:title[^>]*>([^<]+)</dc:title>", xml, re.I)
                            if m:
                                c = _clean_extracted_candidate(m.group(1))
                                if c:
                                    return c
                    if "word/document.xml" in zf.namelist():
                        root_xml = ET.fromstring(zf.read("word/document.xml"))
                        lines = []
                        for p in root_xml.iter():
                            if p.tag.endswith("}p"):
                                txt = "".join(t.text or "" for t in p.iter() if t.tag.endswith("}t")).strip()
                                if 3 <= len(txt) <= 120:
                                    c = _clean_extracted_candidate(txt)
                                    if c:
                                        return c
                                if len(lines) > 15:
                                    break
                                lines.append(txt)
            except Exception:
                pass
        if ext == ".pdf":
            try:
                sub = subprocess.run(
                    [sys.executable, "-c", _PDF_CHILD_CODE, str(tmp)],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=20,
                )
                if sub.returncode == 0 and sub.stdout:
                    for ln in sub.stdout.splitlines():
                        ln = ln.strip()
                        if not ln or re.match(r"(?i)^(?:page|contents|index|isbn|copyright|all rights|www\.|http)", ln):
                            continue
                        if not re.search(r"[\u0980-\u09ff]{3,}|[A-Za-z]{4,}", ln):
                            continue
                        c = _clean_extracted_candidate(ln)
                        if c:
                            return c
            except Exception:
                pass
    return ""


def normalize_match_pair(title: str, author: str = "") -> tuple[str, str]:
    """Compute folded (title_key, author_key) preserving digits/volume markers cleanly."""
    clean_t = tc.clean_book_stem(title, author=author)
    tk, ak = tc.match_keys(clean_t, author)
    tk = tk.translate(BN_DIGITS)
    return tk, ak


def extract_vol_tag(text: str) -> str:
    t = tc.fix_unicode_nfc(text).translate(BN_DIGITS).lower()
    nums = re.findall(r"\d+", t)
    return "_".join(nums[-2:]) if nums else ""


def load_metadata_indexes() -> dict[str, Any]:
    meta_p = DATA / "ebanglalibrary_meta.json"
    eb_raw = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else []
    eb_state = json.loads((DATA / "eb_upload_state.json").read_text(encoding="utf-8"))
    extra = json.loads((DATA / "extra_books.json").read_text(encoding="utf-8"))
    book_covers = json.loads((DATA / "book_covers.json").read_text(encoding="utf-8"))
    bde_cat = json.loads((DATA / "bdebooks_catalog.json").read_text(encoding="utf-8"))
    copy_plan = json.loads((DATA / "copy_plan.json").read_text(encoding="utf-8")) if (DATA / "copy_plan.json").exists() else []
    progress = json.loads((DATA / "catalog_progress.json").read_text(encoding="utf-8")) if (DATA / "catalog_progress.json").exists() else {}
    cache_p = DATA / "internal_title_cache.json"
    int_cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}
    trashed_p = DATA / "trashed_ids.json"
    trashed = set(json.loads(trashed_p.read_text(encoding="utf-8"))) if trashed_p.exists() else set()

    cp_by_src = {r["source_id"]: r for r in copy_plan if r.get("source_id")}
    source_by_fid: dict[str, dict] = {}
    for sid, fid in progress.items():
        if sid in cp_by_src:
            source_by_fid[fid] = cp_by_src[sid]

    # Map Drive text JSON file_id -> eb_meta record
    eb_by_url = {b.get("url"): b for b in eb_raw if b.get("url")}
    eb_id_to_rec: dict[str, dict] = {}
    eb_cover_by_url = eb_state.get("covers") or {}
    for url, fid in (eb_state.get("uploaded") or {}).items():
        if url in eb_by_url:
            rec = dict(eb_by_url[url])
            cov_url = rec.get("cover_url") or ""
            rec["cover_drive_id"] = eb_cover_by_url.get(cov_url, "")
            eb_id_to_rec[fid] = rec

    # Secondary eb lookup by title+author key for any text JSON whose uploaded map lacks it
    eb_by_tk_ak: dict[tuple[str, str], dict] = {}
    for rec in eb_raw:
        t = rec.get("real_title") or rec.get("title") or ""
        a = rec.get("author") or ""
        k = normalize_match_pair(t, a)
        cov_url = rec.get("cover_url") or ""
        rec_copy = dict(rec)
        rec_copy["cover_drive_id"] = eb_cover_by_url.get(cov_url, "")
        eb_by_tk_ak.setdefault(k, rec_copy)

    extra_by_fid = {b["file_id"]: b for b in extra if b.get("file_id")}
    return {
        "eb_id_to_rec": eb_id_to_rec,
        "eb_by_tk_ak": eb_by_tk_ak,
        "extra_by_fid": extra_by_fid,
        "source_by_fid": source_by_fid,
        "book_covers": book_covers,
        "bde_cat": bde_cat,
        "int_cache": int_cache,
        "trashed": trashed,
        "eb_uploaded_fids": set(eb_id_to_rec.keys()),
    }


def classify_drive_tree(folders: dict[str, dict], files: list[dict], idx: dict[str, Any], merge_state: dict) -> dict[str, Any]:
    already_book_fids = set(merge_state.get("created_book_folders", {}).values())

    # Partition files into buckets by their top-level container
    pdf_files: list[dict] = []
    text_files: list[dict] = []
    cover_files: dict[str, dict] = {}
    already_merged_files: list[dict] = []

    for f in files:
        fid = f["id"]
        rel = f["rel_path"]
        ext = Path(f["name"]).suffix.lower()
        if f["parent_id"] in already_book_fids:
            already_merged_files.append(f)
            if ext == ".json":
                text_files.append(f)
            elif ext in IMAGE_EXTS:
                cover_files[fid] = f
            else:
                pdf_files.append(f)
            continue
        top_seg = rel.split("/")[0] if "/" in rel else ""
        if top_seg == "covers" or (ext in IMAGE_EXTS and rel.startswith("covers/")):
            cover_files[fid] = f
        elif top_seg == "text" or ext == ".json":
            text_files.append(f)
        else:
            pdf_files.append(f)

    # Track Vivekananda vol_N_pic.jpg inside pdf/ so we attach them as covers instead of trashing
    vol_pics: dict[str, dict] = {}
    scan_groups: dict[str, list[dict]] = defaultdict(list)
    junk_to_trash: list[dict] = []
    ebooks: list[dict] = []

    for f in pdf_files:
        name = f["name"]
        ext = Path(name).suffix.lower()
        rel = f["rel_path"]

        if ext in TRASH_EXTS or ext in COMPANION_JUNK_EXTS or FOREIGN_SCRIPT_TRASH_RE.search(name):
            junk_to_trash.append(f)
            continue

        if ext in IMAGE_EXTS:
            # 1. Vivekananda volume covers
            m_vol = re.match(r"(?i)^vol[_\s]*(\d+)[_\s]*pic", name)
            if m_vol:
                vol_pics[m_vol.group(1)] = f
                continue
            # 2. Scanned page series 1..109 Constitution (supports বাংলাদেশ/001.jpg..109.jpg)
            if re.match(r"^\d{1,3}\.jpe?g$", name, re.I) and ("Constitution" in rel or "সংবিধান" in rel or "বাংলাদেশ" in rel or "Law" in rel):
                scan_groups["constitution_bn"].append(f)
                continue
            # 3. Scanned Qasida IMG_20190814_* / IMG 20190814 *
            if re.match(r"^IMG[\s_]+20190814[\s_]", name, re.I) or "কাসিদায়ে" in rel or "নেয়ামতুল্লাহ" in rel:
                scan_groups["qasida_shah_neyamatullah"].append(f)
                continue
            # 4. Scanned Ami-Bibekananda-Bolchhi_*
            if "Ami-Bibekananda-Bolchhi" in name:
                scan_groups["ami_bibekananda_bolchhi"].append(f)
                continue
            # 5. Book cover images stored inside pdf/ subdirs (e.g. Hadith book JPEGs) -> cover_files
            if re.search(r"[\u0980-\u09ff]{3,}", name) and not re.search(r"(?i)(?:page|scan|img|part|\d{4,})", name) and not JUNK_IMAGE_PAT.search(name):
                cover_files[f["id"]] = f
                continue
            # 6. Any other image in pdf/: portrait thumbnail or ungrouped page-scan candidate
            if f["parent_id"] in already_book_fids:
                cover_files[f["id"]] = f
                continue
            scan_groups[f"dir::{f['parent_id']}"].append(f)
            continue

        if ext in EBOOK_EXTS or not ext:
            ebooks.append(f)
        else:
            junk_to_trash.append(f)

    # Filter JUNK_IMAGE_PAT first, then trash any dir:: bucket with < 3 genuine pages!
    genuine_scan_groups: dict[str, list[dict]] = {}
    for gkey, imgs in scan_groups.items():
        kept = []
        for img in imgs:
            if JUNK_IMAGE_PAT.search(img["name"]):
                junk_to_trash.append(img)
            else:
                kept.append(img)
        if gkey.startswith("dir::") and len(kept) < 3:
            junk_to_trash.extend(kept)
        elif kept:
            genuine_scan_groups[gkey] = sorted(kept, key=lambda x: x["name"])

    # Deduplicate Drive text JSONs (keep eb_upload_state canonical file_id + NFC)
    eb_uploaded_fids = idx["eb_uploaded_fids"]
    seen_text_keys: dict[tuple[str, int], dict] = {}
    valid_text_files: list[dict] = []
    text_by_fid_sorted = sorted(
        text_files,
        key=lambda x: (
            0 if x["id"] in eb_uploaded_fids else 1,
            0 if unicodedata.normalize("NFC", x["raw_name"]) == x["raw_name"] else 1,
            x["modifiedTime"],
        ),
    )
    seen_text_folded: set[str] = set()
    for tf in text_by_fid_sorted:
        if Path(tf["name"]).suffix.lower() != ".json":
            junk_to_trash.append(tf)
            continue
        fk = tc.fold_bengali_key(Path(tf["name"]).stem)
        if tf["id"] not in eb_uploaded_fids and fk in seen_text_folded:
            junk_to_trash.append(tf)
            continue
        seen_text_folded.add(fk)
        valid_text_files.append(tf)

    return {
        "ebooks": ebooks,
        "text_files": valid_text_files,
        "cover_files": cover_files,
        "vol_pics": vol_pics,
        "scan_groups": genuine_scan_groups,
        "junk_to_trash": junk_to_trash,
        "already_merged_files": already_merged_files,
    }


def _derive_parent_book_prefix(orig_source_path: str) -> str:
    """Extract meaningful book-series folder name from original Drive source_path."""
    if not orig_source_path:
        return ""
    segs = [s.strip() for s in orig_source_path.split("/") if s.strip()]
    if not segs:
        return ""
    last = segs[-1]
    if GENERIC_PARENT_DIR_RE.search(last):
        return ""
    # Convert CamelCase folder names like SreeModaVagbathGita / UpanishatGranthabaliVol-1-2-3 cleanly
    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", last)
    cleaned = tc.strip_watermarks_and_noise(cleaned)
    return tc.fix_unicode_nfc(cleaned)


def resolve_ebook_metadata(f: dict, idx: dict[str, Any], folders: dict[str, dict], inspect_opaque: bool = False) -> dict[str, Any]:
    fid = f["id"]
    ext = Path(f["name"]).suffix.lower() or (".pdf" if "pdf" in f["mimeType"] else ".epub")
    ex = idx["extra_by_fid"].get(fid) or {}
    src_rec = idx["source_by_fid"].get(fid) or {}
    cov_rec = idx["book_covers"].get(fid) or {}

    raw_stem = Path(f["name"]).stem
    if not Path(f["name"]).suffix and f["mimeType"] == "application/pdf":
        raw_stem = f["name"]

    orig_source_path = tc.fix_unicode_nfc(src_rec.get("source_path") or "")
    effective_source_path = orig_source_path or f["rel_path"]

    # Determine initial legacy leaf from rel_path (skip leading pdf/ and trailing author subfolders if non-canonical)
    parts = [p for p in f["rel_path"].split("/")[:-1] if p != "pdf"]
    existing_leaf = ""
    for depth in (3, 2, 1):
        cand = "/".join(parts[:depth])
        if cand in cc.CANONICAL_LEAVES:
            existing_leaf = cand
            break
    if not existing_leaf and parts:
        existing_leaf = "/".join(parts)

    author = tc.fix_unicode_nfc(ex.get("author") or cov_rec.get("author") or "")
    if author in ("Various / Unknown", "Various / Internet Archive"):
        author = ""
    publication = ex.get("publication") or cov_rec.get("source") or src_rec.get("source_collection") or ""

    # Normalize q1..q16 মাসিক আল-আবরার opaque issues cleanly
    m_q = re.match(r"(?i)^q(\d+)$", raw_stem.strip())
    raw_known = tc.fix_unicode_nfc(ex.get("internal_title") or cov_rec.get("title") or "")
    if m_q and "আল-আবরার" in raw_known:
        known_title = f"মাসিক আল-আবরার - সংখ্যা {int(m_q.group(1)):02d}"
    elif raw_known and BAD_INTERNAL_TITLE_RE.search(raw_known):
        known_title = ""
    else:
        known_title = raw_known

    # Prepend parent book/series folder when stem is generic chapter/part/page/index (or underscore placeholder)
    clean_stem_try = tc.clean_book_stem(raw_stem, author=author, known_title=known_title)
    if GENERIC_CHAPTER_STEM_RE.match(raw_stem.strip()) and (not known_title or tc.is_opaque_stem(clean_stem_try)):
        parent_book = _derive_parent_book_prefix(orig_source_path)
        if parent_book:
            if re.match(r"^_+$", raw_stem.strip()):
                clean_stem_try = tc.clean_book_stem(parent_book, author=author)
            else:
                suffix = raw_stem.strip().strip("_ ")
                clean_stem_try = tc.clean_book_stem(f"{parent_book} - {suffix}", author=author)

    # Check cached or live isolated internal title extraction if STILL opaque / Bijoy
    if tc.is_opaque_stem(clean_stem_try) or tc.is_likely_bijoy(clean_stem_try):
        cached = idx["int_cache"].get(fid, "")
        extracted = cached if cached and not BAD_INTERNAL_TITLE_RE.search(cached) else ""
        if not extracted and inspect_opaque and fid not in idx["int_cache"]:
            extracted = extract_internal_title_from_drive(fid, ext, size=f.get("size", 0))
            with _LOCK:
                idx["int_cache"][fid] = extracted
        if extracted:
            known_title = extracted
            clean_stem_try = tc.clean_book_stem(extracted, author=author, known_title=extracted)

    clean_stem = clean_stem_try or tc.sanitize_filename(raw_stem) or f"Book_{fid[:8]}"
    tk, ak = normalize_match_pair(clean_stem, author)

    return {
        "file": f,
        "fid": fid,
        "ext": ext,
        "clean_stem": clean_stem,
        "author": author,
        "publication": publication,
        "existing_leaf": "" if tc.is_opaque_stem(raw_stem) else existing_leaf,
        "source_path": "" if tc.is_opaque_stem(raw_stem) else effective_source_path,
        "cover_drive_id": ex.get("cover_drive_id") or cov_rec.get("cover_drive_id") or "",
        "cover_url": ex.get("cover_url") or cov_rec.get("cover_url") or "",
        "thumbnail_url": ex.get("thumbnail_url") or cov_rec.get("thumbnail_url") or "",
        "book_url": cov_rec.get("book_url") or "",
        "tk": tk,
        "ak": ak,
        "vol_tag": extract_vol_tag(clean_stem),
    }


def resolve_text_metadata(tf: dict, idx: dict[str, Any]) -> dict[str, Any]:
    fid = tf["id"]
    eb = idx["eb_id_to_rec"].get(fid)
    raw_stem = Path(tf["name"]).stem
    if not eb:
        tk0, ak0 = normalize_match_pair(raw_stem)
        eb = idx["eb_by_tk_ak"].get((tk0, ak0)) or {}
        if not eb and ak0:
            # Try title only lookup from title
            t_only = raw_stem.rsplit(" - ", 1)[0].strip() if " - " in raw_stem else raw_stem
            a_only = raw_stem.rsplit(" - ", 1)[1].strip() if " - " in raw_stem else ""
            eb = idx["eb_by_tk_ak"].get(normalize_match_pair(t_only, a_only)) or {}

    title = tc.fix_unicode_nfc(eb.get("real_title") or eb.get("title") or "")
    author = tc.fix_unicode_nfc(eb.get("author") or "")
    if " - " in title and author and title.endswith(f" - {author}"):
        title = title[: -len(f" - {author}")].strip()
    genres = eb.get("genres") or []
    parts = [p for p in tf["rel_path"].split("/")[:-1] if p != "text"]
    existing_leaf = "/".join(parts) if parts else ""

    clean_stem = tc.clean_book_stem(raw_stem, author=author, known_title=title)
    tk, ak = normalize_match_pair(clean_stem, author)
    return {
        "file": tf,
        "fid": fid,
        "clean_stem": clean_stem,
        "title": title or clean_stem,
        "author": author,
        "genres": genres,
        "existing_leaf": existing_leaf,
        "cover_drive_id": eb.get("cover_drive_id") or "",
        "cover_url": eb.get("cover_url") or "",
        "thumbnail_url": eb.get("thumbnail_url") or "",
        "book_url": eb.get("url") or "",
        "tk": tk,
        "ak": ak,
        "vol_tag": extract_vol_tag(clean_stem),
    }


def match_and_build_units(
    classified: dict[str, Any],
    idx: dict[str, Any],
    folders: dict[str, dict],
    inspect_opaque: bool = False,
) -> tuple[list[dict[str, Any]], list[dict]]:
    extra_trash: list[dict] = []
    # 1. Deduplicate identical ebooks in the same leaf/parent (same folded title+ext+size)
    raw_ebooks: list[dict[str, Any]] = [{}] * len(classified["ebooks"])
    if inspect_opaque:
        print(f"Resolving ebook metadata (threaded inspect_opaque over {len(classified['ebooks']):,} files)...", flush=True)
        done_res = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = {
                pool.submit(resolve_ebook_metadata, f, idx, folders, True): i
                for i, f in enumerate(classified["ebooks"])
            }
            for fut in as_completed(futs):
                raw_ebooks[futs[fut]] = fut.result()
                done_res += 1
                if done_res % 1000 == 0 or done_res == len(raw_ebooks):
                    print(f"  Resolved {done_res:,}/{len(raw_ebooks):,} ebooks", flush=True)
        atomic_write_json(DATA / "internal_title_cache.json", idx["int_cache"])
    else:
        raw_ebooks = [resolve_ebook_metadata(f, idx, folders, inspect_opaque=False) for f in classified["ebooks"]]
    eb_dedup_seen: dict[tuple[str, str, int], dict] = {}
    unique_ebooks: list[dict] = []
    for em in sorted(raw_ebooks, key=lambda x: (0 if unicodedata.normalize("NFC", x["file"]["raw_name"]) == x["file"]["raw_name"] else 1, x["file"]["modifiedTime"])):
        k = (tc.fold_bengali_key(em["clean_stem"]), em["ext"], em["file"]["size"])
        if k in eb_dedup_seen and em["file"]["size"] > 0:
            extra_trash.append(em["file"])
            continue
        eb_dedup_seen[k] = em
        unique_ebooks.append(em)

    # 2. Index text files for matching against ebooks
    text_metas = [resolve_text_metadata(tf, idx) for tf in classified["text_files"]]
    text_by_tk_ak: dict[tuple[str, str], list[dict]] = defaultdict(list)
    text_by_tk: dict[str, list[dict]] = defaultdict(list)
    for tm in text_metas:
        text_by_tk_ak[(tm["tk"], tm["ak"])].append(tm)
        text_by_tk[tm["tk"]].append(tm)

    used_text_fids: set[str] = set()
    cover_files = classified["cover_files"]
    vol_pics = classified["vol_pics"]
    pdf_named_covers: dict[str, str] = {
        tc.fold_bengali_key(tc.clean_book_stem(Path(cf["name"]).stem)): cf["id"]
        for cf in cover_files.values()
        if cf["rel_path"].startswith("pdf/")
    }

    # Helper to attach Vivekananda vol_N_pic.jpg if cover missing
    def find_vol_pic(em: dict) -> str:
        s = em["clean_stem"]
        if "বিবেকানন্দ" in s or "vivekananda" in s.lower():
            vt = extract_vol_tag(s)
            if vt in vol_pics:
                return vol_pics[vt]["id"]
        return ""

    # 3. Group ebooks with identical (leaf, clean_stem) OR distinct ebooks -> book units
    units_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    used_vol_pics: set[str] = set()

    for em in unique_ebooks:
        # Match Text JSON by exact (tk, ak) or fallback unambiguous tk
        matched_tm = None
        for cand in text_by_tk_ak.get((em["tk"], em["ak"]), []):
            if cand["fid"] not in used_text_fids:
                matched_tm = cand
                break
        if matched_tm is None and em["tk"]:
            cands = [c for c in text_by_tk.get(em["tk"], []) if c["fid"] not in used_text_fids]
            if len(cands) == 1 and (not em["ak"] or tc._authors_equivalent(em["author"], cands[0]["author"])):
                matched_tm = cands[0]

        if matched_tm:
            used_text_fids.add(matched_tm["fid"])

        best_author = em["author"] or (matched_tm["author"] if matched_tm else "")
        best_title = em["clean_stem"]
        genres = matched_tm["genres"] if matched_tm else None
        ex_leaf = em["existing_leaf"] or (matched_tm["existing_leaf"] if matched_tm else "")
        leaf = cc.classify_clean_leaf(
            title=best_title,
            author=best_author,
            genres=genres,
            existing_leaf=ex_leaf,
            publication=em["publication"],
            source_path=em["source_path"],
        )
        cov_id = em["cover_drive_id"] or (matched_tm["cover_drive_id"] if matched_tm else "")
        if cov_id and cov_id not in cover_files:
            # Might already be moved/copied or missing; keep ID check
            pass
        if not cov_id:
            vpid = find_vol_pic(em)
            if vpid:
                cov_id = vpid
                used_vol_pics.add(vpid)
            elif em["tk"] in pdf_named_covers:
                cov_id = pdf_named_covers[em["tk"]]

        # Preserve NCTB Class separations in key via leaf!
        u_key = (leaf, tc.fold_bengali_key(best_title))
        unit = units_by_key.get(u_key)
        if unit is None:
            unit = {
                "leaf": leaf,
                "folder_name": safe_book_folder_name(best_title, f"Book_{em['fid'][:8]}"),
                "title": best_title,
                "author": best_author or "Various / Unknown",
                "publication": em["publication"] or ("eBanglaLibrary (ebanglalibrary.com)" if matched_tm else ""),
                "ebook_files": [],
                "text_files": [],
                "cover_drive_id": cov_id,
                "cover_url": em["cover_url"] or (matched_tm["cover_url"] if matched_tm else ""),
                "thumbnail_url": em["thumbnail_url"] or (matched_tm["thumbnail_url"] if matched_tm else ""),
                "book_url": em["book_url"] or (matched_tm["book_url"] if matched_tm else ""),
                "is_scan_group": False,
            }
            units_by_key[u_key] = unit

        unit["ebook_files"].append(em["file"])
        if matched_tm:
            unit["text_files"].append(matched_tm["file"])
            if not unit["cover_drive_id"] and matched_tm["cover_drive_id"]:
                unit["cover_drive_id"] = matched_tm["cover_drive_id"]

    # 4. Create Book Units for unmatched Text JSONs (eBanglaLibrary HTML-to-JSON books)
    for tm in text_metas:
        if tm["fid"] in used_text_fids:
            continue
        leaf = cc.classify_clean_leaf(
            title=tm["clean_stem"],
            author=tm["author"],
            genres=tm["genres"],
            existing_leaf=tm["existing_leaf"],
            publication="eBanglaLibrary",
        )
        u_key = (leaf, tc.fold_bengali_key(tm["clean_stem"]))
        unit = units_by_key.get(u_key)
        if unit is None:
            unit = {
                "leaf": leaf,
                "folder_name": safe_book_folder_name(tm["clean_stem"], f"Book_{tm['fid'][:8]}"),
                "title": tm["clean_stem"],
                "author": tm["author"] or "Various / Unknown",
                "publication": "eBanglaLibrary (ebanglalibrary.com)",
                "ebook_files": [],
                "text_files": [tm["file"]],
                "cover_drive_id": tm["cover_drive_id"],
                "cover_url": tm["cover_url"],
                "thumbnail_url": tm["thumbnail_url"],
                "book_url": tm["book_url"],
                "is_scan_group": False,
            }
            units_by_key[u_key] = unit
        else:
            unit["text_files"].append(tm["file"])

    # Unused vol_N_pic.jpg images -> attach to Constitution/Vivekananda if leftover or trash cleanly
    for vn, vf in vol_pics.items():
        if vf["id"] not in used_vol_pics:
            extra_trash.append(vf)

    # 5. Add multi-page scan groups as single clean Book Units
    scan_presets = {
        "constitution_bn": ("Law and Legal/Constitutional Law", "বাংলাদেশের সংবিধান (Constitution of Bangladesh)", "Government of Bangladesh"),
        "qasida_shah_neyamatullah": ("Literature/Poetry", "কাসিদায়ে শাহ্ নেয়ামতুল্লাহ্", "শাহ্ নেয়ামতুল্লাহ্"),
        "ami_bibekananda_bolchhi": ("Religion/Hinduism", "আমি বিবেকানন্দ বলছি - স্বামী বিবেকানন্দ", "স্বামী বিবেকানন্দ"),
    }
    for gkey, imgs in classified["scan_groups"].items():
        if gkey in scan_presets:
            leaf, title, auth = scan_presets[gkey]
        else:
            p_id = gkey.split("::", 1)[1]
            p_name = tc.clean_book_stem(folders.get(p_id, {}).get("name") or f"Scanned Book {p_id[:6]}")
            rel = folders.get(p_id, {}).get("rel_path") or ""
            leaf = cc.classify_clean_leaf(title=p_name, existing_leaf=rel, source_path=rel)
            title, auth = p_name, "Various / Unknown"
        units_by_key[(leaf, f"scan::{gkey}")] = {
            "leaf": leaf,
            "folder_name": safe_book_folder_name(title, f"Scan_{gkey[:8]}"),
            "title": title,
            "author": auth,
            "publication": "Scanned Book Edition",
            "ebook_files": imgs,
            "text_files": [],
            "cover_drive_id": imgs[0]["id"] if imgs else "",
            "cover_url": "",
            "thumbnail_url": "",
            "book_url": "",
            "is_scan_group": True,
        }

    # 6. Guarantee unique folder_name inside each leaf
    units_list = list(units_by_key.values())
    used_names_per_leaf: dict[str, set[str]] = defaultdict(set)
    for u in units_list:
        leaf = u["leaf"]
        base = u["folder_name"]
        cand = base
        suffix_n = 2
        while cand.lower() in used_names_per_leaf[leaf]:
            cand = f"{base} ({suffix_n})"
            suffix_n += 1
        used_names_per_leaf[leaf].add(cand.lower())
        u["folder_name"] = cand

    return units_list, extra_trash


def run_batch_chunks(ops: list[dict], chunk_size: int = 50, workers: int = 4, label: str = "ops") -> int:
    """Execute disjoint batch operations with parallel workers, grouping by fileId to prevent races."""
    if not ops:
        return 0
    # Group ops keeping identical fileId inside the SAME chunk so moves/renames execute sequentially per file!
    by_fid: dict[str, list[dict]] = defaultdict(list)
    no_fid: list[dict] = []
    for op in ops:
        fid = op.get("fileId")
        if fid:
            by_fid[fid].append(op)
        else:
            no_fid.append(op)

    chunks: list[list[dict]] = []
    cur: list[dict] = []
    for fops in by_fid.values():
        if len(cur) + len(fops) > chunk_size and cur:
            chunks.append(cur)
            cur = []
        cur.extend(fops)
    for op in no_fid:
        if len(cur) >= chunk_size:
            chunks.append(cur)
            cur = []
        cur.append(op)
    if cur:
        chunks.append(cur)

    done = 0
    failed_ops = 0
    eff_workers = min(workers, 2)
    with ThreadPoolExecutor(max_workers=eff_workers) as ex:
        futs = {ex.submit(gd_batch, ch): ch for ch in chunks}
        for idx, fut in enumerate(as_completed(futs), 1):
            ok, msg = fut.result()
            ch = futs[fut]
            if ok:
                done += len(ch)
            else:
                print(f"  WARN batch {idx}/{len(chunks)} failed ({msg[:120]}), retrying individually...", flush=True)
                for single in ch:
                    s_ok, s_msg = gd_batch([single], timeout=90, retries=5)
                    if s_ok:
                        done += 1
                    else:
                        failed_ops += 1
                        print(f"  ERROR op failed permanently: {single} -> {s_msg[:120]}", flush=True)
            if idx % 20 == 0 or idx == len(chunks):
                print(f"  [{label}] batch {idx}/{len(chunks)} ({done}/{len(ops)} ops, failed={failed_ops})", flush=True)
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge books into clean <Category>/<Leaf>/<Clean Book Name>/ folders")
    ap.add_argument("--plan-only", action="store_true", help="Audit Drive & build plan without mutating Drive")
    ap.add_argument("--inspect-opaque", action="store_true", help="Download remaining opaque PDFs to inspect internal titles")
    ap.add_argument("--rescan", action="store_true", help="Force fresh live Google Drive BFS scan instead of cached snapshot")
    ap.add_argument("--use-snapshot", action="store_true", help="Reuse data/live_drive_snapshot.json even in execute mode")
    ap.add_argument("--workers", type=int, default=10, help="Concurrent workers for mkdir creation")
    args = ap.parse_args()

    merge_state_p = DATA / "merge_state.json"
    merge_state: dict[str, Any] = (
        json.loads(merge_state_p.read_text(encoding="utf-8"))
        if merge_state_p.exists()
        else {"created_book_folders": {}, "moved_covers": {}, "completed_units": []}
    )

    print("Loading metadata indexes...", flush=True)
    idx = load_metadata_indexes()
    snap_p = DATA / "live_drive_snapshot.json"
    use_cached_snap = snap_p.exists() and not args.rescan and (args.plan_only or args.use_snapshot)
    if use_cached_snap:
        print("Loading cached Drive tree from data/live_drive_snapshot.json...", flush=True)
        snap = json.loads(snap_p.read_text(encoding="utf-8"))
        folders, files = snap["folders"], snap["files"]
    else:
        print("Scanning live Google Drive tree via stream ls...", flush=True)
        folders, files = stream_bfs_drive(ROOT_DRIVE_ID)
        atomic_write_json(snap_p, {"folders": folders, "files": files})
    print(f"Live Drive scan: {len(folders)} folders | {len(files)} files", flush=True)

    classified = classify_drive_tree(folders, files, idx, merge_state)
    units, extra_trash = match_and_build_units(classified, idx, folders, inspect_opaque=args.inspect_opaque)
    all_trash = classified["junk_to_trash"] + extra_trash

    # Summary stats
    both_cnt = sum(1 for u in units if u["ebook_files"] and u["text_files"])
    eb_only = sum(1 for u in units if u["ebook_files"] and not u["text_files"])
    tx_only = sum(1 for u in units if u["text_files"] and not u["ebook_files"])
    cov_cnt = sum(1 for u in units if u["cover_drive_id"])
    others_cnt = sum(1 for u in units if u["leaf"].startswith("Others"))
    opaque_cnt = sum(1 for u in units if tc.is_opaque_stem(u["title"]))

    print("=== MERGE PLAN SUMMARY ===", flush=True)
    print(f"  Total Merged Book Folders : {len(units):,}", flush=True)
    print(f"    - Ebook + Text JSON     : {both_cnt:,}", flush=True)
    print(f"    - Ebook only            : {eb_only:,}", flush=True)
    print(f"    - Text JSON only        : {tx_only:,}", flush=True)
    print(f"    - With Cover Image      : {cov_cnt:,}", flush=True)
    print(f"    - Page-Scan Groups      : {sum(1 for u in units if u['is_scan_group']):,}", flush=True)
    print(f"    - In 'Others' Leaf      : {others_cnt:,}", flush=True)
    print(f"    - Still Opaque Titles   : {opaque_cnt:,}", flush=True)
    print(f"  Junk / Dupes to Trash     : {len(all_trash):,}", flush=True)

    if args.plan_only:
        plan_preview = [
            {
                "leaf": u["leaf"],
                "folder_name": u["folder_name"],
                "author": u["author"],
                "ebooks": [x["name"] for x in u["ebook_files"]],
                "texts": [x["name"] for x in u["text_files"]],
                "has_cover": bool(u["cover_drive_id"]),
            }
            for u in units[:30]
        ]
        atomic_write_json(DATA / "merge_plan_preview.json", plan_preview, indent=2)
        if opaque_cnt:
            op_samples = [u["title"] for u in units if tc.is_opaque_stem(u["title"])][:20]
            print("  Sample opaque titles:", op_samples, flush=True)
        return

    # 1. Trash junk & duplicates
    trash_ops = [{"op": "trash", "fileId": f["id"]} for f in all_trash if f["id"] not in idx["trashed"]]
    if trash_ops:
        print(f"Step 1: Trashing {len(trash_ops)} junk & duplicate files...", flush=True)
        run_batch_chunks(trash_ops, chunk_size=50, workers=4, label="trash")
        idx["trashed"].update(op["fileId"] for op in trash_ops)
        atomic_write_json(DATA / "trashed_ids.json", sorted(idx["trashed"]), indent=2)

    # 2. Promote 25 clean categories directly to ROOT_DRIVE_ID & ensure all 256 canonical leaves
    print("Step 2: Promoting 25 clean categories to Drive Root & verifying 256 leaves...", flush=True)
    root_children = {f["name"]: fid for fid, f in folders.items() if f["parent_id"] == ROOT_DRIVE_ID}
    pdf_fid = root_children.get("pdf")
    clean_folders: dict[str, str] = {}

    # Identify existing category/leaf folder IDs from live scan (either already at Root or under pdf/)
    for fid, finfo in folders.items():
        rel = finfo["rel_path"]
        stripped = rel[4:] if rel.startswith("pdf/") else rel
        if stripped in cc.CANONICAL_LEAVES or stripped in CANONICAL_TOP_CATS or stripped == "Religion/Islam":
            clean_folders[stripped] = fid

    promote_ops = []
    for cat in CANONICAL_TOP_CATS:
        if cat in root_children:
            clean_folders[cat] = root_children[cat]
        elif cat in clean_folders:
            promote_ops.append({"op": "move", "fileId": clean_folders[cat], "dest": ROOT_DRIVE_ID})
        else:
            new_cid = gd_mkdir(cat, ROOT_DRIVE_ID)
            if not new_cid:
                raise RuntimeError(f"Failed creating top category {cat}")
            clean_folders[cat] = new_cid

    if promote_ops:
        run_batch_chunks(promote_ops, chunk_size=25, workers=2, label="promote-cats")

    # Ensure every canonical intermediate & leaf path exists cleanly
    for leaf in sorted(cc.CANONICAL_LEAVES):
        parts = leaf.split("/")
        cur_p = ""
        parent_id = ROOT_DRIVE_ID
        for part in parts:
            cur_p = f"{cur_p}/{part}" if cur_p else part
            if cur_p in clean_folders:
                parent_id = clean_folders[cur_p]
                continue
            new_id = gd_mkdir(part, parent_id)
            if not new_id:
                raise RuntimeError(f"Failed creating leaf folder {cur_p}")
            clean_folders[cur_p] = new_id
            parent_id = new_id

    atomic_write_json(DATA / "clean_folders.json", clean_folders, indent=2)

    # Pre-load existing subfolders inside every canonical leaf so resume never creates duplicate book folders
    leaf_existing_children: dict[str, dict[str, str]] = defaultdict(dict)
    for fid, finfo in folders.items():
        pid = finfo["parent_id"]
        if pid in set(clean_folders.values()):
            leaf_existing_children[pid][finfo["name"].lower()] = fid

    # 3. Create missing <Clean Book Name>/ folders in parallel
    print(f"Step 3: Creating/resolving {len(units)} clean per-book folders...", flush=True)
    todo_mkdir: list[tuple[str, str, str, str]] = []  # (unit_uid, leaf_id, folder_name, leaf)
    for u in units:
        uid = f"{u['leaf']}||{u['folder_name']}"
        u["uid"] = uid
        leaf_id = clean_folders[u["leaf"]]
        if uid in merge_state["created_book_folders"]:
            u["book_folder_id"] = merge_state["created_book_folders"][uid]
        elif u["folder_name"].lower() in leaf_existing_children[leaf_id]:
            bfid = leaf_existing_children[leaf_id][u["folder_name"].lower()]
            u["book_folder_id"] = bfid
            merge_state["created_book_folders"][uid] = bfid
        else:
            todo_mkdir.append((uid, leaf_id, u["folder_name"], u["leaf"]))

    if todo_mkdir:
        created_cnt = 0
        for attempt_mk in range(2):
            todo_round = [x for x in todo_mkdir if x[0] not in merge_state["created_book_folders"]]
            if not todo_round:
                break
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futs = {ex.submit(gd_mkdir, fname, lid): (uid, fname) for uid, lid, fname, _ in todo_round}
                for fut in as_completed(futs):
                    uid, fname = futs[fut]
                    bfid = fut.result()
                    if bfid:
                        with _LOCK:
                            merge_state["created_book_folders"][uid] = bfid
                            created_cnt += 1
                    elif attempt_mk == 1:
                        print(f"  WARN mkdir failed after retry: {uid}", flush=True)
                    if created_cnt % 100 == 0 or created_cnt == len(todo_mkdir):
                        print(f"  Created {created_cnt}/{len(todo_mkdir)} book folders", flush=True)
                        atomic_write_json(merge_state_p, merge_state)

        for u in units:
            if "book_folder_id" not in u:
                u["book_folder_id"] = merge_state["created_book_folders"].get(u["uid"], "")
        atomic_write_json(merge_state_p, merge_state)

    # 4. Build move + rename + cover copy ops into each book folder
    print("Step 4: Moving & renaming PDFs, Text JSONs, and Covers into per-book folders...", flush=True)
    completed_set = set(merge_state.get("completed_units", []))
    moved_covers: dict[str, str] = merge_state.get("moved_covers", {})
    file_ops: list[dict] = []
    copy_ops: list[tuple[dict, str, str, str]] = []  # (unit, src_cov_id, target_name, dest_folder_id)

    for u in units:
        bfid = u.get("book_folder_id")
        if not bfid or u["uid"] in completed_set:
            continue
        fname = u["folder_name"]

        # Ebooks
        if u["is_scan_group"]:
            for idx_p, ef in enumerate(u["ebook_files"], 1):
                ext = Path(ef["name"]).suffix.lower() or ".jpg"
                target_n = f"Page {idx_p:03d}{ext}"
                if ef["parent_id"] != bfid:
                    file_ops.append({"op": "move", "fileId": ef["id"], "dest": bfid})
                if ef["name"] != target_n:
                    file_ops.append({"op": "rename", "fileId": ef["id"], "name": target_n})
        else:
            for idx_e, ef in enumerate(u["ebook_files"], 1):
                ext = Path(ef["name"]).suffix.lower() or ".pdf"
                target_n = f"{fname}{ext}" if len(u["ebook_files"]) == 1 else f"{fname} ({idx_e}){ext}"
                if ef["parent_id"] != bfid:
                    file_ops.append({"op": "move", "fileId": ef["id"], "dest": bfid})
                if ef["name"] != target_n:
                    file_ops.append({"op": "rename", "fileId": ef["id"], "name": target_n})

        # Text JSONs
        for idx_t, tf in enumerate(u["text_files"], 1):
            target_n = f"{fname}.json" if len(u["text_files"]) == 1 else f"{fname} ({idx_t}).json"
            if tf["parent_id"] != bfid:
                file_ops.append({"op": "move", "fileId": tf["id"], "dest": bfid})
            if tf["name"] != target_n:
                file_ops.append({"op": "rename", "fileId": tf["id"], "name": target_n})

        # Covers (skip separate cover op if scan_group already moved imgs[0] into folder)
        cid = u.get("cover_drive_id")
        if cid and not u["is_scan_group"]:
            cfile = classified["cover_files"].get(cid) or next((vf for vf in classified["vol_pics"].values() if vf["id"] == cid), None)
            cext = (Path(cfile["name"]).suffix.lower() if cfile else "") or ".jpg"
            if cext not in IMAGE_EXTS:
                cext = ".jpg"
            cov_target = f"{fname}{cext}"
            if cid not in moved_covers and cfile is not None:
                if cfile["parent_id"] != bfid:
                    file_ops.append({"op": "move", "fileId": cid, "dest": bfid})
                if cfile["name"] != cov_target:
                    file_ops.append({"op": "rename", "fileId": cid, "name": cov_target})
                moved_covers[cid] = bfid
            elif moved_covers.get(cid) != bfid:
                copy_ops.append((u, cid, cov_target, bfid))

    if file_ops:
        print(f"  Executing {len(file_ops)} move/rename ops...", flush=True)
        run_batch_chunks(file_ops, chunk_size=50, workers=6, label="move-rename")

    if copy_ops:
        print(f"  Executing {len(copy_ops)} shared-cover copy ops...", flush=True)
        c_batch = [{"op": "copy", "fileId": cid, "name": cname, "parentId": bfid} for _, cid, cname, bfid in copy_ops]
        run_batch_chunks(c_batch, chunk_size=40, workers=6, label="copy-covers")

    merge_state["moved_covers"] = moved_covers
    merge_state["completed_units"] = sorted({u["uid"] for u in units if u.get("book_folder_id")})
    atomic_write_json(merge_state_p, merge_state)

    # 5. Re-scan root & trash empty legacy containers (pdf/, text/, covers/, empty author subfolders)
    print("Step 5: Verifying clean layout & trashing empty legacy folders...", flush=True)
    canon_ids = set(clean_folders.values())
    book_fid_set = set(merge_state["created_book_folders"].values())
    legacy_ids = [
        fid for fid, finfo in folders.items()
        if fid not in canon_ids and fid not in book_fid_set and fid != ROOT_DRIVE_ID
    ]
    if legacy_ids:
        empty_trash = []
        ls_check = stream_ls_many(legacy_ids)
        children_count: dict[str, int] = defaultdict(int)
        for fid, items in ls_check.items():
            for it in items:
                if it.get("mimeType") != "application/vnd.google-apps.folder":
                    children_count[fid] += 1
        for fid in legacy_ids:
            rel_f = folders[fid]["rel_path"]
            has_files = any(
                cnt > 0 and (folders[cfid]["rel_path"] == rel_f or folders[cfid]["rel_path"].startswith(rel_f + "/"))
                for cfid, cnt in children_count.items()
                if cfid in folders
            )
            if not has_files:
                empty_trash.append({"op": "trash", "fileId": fid})
        print(f"  Verified {len(empty_trash)}/{len(legacy_ids)} legacy containers are empty -> trashing cleanly", flush=True)
        if empty_trash:
            run_batch_chunks(empty_trash, chunk_size=50, workers=4, label="trash-empty-legacy")

    # 6. Final live verification scan of merged book folders -> write merged_books.json!
    print("Step 6: Exporting data/merged_books.json from merged book folders...", flush=True)
    book_fids = [u["book_folder_id"] for u in units if u.get("book_folder_id")]
    bf_ls = stream_ls_many(book_fids, max_per_folder=200)
    merged_records = []
    for u in units:
        bfid = u.get("book_folder_id")
        if not bfid:
            continue
        contents = bf_ls.get(bfid, [])
        pdf_id = ""
        epub_id = ""
        text_id = ""
        cov_id = ""
        other_id = ""
        total_size = 0
        fmts = []
        file_list = []
        for it in contents:
            sz = int(it.get("size") or 0)
            total_size += sz
            ext = Path(it.get("name") or "").suffix.lower()
            file_list.append({"id": it["id"], "name": it["name"], "size": sz, "mimeType": it.get("mimeType") or ""})
            if ext == ".pdf" and not pdf_id:
                pdf_id = it["id"]
                fmts.append("PDF")
            elif ext == ".epub" and not epub_id:
                epub_id = it["id"]
                fmts.append("EPUB")
            elif ext == ".json" and not text_id:
                text_id = it["id"]
                fmts.append("TEXT")
            elif ext in IMAGE_EXTS and not cov_id:
                cov_id = it["id"]
                fmts.append("COVER")
            elif ext in EBOOK_EXTS and not other_id:
                other_id = it["id"]
                fmts.append(ext.lstrip(".").upper())

        primary_id = pdf_id or epub_id or other_id or text_id or bfid
        parts = u["leaf"].split("/")
        merged_records.append({
            "folder_id": bfid,
            "folder_link": f"https://drive.google.com/drive/folders/{bfid}",
            "file_id": primary_id,
            "link": f"https://drive.google.com/drive/folders/{bfid}",
            "name": u["folder_name"],
            "title": u["title"],
            "author": u["author"],
            "publication": u["publication"],
            "top_category": parts[0],
            "leaf_path": u["leaf"],
            "leaf_category": parts[-1],
            "size": total_size,
            "pdf_file_id": pdf_id,
            "epub_file_id": epub_id,
            "text_file_id": text_id,
            "cover_file_id": cov_id or u.get("cover_drive_id") or "",
            "cover_url": u.get("cover_url") or "",
            "thumbnail_url": u.get("thumbnail_url") or "",
            "book_url": u.get("book_url") or "",
            "formats": sorted(set(fmts)),
            "files": file_list,
        })

    atomic_write_json(DATA / "merged_books.json", merged_records)
    print(f"DONE! Saved {len(merged_records):,} merged book folders -> data/merged_books.json", flush=True)


if __name__ == "__main__":
    main()
