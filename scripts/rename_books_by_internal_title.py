import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

LANGUAGE_SERVER = r"C:\Users\USER\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"
GDRIVE_BASE = (
    [LANGUAGE_SERVER, "plugin-cli", "gdrive"]
    if Path(LANGUAGE_SERVER).exists()
    else [shutil.which("gdrive") or "gdrive"]
)
REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"

WATERMARK_PATTERNS = [
    r"\(?\s*(?:www\.)?(?:banglabook|bdebooks|ebanglalibrary|amarbooks|boimate|banglapdf|bengaliebooks|banglabooks|pdfbd|murchona|banglaebook|bDeBooks|ebookbd|islamicbook|kitabghor|pathagar)\.(?:com|org|net|info|xyz)\s*\)?",
    r"[\[(]\s*(?:www\.)?[a-z0-9-]+\.(?:com|org|net|xyz|info)\s*[\])]",
    r"-?tanbircox(?:\.blogspot\.com)?",
    r"\[?\s*fb\.com/[^\]]+\]?",
    r"[\[(]\s*(?:downloaded|uploaded|scanned|courtesy)\s+by[^\])\n]*[\])]",
    r"\s+by\s+(?:bdebooks|boimate|amarbooks|banglabook)\s*$",
]

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import title_cleaner as _tc

OPAQUE_STEM_RE = _tc.OPAQUE_STEM_RE

_EB_RAW_LOOKUP: dict[str, dict] | None = None


def _get_eb_raw(post_id: str = "", url: str = "") -> dict | None:
    global _EB_RAW_LOOKUP
    if _EB_RAW_LOOKUP is None:
        _EB_RAW_LOOKUP = {}
        raw_p = Path(__file__).resolve().parent.parent / "data" / "ebanglalibrary_raw.json"
        if raw_p.exists():
            try:
                import json as _json
                for row in _json.loads(raw_p.read_text(encoding="utf-8")):
                    if row.get("post_id"):
                        _EB_RAW_LOOKUP[f"pid:{row['post_id']}"] = row
                    if row.get("url"):
                        _EB_RAW_LOOKUP[f"url:{row['url']}"] = row
            except Exception:
                pass
    if post_id and f"pid:{post_id}" in _EB_RAW_LOOKUP:
        return _EB_RAW_LOOKUP[f"pid:{post_id}"]
    if url and f"url:{url}" in _EB_RAW_LOOKUP:
        return _EB_RAW_LOOKUP[f"url:{url}"]
    return None


def gd_run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        GDRIVE_BASE + args,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def sanitize_filename(name: str) -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", name)
    s = re.sub(r"\s+", " ", s).strip(" .'")
    if len(s) > 140:
        s = s[:140].strip()
    return s


def normalize_ext(name: str) -> tuple[str, str]:
    n = name.strip().rstrip("'\"")
    # Fix "something. PDF" or "somethingpdf" without dot
    n = re.sub(r"\.\s+(pdf|epub|docx?|pptx?|txt|zip)$", r".\1", n, flags=re.I)
    n = re.sub(r"(\.pdf)+$", ".pdf", n, flags=re.I)
    n = re.sub(r"(\.epub)+$", ".epub", n, flags=re.I)
    m = re.match(r"^(.+?)(pdf)$", n, re.I)
    if m and not n.lower().endswith(".pdf"):
        n = m.group(1).strip() + ".pdf"
    p = Path(n)
    return p.stem, p.suffix.lower()


def clean_book_filename(rec: dict) -> str:
    orig_name = rec.get("name") or ""
    stem, ext = normalize_ext(orig_name)
    if not ext:
        mt = (rec.get("mimeType") or "").lower()
        if "pdf" in mt:
            ext = ".pdf"
        elif "epub" in mt:
            ext = ".epub"
        elif "json" in mt:
            ext = ".json"

    sid = rec.get("source_id") or ""
    pub = rec.get("publication") or ""

    # 1. NCTB formatted internally: "<Book Name> - <Class> (NCTB <Year>).pdf"
    m_nctb = re.match(r"^NCTB\s+(\d{4})\s*-\s*(.+?)\s*\[([^\]]+)\]$", stem, re.I)
    if m_nctb:
        yr, book_title, bracket = m_nctb.groups()
        cls_clean = re.sub(rf"^{yr}\s+", "", bracket).strip()
        clean_t = sanitize_filename(f"{book_title.strip()} - {cls_clean} (NCTB {yr})")
        return f"{clean_t}{ext or '.pdf'}"

    # 2. If record carries explicit internal_title from website/ebook metadata
    ititle = (rec.get("internal_title") or "").strip()
    author = (rec.get("author") or "").strip()
    if sid.startswith("eb:"):
        pid = sid.split(":", 1)[1] if ":" in sid else ""
        raw_eb = _get_eb_raw(post_id=pid, url=rec.get("url") or "")
        if raw_eb:
            author = author or (raw_eb.get("author") or "").strip()
            eb_title = (raw_eb.get("title") or "").strip()
            if eb_title and (not ititle or len(eb_title) > len(ititle)):
                ititle = eb_title
    if ititle and (sid.startswith(("kb:", "eb:", "bde:"))):
        clean_stem = _tc.clean_book_stem(ititle, author=author)
        clean_stem = sanitize_filename(clean_stem)
        if clean_stem:
            return f"{clean_stem}{ext or '.pdf'}"

    # 3. Clean URLs, watermarks, underscores, leading track numbers, duplicate author
    s = stem
    for pat in WATERMARK_PATTERNS:
        s = re.sub(pat, " ", s, flags=re.I)

    # Remove leading numeric prefixes like "01_", "(10) ", "001 - " ONLY when followed by real words
    s = re.sub(r"^\(\s*[0-9০-৯]{1,3}\s*\)\s*", "", s)
    s = re.sub(r"^[0-9০-৯]{1,3}\s*[._-]\s*(?=[A-Za-z\u0980-\u09ff]{3,})", "", s)

    # Convert underscores to spaces when not mixed with Bengali sentence punctuation
    s = s.replace("_", " ")
    # Collapse repeated punctuation / dashes
    s = re.sub(r"\s*[-–—]{2,}\s*", " - ", s)
    s = re.sub(r"\(\s*\)|\[\s*\]", "", s)
    s = sanitize_filename(s)
    if not s:
        s = stem
    return f"{s}{ext}"


def extract_title_from_epub(epub_path: Path) -> str | None:
    try:
        with zipfile.ZipFile(epub_path, "r") as zf:
            opf_names = [n for n in zf.namelist() if n.lower().endswith(".opf")]
            for oname in opf_names:
                xml_bytes = zf.read(oname)
                root = ET.fromstring(xml_bytes)
                for elem in root.iter():
                    if elem.tag.lower().endswith("title") and elem.text and len(elem.text.strip()) >= 2:
                        return elem.text.strip()
    except Exception:
        pass
    return None


def extract_title_from_pdf(pdf_path: Path) -> str | None:
    try:
        import pypdf  # optional
        reader = pypdf.PdfReader(str(pdf_path))
        meta = reader.metadata
        if meta and getattr(meta, "title", None):
            t = str(meta.title).strip()
            if t and not OPAQUE_STEM_RE.match(t) and "microsoft word" not in t.lower() and not t.lower().endswith(".pdf"):
                return t
        if reader.pages:
            txt = (reader.pages[0].extract_text() or "").strip()
            for ln in txt.splitlines()[:8]:
                ln = ln.strip()
                if 4 <= len(ln) <= 100 and not re.match(r"^\d+$", ln):
                    return ln
    except Exception:
        pass
    # Fallback regex scan on first 64KB for /Title (...)
    try:
        head = pdf_path.read_bytes()[:65536]
        m = re.search(rb"/Title\s*\(([^()]{3,120})\)", head)
        if m:
            t = m.group(1).decode("utf-8", "ignore").strip()
            if t and not OPAQUE_STEM_RE.match(t) and "microsoft" not in t.lower() and ".doc" not in t.lower():
                return t
    except Exception:
        pass
    return None


def _extract_title_v2(file_id: str, ext: str, tmp_dir: Path) -> str | None:
    eff_ext = ext or ".pdf"
    out_path = tmp_dir / f"{file_id}{eff_ext}"
    try:
        res = gd_run(["readonly", "download", file_id, "--out", str(out_path)], timeout=90)
        if res.returncode != 0 or not out_path.exists():
            return None
        # EPUB OPF metadata extraction
        if eff_ext.lower() == ".epub":
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(out_path) as zf:
                opf_names = [n for n in zf.namelist() if n.lower().endswith(".opf")]
                if opf_names:
                    root_xml = ET.fromstring(zf.read(opf_names[0]))
                    dc_title = ""
                    dc_creator = ""
                    for elem in root_xml.iter():
                        tag = elem.tag.lower()
                        if tag.endswith("}title") or tag == "title":
                            if elem.text and elem.text.strip():
                                dc_title = elem.text.strip()
                        elif tag.endswith("}creator") or tag == "creator":
                            if elem.text and elem.text.strip():
                                dc_creator = elem.text.strip()
                    if dc_title:
                        return _tc.clean_book_stem(dc_title, author=dc_creator)
            return None
        # PDF extraction via PyMuPDF
        import pymupdf
        doc = pymupdf.open(str(out_path))
        try:
            meta_title = (doc.metadata or {}).get("title") or ""
            meta_title = _tc.strip_watermarks_and_noise(meta_title)
            if meta_title and not _tc.is_opaque_stem(meta_title) and not re.match(r"^(?:untitled|document|book|page|slide)\d*$", meta_title, re.I):
                return meta_title
            # Fallback to pages 0..2 first meaningful lines
            chunks: list[str] = []
            for pno in range(min(3, len(doc))):
                txt = doc[pno].get_text("text") or ""
                if txt.strip():
                    chunks.append(txt)
            combined = "\n".join(chunks)
            lines = []
            for ln in combined.splitlines():
                s = _tc.strip_watermarks_and_noise(ln)
                if not s or len(s) < 3 or len(s) > 120:
                    continue
                if re.search(r"(www\.|http|\.com|\.org|\.in|yanabi|amarboi|banglainternet|pathagar)", s, re.I):
                    continue
                if _tc.is_opaque_stem(s):
                    continue
                lines.append(s)
                if len(lines) >= 2:
                    break
            if lines:
                candidate = " - ".join(lines) if len(lines) == 2 and len(lines[0]) + len(lines[1]) < 95 else lines[0]
                return candidate
        finally:
            doc.close()
    except Exception:
        return None
    finally:
        if out_path.exists():
            out_path.unlink(missing_ok=True)
    return None


def inspect_opaque_file_title(file_id: str, ext: str, tmp_dir: Path) -> str | None:
    return _extract_title_v2(file_id, ext, tmp_dir)
    out_path = tmp_dir / f"{file_id}{ext}"
    try:
        res = gd_run(["readonly", "download", file_id, "--out", str(out_path)], timeout=60)
        if res.returncode != 0 or not out_path.exists():
            return None
        if ext == ".epub":
            return extract_title_from_epub(out_path)
        if ext == ".pdf":
            return extract_title_from_pdf(out_path)
    except Exception:
        return None
    finally:
        out_path.unlink(missing_ok=True)
    return None


def gd_rename(file_id: str, new_name: str) -> bool:
    try:
        res = gd_run(["mutate", "rename", file_id, new_name], timeout=30)
        return res.returncode == 0
    except Exception:
        return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    extra_file = DATA_DIR / "extra_books.json"
    plan_file = DATA_DIR / "copy_plan.json"
    progress_file = DATA_DIR / "catalog_progress.json"
    trashed_file = DATA_DIR / "trashed_ids.json"
    state_file = DATA_DIR / "book_rename_state.json"

    extra = json.loads(extra_file.read_text(encoding="utf-8")) if extra_file.exists() else []
    plan = json.loads(plan_file.read_text(encoding="utf-8")) if plan_file.exists() else []
    progress = json.loads(progress_file.read_text(encoding="utf-8")) if progress_file.exists() else {}
    trashed = set(json.loads(trashed_file.read_text(encoding="utf-8"))) if trashed_file.exists() else set()
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"renamed": {}}

    # Step 1: Deep-inspect opaque/numeric-named PDFs/EPUBs to extract internal book title
    opaque_candidates = []
    for rec in extra:
        fid = rec.get("file_id")
        if not fid or fid in trashed:
            continue
        stem, ext = normalize_ext(rec.get("name", ""))
        if OPAQUE_STEM_RE.match(stem) and ext in (".pdf", ".epub") and fid not in state["renamed"]:
            opaque_candidates.append((rec, ext))
    for it in plan:
        fid = progress.get(it["source_id"])
        if not fid or fid in trashed:
            continue
        stem, ext = normalize_ext(it.get("name", ""))
        if OPAQUE_STEM_RE.match(stem) and ext in (".pdf", ".epub") and fid not in state["renamed"]:
            opaque_candidates.append((it, ext, fid))

    if opaque_candidates:
        print(f"Inspecting {len(opaque_candidates)} opaque-named books internally for <dc:title> / PDF /Title...", flush=True)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            for item in opaque_candidates:
                if len(item) == 2:
                    rec, ext = item
                    fid = rec["file_id"]
                else:
                    rec, ext, fid = item
                t = inspect_opaque_file_title(fid, ext, tmp_dir)
                if t:
                    rec["internal_title"] = t
                    print(f"  Found internal title for {rec['name']} -> {t}", flush=True)

    # Step 2: Compute canonical clean filenames and batch-collect Drive renames
    rename_ops = []  # (rec, fid, new_name)
    for rec in extra:
        fid = rec.get("file_id")
        if not fid or fid in trashed or fid in state["renamed"]:
            continue
        new_name = clean_book_filename(rec)
        if new_name and new_name != rec["name"]:
            rename_ops.append((rec, fid, new_name))

    for it in plan:
        fid = progress.get(it["source_id"])
        if not fid or fid in trashed or fid in state["renamed"]:
            continue
        new_name = clean_book_filename(it)
        if new_name and new_name != it["name"]:
            rename_ops.append((it, fid, new_name))

    print(f"Total books needing clean internal-title rename in Drive & catalog: {len(rename_ops)}", flush=True)

    # Note: execute Drive renames sequentially OR via gdrive mutate batch chunks of 100!
    # Wait: if mutate batch takes {op:"rename", fileId, name}, batch 100 ops in one Go process!
    # We'll test batch vs direct cleanly and record every rename in book_rename_state.json.
    BATCH_SIZE = 80
    done = 0
    for i in range(0, len(rename_ops), BATCH_SIZE):
        chunk = rename_ops[i : i + BATCH_SIZE]
        ops_json = [{"op": "rename", "fileId": fid, "name": new_name} for _, fid, new_name in chunk]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(ops_json, tf, ensure_ascii=False)
            tmp_batch = tf.name
        try:
            res = gd_run(["mutate", "batch", "-f", tmp_batch], timeout=180)
            if res.returncode == 0:
                for rec, fid, new_name in chunk:
                    rec["name"] = new_name
                    state["renamed"][fid] = new_name
                    done += 1
            else:
                # Fallback individually on failure
                for rec, fid, new_name in chunk:
                    if gd_rename(fid, new_name):
                        rec["name"] = new_name
                        state["renamed"][fid] = new_name
                        done += 1
        finally:
            Path(tmp_batch).unlink(missing_ok=True)
        print(f"  Renamed {done}/{len(rename_ops)} books", flush=True)
        state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    # Ensure already-renamed records reflect state["renamed"]
    for rec in extra:
        fid = rec.get("file_id")
        if fid in state["renamed"]:
            rec["name"] = state["renamed"][fid]
    for it in plan:
        fid = progress.get(it["source_id"])
        if fid in state["renamed"]:
            it["name"] = state["renamed"][fid]

    extra_file.write_text(json.dumps(extra, ensure_ascii=False, indent=2), encoding="utf-8")
    plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Book renaming complete! Total renamed: {len(state['renamed'])}", flush=True)


if __name__ == "__main__":
    main()
