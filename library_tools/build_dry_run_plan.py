"""READ-ONLY Master Metadata Reconciler & Dry-Run Reorganization Planner.

Reads the live Drive audit (out/audit/), embedded file validation/metadata
(out/meta/), curated catalogs + git pre-rename history (repo data/), and
produces a complete non-destructive dry-run execution plan and Master Catalog:

  out/dry_run/master_catalog.csv
  out/dry_run/master_catalog.json
  out/dry_run/dry_run_operations.json
  out/dry_run/dry_run_summary.json
  out/dry_run/sample_renames.json
  out/dry_run/broken_html_redirects_report.csv
  out/dry_run/corrupted_files_report.csv
  out/dry_run/duplicates_report.csv
  out/dry_run/empty_folders_to_clean.csv
  out/dry_run/needs_review_report.csv

Does ZERO Google Drive writes and ZERO permanent deletions.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import taxonomy_rules as tr  # noqa: E402

INVALID_EMBED_TITLES = {
    "", "untitled", "untitled document", "document", "document1", "book",
    "microsoft word", "pdf", "none", "n/a", "test", "sample", "camscanner",
    "slide 1", "presentation", "index", "cover",
}
INVALID_EMBED_AUTHORS = {
    "", "unknown", "admin", "administrator", "user", "hp", "dell", "asus",
    "lenovo", "acer", "microsoft", "adobe", "owner", "pc", "windows user",
    "desktop", "scanner", "calibre", "writer", "author", "anon", "quran",
    "islam", "allah", "najib1", "mamun", "joy", "hardcopy", "canon",
    "andolon", "feysal", "shahadat",
}

SOFTWARE_AUTHOR_RE = re.compile(
    r"(?:adobe|acrobat|\bpdf\b|pdf24|pdffactory|primopdf|cutepdf|bullzip|dopdf|"
    r"wkhtml|canon|epson|xerox|brother|ricoh|fujitsu|samsung|konica|kyocera|lexmark|"
    r"scanfix|hardcopy|microsoft|word|excel|powerpoint|writer|libreoffice|openoffice|"
    r"\bwps\b|latex|ghostscript|pscript|quartz|corel|indesign|pagemaker|calibre|"
    r"abbyy|finereader|omnipage|foxit|nitro|sonic|wpdf|wpcubed|e-pdf|a-pdf|nuance|"
    r"converter|creator|distiller|scanner|printer|www\.|\.com|\.org|\.net|v?\d+\.\d+)",
    re.I,
)

OPAQUE_TITLE_RE = re.compile(
    r"^(?:"
    r"[\s._\-\u09e6-\u09ef0-9]+"
    r"|(?:book|file|doc|document|scan|img|untitled|part|vol|volume|chapter|ch|pdf|epub|page|q|no|issue|copy|"
    r"bengal|urdu|amharic|arabic|pashto|hindi|tamil|telugu|french|spanish|german|content[\s_\-]*page)[\s._\-()]*[\d\u09e6-\u09ef+._\-()]*"
    r"|new[\s._\-]*doc.*"
    r"|camscanner.*"
    r"|microsoft\s+word.*"
    r"|https?[\s_]+(?:file|download).*"
    r")$",
    re.I,
)

RANDOM_DRIVE_TOKEN_RE = re.compile(r"\b(?=[A-Za-z0-9_-]{18,}\b)(?=.*\d)(?=.*[a-z])(?=.*[A-Z])[A-Za-z0-9_-]{18,}\b")


def has_random_id_token(text: str) -> bool:
    return bool(RANDOM_DRIVE_TOKEN_RE.search(text or ""))


def is_sane_embed_text(val: str, kind: str = "title", title_hint: str = "") -> bool:
    s = tr.nfc(val)
    if not s or len(s) < 2 or len(s) > 120:
        return False
    low = s.lower()
    if "\ufffd" in s or low.startswith("microsoft word") or low.startswith("camscanner"):
        return False
    if kind == "title":
        if low in INVALID_EMBED_TITLES or re.fullmatch(r"[\d\s._\-]+", s) or has_random_id_token(s):
            return False
        if re.search(r"\.(?:doc|docx|pdf|indd|pmd|qxd|pages)$", low):
            return False
        return True
    if (
        low in INVALID_EMBED_AUTHORS
        or SOFTWARE_AUTHOR_RE.search(s)
        or re.fullmatch(r"[\d\s._\-]+", s)
        or re.fullmatch(r"[a-z]{2,12}\d+", low)
        or has_random_id_token(s)
    ):
        return False
    if title_hint and (low == title_hint.lower() or (len(low) > 15 and low in title_hint.lower())):
        return False
    # Ignore single-word non-Bangla typist usernames (e.g. "andolon", "Feysal", "Shahadat")
    if not tr.BN_RE.search(s) and len(s.split()) < 2:
        return False
    return True


def is_unknown_author(val: str) -> bool:
    return not val or tr.canonicalize_author(val, "English") == "Unknown"


def strip_ext(name: str) -> tuple[str, str]:
    m = re.match(r"^(.*)\.([A-Za-z0-9]{1,5})$", name)
    return (m.group(1), m.group(2).lower()) if m else (name, "")


def clean_title_text(raw: str) -> str:
    s = tr.nfc(raw)
    # Remove file extension if leaked into title
    s = re.sub(r"\.(?:pdf|epub|mobi|docx?|txt)$", "", s, flags=re.I).strip()
    # Remove Copy suffixes and redundant author tags
    s = re.sub(r"^(?:Copy of\s+)+", "", s, flags=re.I)
    s = re.sub(r"\s*\((?:Copy|কপি)(?:\s+\d+)?\)\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*\((?:Unknown Author|লেখক অজানা|Compiled|সংকলিত|Unknown)\)\s*", " ", s, flags=re.I)
    # Remove common piracy/watermark/downloader tags
    s = re.sub(r"\b(?:www\.)?(?:banglapdf|pdfbd|amarboi|boierhut|murchona|boighor|ebanglalibrary|islamicbook\.ws|tanbircox)\.(?:com|net|org|ws|blogspot\.com)\b", "", s, flags=re.I)
    s = re.sub(r"\b(?:Bangla\s*PDF\s*Book|Free\s*Bangla\s*eBook|Download\s*PDF)\b", "", s, flags=re.I)
    s = re.sub(r"^(?:https?\s+(?:file|download)\s+[A-Za-z0-9]{10,}\s*)", "", s, flags=re.I)
    # Clean underscores / hyphenated slugs when used as word separators
    if "_" in s and " " not in s:
        s = s.replace("_", " ")
    else:
        s = re.sub(r"(?<=[^\s])_(?=[^\s])", " ", s)
    if " " not in s and s.count("-") >= 2 and not has_random_id_token(s):
        s = re.sub(r"(?<![0-9])-(?![0-9])", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" -–—_.")
    return s


NON_AUTHOR_DASH_RHS = re.compile(
    r"^(?:\d{1,4}(?:\s*-\s*\d{1,4})?|\d+\s*p|part\s*\d+|vol\.?\s*\d+|chapter\s*\d+|paper\s*\d+|"
    r"\d+(?:st|nd|rd|th)\s*(?:part|vol|ed(?:ition)?|paper)|full\s*syllabus|bangla|english|"
    r"খণ্ড\s*[০-৯\d]*|পর্ব\s*[০-৯\d]*|[০-৯\d]+ম?\s*(?:খণ্ড|পর্ব|পত্র|সংস্করণ)|"
    r"প্রথম\s*খণ্ড|দ্বিতীয়\s*খণ্ড|তৃতীয়\s*খণ্ড|চতুর্থ\s*খণ্ড|"
    r"april|may|june|july|august|january|february|march|september|october|november|december)\b",
    re.I,
)


def extract_title_author_from_filename(raw_name: str, language_hint: str = "") -> tuple[str, str, str]:
    """Parse (title, author, translator) from a filename without inventing info."""
    stem, _ = strip_ext(raw_name)
    s = clean_title_text(stem)
    translator = ""

    # Translator patterns like "(অনুবাদ : রিশাদ হাবীব)" or "(Translated by X)"
    m_tr = re.search(r"\((?:অনুবাদ\s*[:ঃ\-]?\s*|Translated\s+by\s+)([^)]{2,60})\)", s, re.I)
    if m_tr:
        translator = tr.nfc(m_tr.group(1)).strip()

    # Strip trailing [YYYY] bracket cleanly for parsing (keep year inside title if not after author)
    yr_suf = ""
    m_yr_end = re.search(r"\s*(\[(?:19|20)\d{2}\])$", s)
    if m_yr_end:
        yr_suf = " " + m_yr_end.group(1)
        s_noyr = s[:m_yr_end.start()].strip()
    else:
        s_noyr = s

    # Pattern 1: Clean em-dash "Title — Author"
    if " — " in s_noyr:
        parts = s_noyr.rsplit(" — ", 1)
        if len(parts[0].strip()) >= 2 and len(parts[1].strip()) >= 2:
            return parts[0].strip(), parts[1].strip(), translator

    # Pattern 2: "Title ।। Author"
    if "।।" in s_noyr:
        parts = s_noyr.rsplit("।।" , 1)
        if len(parts[0].strip()) >= 2 and len(parts[1].strip()) >= 2:
            return parts[0].strip(), parts[1].strip(), translator

    # Pattern 3: Broken split-surname from earlier renamer: "Title – FirstWords (LastWord)"
    m_split = re.match(r"^(.{3,}?)\s+[–\-]\s+([A-Za-z\u0980-\u09FF.\s]{2,45}?)\s+\(([A-Za-z\u0980-\u09FF]{2,25})\)$", s_noyr)
    if m_split:
        t_cand, a1, a2 = m_split.group(1).strip(), m_split.group(2).strip(), m_split.group(3).strip()
        if not re.search(r"(?:খণ্ড|পর্ব|অধ্যায়|সংস্করণ|শ্রেণি|Part|Vol|Ed|\d|রাঃ|রা\.|সাঃ|আঃ)", a2, re.I):
            return t_cand, f"{a1} {a2}".strip(), translator

    # Pattern 4: NCTB pre-rename long string: "Subject (BV) - ২০২৬ মাধ্যমিক ... - NCTB (জাতীয় ...)"
    m_nctb = re.match(r"^(.+?)\s*\((BV|EV)\)\s*[-–—]\s*(.+?)\s*\(NCTB(?:\s*(202[0-9]))?\).*$", s_noyr, re.I)
    if m_nctb:
        subj, ver, detail = m_nctb.group(1).strip(), m_nctb.group(2).upper(), m_nctb.group(3).strip()
        detail = re.sub(r"\s*[-–—]\s*NCTB.*$", "", detail, flags=re.I).strip()
        auth = "NCTB" if ver == "EV" else "এনসিটিবি"
        clean_t = f"{subj} ({'English Version, ' if ver == 'EV' else ''}{detail})".strip()
        return clean_t, auth, translator

    # Pattern 5: "Title by Author" (handles optional trailing [YYYY] stripped into s_noyr)
    m_by = re.match(r"^(.{3,}?)\s+by\s+([A-Za-z][A-Za-z.\s\-]{2,55})$", s_noyr, re.I)
    if m_by and not re.search(r"\b(?:edition|vol|part|chapter|\d)\b", m_by.group(2), re.I):
        return (m_by.group(1).strip() + yr_suf).strip(), m_by.group(2).strip(), translator

    # Pattern 6: Spaced en-dash or hyphen "Title – Author" / "Title - Author"
    for sep in (" – ", " - "):
        if sep in s_noyr:
            lhs, rhs = s_noyr.rsplit(sep, 1)
            lhs, rhs = lhs.strip(), rhs.strip()
            if (
                len(lhs) >= 3
                and 2 <= len(rhs) <= 55
                and not NON_AUTHOR_DASH_RHS.search(rhs)
                and not re.search(r"\b(?:19|20)\d{2}\b", rhs)
                and not re.search(r"(?:শ্রেণির|শ্রেণী|shrenir|board book|edition|volume|chapter|part|khondo|porbo)", rhs, re.I)
                and len(rhs.split()) <= 6
            ):
                return (lhs + yr_suf).strip(), rhs, translator

    # Pattern 7: Tight Bangla honorific separator "Title-আবু বকর ..."
    m_tight = re.match(r"^(.{4,}?)[-–]((?:ড\.|ডা\.|মাওলানা|শাইখ|ইমাম|আল্লামা|আবু\s+বকর|মুহাম্ম[দ|া]দ|ইবনে)\s*[\u0980-\u09FF\s.]{3,45})$", s_noyr)
    if m_tight:
        return (m_tight.group(1).strip() + yr_suf).strip(), m_tight.group(2).strip(), translator

    # Pattern 8: "Title (Author)" when trailing parens looks like a person/org name (not year/edition/part/tag)
    m_par = re.match(r"^(.{3,}?)\s*\(([^()]{3,65})\)$", s_noyr)
    if m_par:
        t_cand, p_cand = m_par.group(1).strip(), m_par.group(2).strip()
        non_author_rx = re.compile(
            r"^(?:\d{4}|19\d{2}|20\d{2}|part\s*\d+|vol\.?\s*\d+|chapter|edition|\d+(?:st|nd|rd|th)|"
            r"bv|ev|english\s*version|bangla\s*version|full\s*syllabus|bangla|english|pdf|epub|quran|"
            r".*(?:খণ্ড|পর্ব|সংস্করণ|অনুবাদ|সংকলন|সম্পূর্ণ|জীবন ও কর্ম|পর্যালোচনা|রাঃ|রা\.|সাঃ|আঃ).*)$",
            re.I,
        )
        if not non_author_rx.search(p_cand) and not re.search(r"\d{2,}", p_cand):
            return (t_cand + yr_suf).strip(), p_cand, translator

    return s, "Unknown", translator


def sanitize_filename(name: str, max_len: int = 180) -> str:
    s = tr.nfc(name)
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', " - ", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > max_len:
        s = s[:max_len].strip(" .-—")
    return s or "Untitled"


def format_target_filename(title: str, author: str, ext: str) -> str:
    t = sanitize_filename(title, 130)
    a = sanitize_filename(author, 60)
    if a and a != "Unknown":
        # Remove redundant trailing "- Author" / "– Author" if present on title
        t = re.sub(r"\s*[-–—]\s*" + re.escape(a) + r"$", "", t, flags=re.I).strip()
        if a.lower() not in t.lower():
            base = f"{t} — {a}"
        else:
            base = t
    else:
        base = t
    base = sanitize_filename(base, 185)
    return f"{base}.{ext}" if ext else base


def load_historical_and_curated(repo_dir: Path, drive_ids: set[str], md5_map: dict[str, dict]) -> tuple[dict, dict, dict, dict]:
    """Load curated website catalogs and historical pre-English-rename git records."""
    # 1. eBanglaLibrary meta keyed by URL
    eb_meta: dict[str, dict] = {}
    eb_p = repo_dir / "data" / "ebanglalibrary_meta.json"
    if eb_p.exists():
        for m in json.load(open(eb_p, encoding="utf-8")):
            if m.get("url"):
                eb_meta[m["url"]] = m

    # 2. Other catalogs keyed by URL or drive_file_id
    kb_by_url: dict[str, dict] = {}
    kb_by_fid: dict[str, dict] = {}
    kb_p = repo_dir / "data" / "kindlebangla_catalog.json"
    if kb_p.exists():
        for m in json.load(open(kb_p, encoding="utf-8")):
            if m.get("url"):
                kb_by_url[m["url"]] = m
            if m.get("drive_file_id"):
                kb_by_fid[m["drive_file_id"]] = m

    # 3. Mine git history: pre-English-rename merged_books.json (e7b362e1f~1) + earlier commits
    by_fid_hist: dict[str, dict] = {}
    def ingest_list(items: list[dict], source_tag: str, overwrite_bn: bool = False):
        for it in items:
            if not isinstance(it, dict):
                continue
            ids = [it.get("file_id"), it.get("pdf_file_id"), it.get("epub_file_id")]
            for f in (it.get("files") or []):
                if isinstance(f, dict) and f.get("id"):
                    ids.append(f["id"])
            rec = {
                "title": it.get("title") or it.get("name") or "",
                "author": it.get("author") or "",
                "publication": it.get("publication") or "",
                "book_url": it.get("book_url") or "",
                "cover_url": it.get("cover_url") or it.get("thumbnail_url") or "",
                "leaf_path": it.get("leaf_path") or "",
                "_src": source_tag,
            }
            rec_has_bn = bool(tr.BN_RE.search(rec["title"] + " " + rec["author"]))
            for fid in ids:
                if not fid or fid not in drive_ids:
                    continue
                cur = by_fid_hist.get(fid)
                if cur is None:
                    by_fid_hist[fid] = rec
                else:
                    cur_has_bn = bool(tr.BN_RE.search((cur.get("title") or "") + " " + (cur.get("author") or "")))
                    if overwrite_bn and rec_has_bn and not cur_has_bn:
                        merged = dict(cur)
                        for k, v in rec.items():
                            if v:
                                merged[k] = v
                        by_fid_hist[fid] = merged
                    else:
                        for k in ("book_url", "cover_url", "publication"):
                            if not cur.get(k) and rec.get(k):
                                cur[k] = rec[k]

    # Pre-English-rename baseline first
    try:
        raw_pre = subprocess.check_output(
            ["git", "-C", str(repo_dir), "show", "e7b362e1f~1:data/merged_books.json"],
            stderr=subprocess.DEVNULL,
        )
        ingest_list(json.loads(raw_pre), "git:e7b362e1f~1")
    except Exception as e:
        print(f"WARN pre-rename load: {e}", file=sys.stderr)

    # Scan non-English-rename commits touching merged_books / extra_books
    try:
        commits = subprocess.check_output(
            ["git", "-C", str(repo_dir), "log", "--format=%H %s", "--", "data/merged_books.json", "data/extra_books.json"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", "replace").splitlines()
        seen_commits = 0
        for line in commits:
            h, msg = line.split(" ", 1)
            if "English Drive rename" in msg or "to English" in msg:
                continue
            for rel in ("data/merged_books.json", "data/extra_books.json"):
                try:
                    raw = subprocess.check_output(["git", "-C", str(repo_dir), "show", f"{h}:{rel}"], stderr=subprocess.DEVNULL)
                    ingest_list(json.loads(raw), f"git:{h[:7]}:{rel}", overwrite_bn=True)
                except Exception:
                    continue
            seen_commits += 1
            if seen_commits >= 20:
                break
    except Exception:
        pass

    # Current data files (supplement URLs, covers, recently ingested books)
    for rel in ("data/merged_books.json", "data/extra_books.json", "data/local_added_books.json"):
        p = repo_dir / rel
        if p.exists():
            ingest_list(json.load(open(p, encoding="utf-8")), rel, overwrite_bn=False)

    # Also build source_lookup matching by file_id and md5
    src_by_fid: dict[str, dict] = {}
    src_by_md5: dict[str, dict] = {}
    for k, v in md5_map.items():
        if v.get("file_id"):
            src_by_fid[v["file_id"]] = v
        if k:
            src_by_md5[k] = v

    return eb_meta, kb_by_url, by_fid_hist, {"by_fid": src_by_fid, "by_md5": src_by_md5, "kb_by_fid": kb_by_fid}


def map_ebook_license(publication: str, source_url: str, title: str, author: str) -> tuple[str, str]:
    blob = f"{publication} {source_url} {title} {author}".lower()
    if "nctb" in blob or "egovcloud" in blob:
        return "Government of Bangladesh Free Educational Distribution (NCTB)", "Official Free Textbook"
    if "wikisource" in blob:
        return "Public Domain / CC-BY-SA-4.0 (Wikisource)", "Public Domain"
    if "gutenberg" in blob:
        return "Public Domain (Project Gutenberg)", "Public Domain"
    if "openstax" in blob:
        return "Creative Commons (OpenStax)", "Open Access"
    if "archive.org" in blob:
        return "Digitized Archive (Verify per item)", "Needs Review"
    if "ebanglalibrary" in blob or "kindlebangla" in blob or "bdebooks" in blob or "students.bd" in blob:
        return "Existing Personal Library Import", "Personal Collection (Verify Before Public Redistribution)"
    return "Existing Personal Library File", "Personal Collection (Verify Before Public Redistribution)"


def infer_author_subcat(subcat: str, series: str, author: str) -> str:
    if series and author in tr.nfc(series) or (
        author == "হুমায়ূন আহমেদ" and series in ("হিমু সিরিজ", "মিসির আলি সিরিজ", "শুভ্র সিরিজ")
    ) or (
        author == "সত্যজিৎ রায়" and series in ("ফেলুদা সিরিজ", "প্রফেসর শঙ্কু সিরিজ")
    ) or (
        author == "কাজী আনোয়ার হোসেন" and series in ("মাসুদ রানা সিরিজ", "কুয়াশা সিরিজ")
    ) or (
        author == "আবুল আসাদ" and series == "সাইমুম সিরিজ"
    ) or (
        author == "শরদিন্দু বন্দ্যোপাধ্যায়" and series == "ব্যোমকেশ বক্সী সিরিজ"
    ) or (
        author == "সুনীল গঙ্গোপাধ্যায়" and series == "কাকাবাবু সিরিজ"
    ):
        return series
    mapping = {
        "উপন্যাস": "উপন্যাস",
        "Fiction": "Fiction",
        "গল্প ও ছোটগল্প": "গল্প",
        "কবিতা": "কবিতা",
        "নাটক": "নাটক",
        "প্রবন্ধ": "প্রবন্ধ",
        "শিশু-কিশোর সাহিত্য": "শিশু-কিশোর সাহিত্য",
        "থ্রিলার, রহস্য ও গোয়েন্দা": "থ্রিলার ও গোয়েন্দা",
        "অনুবাদ ও বিদেশী সাহিত্য": "অনুবাদ ও বিদেশী সাহিত্য",
    }
    return mapping.get(subcat, "অন্যান্য" if tr.BN_RE.search(author) else "Others")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-dir", required=True)
    ap.add_argument("--meta-dir", required=True)
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    audit_dir = Path(args.audit_dir)
    meta_dir = Path(args.meta_dir)
    repo_dir = Path(args.repo_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(repo_dir / "scripts"))
    import clean_classifier as cc  # noqa: E402

    # 1. Load audit inventory + file_meta + source_lookup + empty_folders
    inv_rows = list(csv.DictReader(open(audit_dir / "inventory_full.csv", encoding="utf-8-sig")))
    empty_rows = list(csv.DictReader(open(audit_dir / "empty_folders.csv", encoding="utf-8-sig")))
    file_meta: dict[str, dict] = {}
    fm_path = meta_dir / "file_meta.jsonl"
    if fm_path.exists():
        for line in open(fm_path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            file_meta[r["id"]] = r

    fm_total = len(file_meta)
    fm_valid = sum(1 for v in file_meta.values() if v.get("valid") is True)
    fm_html = sum(1 for v in file_meta.values() if v.get("real_type") == "html")
    fm_invalid = sum(1 for v in file_meta.values() if v.get("valid") is False and v.get("real_type") != "html")
    fm_err = sum(1 for v in file_meta.values() if v.get("error") and v.get("valid") is None)
    err_rate = (fm_err / fm_total * 100.0) if fm_total else 0.0
    print(
        f"file_meta summary: total={fm_total} valid={fm_valid} html={fm_html} "
        f"corrupted_or_empty={fm_invalid} download_errors={fm_err} error_rate={err_rate:.2f}%",
        flush=True,
    )

    src_md5_map: dict[str, dict] = {}
    sl_path = meta_dir / "source_lookup.jsonl"
    if sl_path.exists():
        for line in open(sl_path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("ok") and r.get("md5"):
                src_md5_map.setdefault(r["md5"], r)

    ebooks = [r for r in inv_rows if r["kind"] == "ebook"]
    drive_ids = {r["id"] for r in ebooks}

    eb_meta, kb_by_url, hist_by_fid, extra_lookups = load_historical_and_curated(repo_dir, drive_ids, src_md5_map)

    # 2. Triage: Broken HTML redirects, Corrupted/Empty, MD5 Duplicates, Valid Unique
    broken_html: list[dict] = []
    corrupted: list[dict] = []
    candidate_valid: list[dict] = []

    for r in ebooks:
        fid = r["id"]
        size = int(r["size"] or 0)
        fm = file_meta.get(fid, {})
        if fm.get("real_type") == "html":
            broken_html.append({
                "drive_file_id": fid,
                "name": r["name"],
                "size": size,
                "html_title": fm.get("html_title", ""),
                "redirect_urls": "; ".join(fm.get("redirect_urls") or []),
                "original_path": r["path"],
                "target_folder": "08_Review_and_Unclassified/Broken_HTML_Redirects",
            })
        elif size == 0 or fm.get("valid") is False:
            corrupted.append({
                "drive_file_id": fid,
                "name": r["name"],
                "size": size,
                "real_type": fm.get("real_type", "unknown"),
                "error": fm.get("error", ""),
                "original_path": r["path"],
                "target_folder": "08_Review_and_Unclassified/Corrupted_or_Empty",
            })
        else:
            candidate_valid.append(r)

    # Group valid candidates by MD5 checksum for byte-exact duplicate detection
    md5_groups: dict[str, list[dict]] = collections.defaultdict(list)
    for r in candidate_valid:
        md5_groups[r["md5"] or f"nomd5:{r['id']}"].append(r)

    def keep_priority(r: dict) -> tuple:
        in_bad_area = any(s in r["path"] for s in ("90_UNSORTED_REVIEW", "DUPLICATE", "LEGACY"))
        has_copy = bool(re.search(r"\((?:Copy|কপি)|Copy of ", r["name"], re.I))
        has_meta = r["id"] in hist_by_fid
        return (in_bad_area, has_copy, not has_meta, r["created"], r["id"])

    unique_valid: list[dict] = []
    exact_duplicates: list[dict] = []

    for md5, grp in md5_groups.items():
        if len(grp) == 1:
            unique_valid.append(grp[0])
            continue
        grp_sorted = sorted(grp, key=keep_priority)
        keeper = grp_sorted[0]
        unique_valid.append(keeper)
        for dup in grp_sorted[1:]:
            exact_duplicates.append({
                "md5": md5,
                "size": int(dup["size"]),
                "kept_id": keeper["id"],
                "kept_name": keeper["name"],
                "kept_path": keeper["path"],
                "dup_id": dup["id"],
                "dup_name": dup["name"],
                "dup_path": dup["path"],
                "target_folder": "08_Review_and_Unclassified/Exact_Duplicates_Quarantine",
            })

    # 3. Reconcile metadata & plan moves/renames for unique_valid
    catalog_records: list[dict] = []
    move_rename_ops: list[dict] = []
    used_paths: set[tuple[str, str]] = set()
    used_ids: set[str] = set()

    def alloc_unique_name(folder: str, desired_name: str) -> str:
        stem, ext = strip_ext(desired_name)
        cand = desired_name
        idx = 2
        while (folder, cand.lower()) in used_paths:
            cand = f"{stem} [v{idx}].{ext}" if ext else f"{stem} [v{idx}]"
            idx += 1
        used_paths.add((folder, cand.lower()))
        return cand

    # Reserve names for quarantine folders too so zero collisions anywhere
    for item in broken_html:
        item["target_name"] = alloc_unique_name(item["target_folder"], sanitize_filename(item["name"], 190))
    for item in corrupted:
        item["target_name"] = alloc_unique_name(item["target_folder"], sanitize_filename(item["name"], 190))
    for item in exact_duplicates:
        item["target_name"] = alloc_unique_name(item["target_folder"], sanitize_filename(item["dup_name"], 190))

    recovered_bn_count = 0
    needs_review_rows: list[dict] = []

    for idx_num, r in enumerate(sorted(unique_valid, key=lambda x: x["id"]), 1):
        fid = r["id"]
        used_ids.add(fid)
        fm = file_meta.get(fid, {})
        hist = hist_by_fid.get(fid, {})
        src_rec = extra_lookups["by_fid"].get(fid) or extra_lookups["by_md5"].get(r["md5"]) or {}

        book_url = hist.get("book_url") or ""
        eb = eb_meta.get(book_url, {}) if book_url else {}
        kb = kb_by_url.get(book_url, {}) or extra_lookups["kb_by_fid"].get(fid, {})

        publication = hist.get("publication") or ""
        cover_url = hist.get("cover_url") or eb.get("cover_url") or kb.get("cover_url") or ""
        genres = list(eb.get("genres") or kb.get("categories") or [])

        # Determine best title + author from curated -> git historical -> source_lookup -> embedded -> Drive name
        title_cand = ""
        author_cand = ""
        orig_title = ""
        translator = ""
        publisher = fm.get("publisher") or ""
        pub_year = ""

        # Publication year from filename / embedded date
        for yr_src in (fm.get("date", ""), hist.get("title", ""), r["name"]):
            m_yr = re.search(r"\b(19\d{2}|20[0-2]\d)\b", str(yr_src))
            if m_yr:
                pub_year = m_yr.group(1)
                break

        # Curated eBanglaLibrary
        if eb:
            raw_eb_t = eb.get("real_title") or eb.get("title") or ""
            if " – " in raw_eb_t:
                title_cand = raw_eb_t.split(" – ", 1)[0].strip()
            elif " - " in raw_eb_t:
                title_cand = raw_eb_t.split(" - ", 1)[0].strip()
            else:
                title_cand = raw_eb_t.strip()
            author_cand = (eb.get("author") or "").strip()
            orig_title = title_cand

        # Historical pre-rename / merged metadata
        if hist:
            ht = hist.get("title") or ""
            ha = hist.get("author") or ""
            ht_parsed, ha_parsed, tr_parsed = extract_title_author_from_filename(ht)
            if not title_cand or (tr.BN_RE.search(ht_parsed) and not tr.BN_RE.search(title_cand)):
                title_cand = ht_parsed
                orig_title = orig_title or ht
            if is_unknown_author(author_cand) or (tr.BN_RE.search(ha) and not tr.BN_RE.search(author_cand)):
                author_cand = ha if not is_unknown_author(ha) else ha_parsed
            if tr_parsed and not translator:
                translator = tr_parsed

        # Original Drive source file lookup (when historical didn't have Bangla)
        if src_rec:
            sn = src_rec.get("name") or src_rec.get("recorded_name") or ""
            st_parsed, sa_parsed, tr_s = extract_title_author_from_filename(sn)
            if tr.BN_RE.search(st_parsed) and not tr.BN_RE.search(title_cand):
                title_cand = st_parsed
                orig_title = orig_title or sn
            if tr.BN_RE.search(sa_parsed) and is_unknown_author(author_cand):
                author_cand = sa_parsed
            if tr_s and not translator:
                translator = tr_s

        # Fallback: current Drive filename
        fn_title, fn_author, fn_tr = extract_title_author_from_filename(r["name"])
        if not title_cand:
            title_cand = fn_title
        if is_unknown_author(author_cand) and not is_unknown_author(fn_author):
            author_cand = fn_author
        if fn_tr and not translator:
            translator = fn_tr
        if not orig_title:
            orig_title = hist.get("title") or strip_ext(r["name"])[0]

        # Embedded file metadata fallback (strictly validated; NEVER read PDF /Creator as author!)
        emb_title = fm.get("title_full") or fm.get("xmp_title") or fm.get("title") or ""
        if fm.get("real_type") == "pdf":
            emb_author = fm.get("xmp_creator") or fm.get("author") or ""
        else:
            emb_author = fm.get("xmp_creator") or fm.get("creator") or fm.get("author") or ""
        if (not title_cand or OPAQUE_TITLE_RE.search(title_cand) or has_random_id_token(title_cand)) and is_sane_embed_text(emb_title, "title"):
            title_cand = clean_title_text(emb_title)
        if is_unknown_author(author_cand) and is_sane_embed_text(emb_author, "author", title_hint=title_cand):
            author_cand = tr.nfc(emb_author)

        # Parent folder author fallback ONLY inside STORIES_AND_FICTION author subfolders
        path_parts = r["path"].split("/")
        if is_unknown_author(author_cand) and len(path_parts) >= 4:
            if path_parts[1].strip('"') == "STORIES_AND_FICTION":
                folder_cand = path_parts[2].strip('"')
                if folder_cand and folder_cand not in ("Various  Unknown", "Various Unknown", "Novels", "Short_Stories"):
                    if not folder_cand.startswith("Humayun Ahmed ["):
                        author_cand = folder_cand

        title_clean = clean_title_text(title_cand)
        language = tr.detect_language(
            title_clean, author=author_cand, publication=publication,
            emb_lang=fm.get("language") or fm.get("xmp_language") or "", source_path=r["path"]
        )
        author_clean = tr.canonicalize_author(author_cand, language)
        if author_clean == "Unknown" and ("board book" in title_clean.lower() or "nctb" in (title_clean + " " + r["path"]).lower()):
            author_clean = "NCTB" if language == "English" else "এনসিটিবি"

        # Clean NCTB bloated title formatting while preserving class/version/year
        if author_clean in ("এনসিটিবি", "NCTB"):
            m_n = re.match(r"^(.+?)\s*\((BV|EV)\)\s*[-–—]\s*(.+)$", title_clean, re.I)
            if m_n:
                subj, ver, rest = m_n.group(1).strip(), m_n.group(2).upper(), m_n.group(3).strip()
                rest = re.sub(r"\s*\(NCTB(?:\s*\d{4})?\)\s*", " ", rest, flags=re.I)
                rest = re.sub(r"\s*[-–—]?\s*(?:NCTB|জাতীয় শিক্ষাক্রম ও পাঠ্যপুস্তক বোর্ড).*$", "", rest, flags=re.I).strip(" -–—")
                title_clean = f"{subj} ({'English Version, ' if ver == 'EV' else ''}{rest})".strip()
            # Also handle legacy "Class 5 Amar Bangla Boi Board Book"
            title_clean = re.sub(r"\s*\(NCTB\s*\d{4}\)\s*$", "", title_clean, flags=re.I).strip()

        if tr.BN_RE.search(title_clean) and not tr.BN_RE.search(r["name"]):
            recovered_bn_count += 1

        # Opaque / corrupted title check -> route to Needs_Manual_Review without inventing name
        opaque = (
            not title_clean
            or len(re.sub(r"[\W_0-9]+", "", title_clean)) < 2
            or bool(OPAQUE_TITLE_RE.search(title_clean))
            or has_random_id_token(title_clean)
            or "\ufffd" in title_clean
        )

        series = tr.detect_series(title_clean, author_clean, r["path"], publication)
        if opaque:
            target_folder = "08_Review_and_Unclassified/Needs_Manual_Review"
            cat, subcat = "08_Review_and_Unclassified", "Needs_Manual_Review"
            target_name = alloc_unique_name(target_folder, sanitize_filename(r["name"], 190))
            ver_status = "Needs Review"
            needs_review_rows.append({
                "drive_file_id": fid, "original_name": r["name"], "cleaned_title": title_clean,
                "author": author_clean, "reason": "opaque_or_truncated_title", "original_path": r["path"],
            })
        else:
            target_folder, cat, subcat = tr.map_target_category(
                title=title_clean,
                author=author_clean,
                language=language,
                genres=genres,
                orig_path=r["path"],
                publication=publication,
                series=series,
                clean_leaf_fn=cc.classify_clean_leaf,
            )
            _, ext = strip_ext(r["name"])
            desired_name = format_target_filename(title_clean, author_clean, ext or r["ext"])
            target_name = alloc_unique_name(target_folder, desired_name)
            if author_clean == "Unknown":
                ver_status = "Needs Review (Author Unknown)"
            elif not tr.BN_RE.search(title_clean) and language == "Bangla":
                ver_status = "Needs Review (Romanized Bangla Title)"
            else:
                ver_status = "Verified"

        target_path = f"{target_folder}/{target_name}"
        lic, cstat = map_ebook_license(publication, book_url, title_clean, author_clean)
        edition = ""
        m_ed = re.search(r"(\d+(?:st|nd|rd|th)\s+Ed(?:ition)?|[১-৯০]+ম\s+সংস্করণ|Revised)", title_clean, re.I)
        if m_ed:
            edition = m_ed.group(1)

        rec = {
            "book_id": f"BK{idx_num:06d}",
            "title": title_clean,
            "original_title": orig_title,
            "author": author_clean,
            "translator": translator,
            "publisher": publisher or publication,
            "publication_year": pub_year or "Unknown",
            "language": language,
            "category": cat,
            "subcategory": subcat,
            "series": series,
            "edition": edition,
            "format": (r["ext"] or fm.get("real_type") or "").upper(),
            "file_size": int(r["size"]),
            "drive_file_id": fid,
            "drive_path": target_path,
            "original_filename": r["name"],
            "source_url": book_url,
            "license": lic,
            "copyright_status": cstat,
            "cover_url": cover_url,
            "date_added": (r["created"] or "")[:10],
            "verification_status": ver_status,
        }
        catalog_records.append(rec)

        old_parent_path = "/".join(r["path"].split("/")[:-1])
        move_rename_ops.append({
            "kind": "ebook",
            "drive_file_id": fid,
            "old_name": r["name"],
            "old_parent_id": r["parent_id"],
            "old_path": r["path"],
            "target_folder": target_folder,
            "target_name": target_name,
            "needs_move": old_parent_path != target_folder,
            "needs_rename": r["name"] != target_name,
        })

    # 4. Plan Author Shortcuts (05_Authors_and_Scholars) & Series Shortcuts (06_Series_and_Collections)
    active_books = [b for b in catalog_records if b["category"] != "08_Review_and_Unclassified"]
    author_groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for b in active_books:
        a = b["author"]
        if a in ("Unknown", "এনসিটিবি", "NCTB"):
            continue
        is_bn_auth = bool(tr.BN_RE.search(a)) or b["language"] == "Bangla"
        author_groups[(a, "bn" if is_bn_auth else "az")].append(b)

    series_groups: dict[str, list[dict]] = collections.defaultdict(list)
    for b in active_books:
        if b["series"] and not b["series"].startswith("NCTB Textbooks"):
            series_groups[b["series"]].append(b)

    shortcut_ops: list[dict] = []
    author_folders: dict[str, int] = {}
    for (auth, script_grp), blist in sorted(author_groups.items(), key=lambda kv: -len(kv[1])):
        if len(blist) < 3:
            continue
        safe_auth = sanitize_filename(auth, 80)
        if script_grp == "bn":
            base_dir = f"05_Authors_and_Scholars/বাংলা বর্ণমালা/{safe_auth}"
        else:
            first_ch = re.sub(r"[^A-Za-z]", "", auth)[:1].upper() or "0-9"
            base_dir = f"05_Authors_and_Scholars/A-Z/{first_ch}/{safe_auth}"
        author_folders[base_dir] = len(blist)
        use_sub = len(blist) >= 15
        for b in blist:
            if use_sub:
                sub = infer_author_subcat(b["subcategory"], b["series"], auth)
                tf = f"{base_dir}/{sub}"
            else:
                tf = base_dir
            tname = alloc_unique_name(tf, Path(b["drive_path"]).name)
            shortcut_ops.append({
                "type": "author",
                "target_file_id": b["drive_file_id"],
                "shortcut_folder": tf,
                "shortcut_name": tname,
            })

    series_folders: dict[str, int] = {}
    for sname, blist in sorted(series_groups.items(), key=lambda kv: -len(kv[1])):
        if len(blist) < 3:
            continue
        tf = f"06_Series_and_Collections/{sanitize_filename(sname, 80)}"
        series_folders[tf] = len(blist)
        for b in blist:
            tname = alloc_unique_name(tf, Path(b["drive_path"]).name)
            shortcut_ops.append({
                "type": "series",
                "target_file_id": b["drive_file_id"],
                "shortcut_folder": tf,
                "shortcut_name": tname,
            })

    # 5. Non-ebook cleanup moves (JSONs, covers, legacy reports, zips)
    non_ebook_moves: list[dict] = []
    for r in inv_rows:
        k = r["kind"]
        if k in ("folder", "ebook", "shortcut"):
            continue
        if r["id"] in ("1dEMPkGWXWvx3vSHu708KTfpKwS7IG0Ar_ffKtA4-QDM",):  # Keep 00 - START HERE at root
            continue
        if r["id"] == "14w-o89nRvdYYOINV2mtEZBZbNRh0P1TDZZ_84arSG-k":
            tf = "00_Library_Management/Master_Catalog"
        elif k == "google_doc":
            tf = "00_Library_Management/Reports/Archived_Legacy_Docs"
        elif k == "archive":
            tf = "08_Review_and_Unclassified/Archives_ZIP"
        elif k == "json":
            tf = "00_Library_Management/Reports/Archived_Legacy_Reports" if "MASTER_INDEX" in r["name"] else "00_Library_Management/Metadata/eBanglaLibrary_JSON"
        elif k == "image":
            tf = "00_Library_Management/Cover_Images"
        else:
            tf = "00_Library_Management/Reports/Archived_Legacy_Reports"
        old_parent = "/".join(r["path"].split("/")[:-1])
        if old_parent != tf:
            non_ebook_moves.append({
                "kind": k, "drive_file_id": r["id"], "name": r["name"],
                "old_parent_id": r["parent_id"], "target_folder": tf,
            })

    # 6. Write outputs
    cat_fields = [
        "book_id", "title", "original_title", "author", "translator", "publisher",
        "publication_year", "language", "category", "subcategory", "series", "edition",
        "format", "file_size", "drive_file_id", "drive_path", "original_filename",
        "source_url", "license", "copyright_status", "cover_url", "date_added",
        "verification_status",
    ]
    with open(out_dir / "master_catalog.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cat_fields)
        w.writeheader()
        w.writerows(catalog_records)
    (out_dir / "master_catalog.json").write_text(json.dumps(catalog_records, ensure_ascii=False, indent=1), encoding="utf-8")

    def write_csv(fn: str, rows_list: list[dict], cols: list[str] | None = None):
        cols = cols or (list(rows_list[0].keys()) if rows_list else [])
        with open(out_dir / fn, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows_list)

    write_csv("broken_html_redirects_report.csv", broken_html)
    write_csv("corrupted_files_report.csv", corrupted)
    write_csv("duplicates_report.csv", exact_duplicates)
    write_csv("empty_folders_to_clean.csv", empty_rows)
    write_csv("needs_review_report.csv", needs_review_rows)

    legacy_roots = [
        {"id": r["id"], "name": r["name"]}
        for r in inv_rows
        if r["kind"] == "folder" and str(r["depth"]) == "1"
        and r["name"] not in ("00_Library_Management", "01_Bangla_Books", "02_English_Books",
                              "03_Education_and_Textbooks", "04_Islamic_Books",
                              "05_Authors_and_Scholars", "06_Series_and_Collections",
                              "07_Reference_and_Research", "08_Review_and_Unclassified")
    ]
    ops_payload = {
        "delete_count": 0,
        "ebook_moves_and_renames": move_rename_ops,
        "quarantine_broken_html": broken_html,
        "quarantine_corrupted": corrupted,
        "quarantine_duplicates": exact_duplicates,
        "non_ebook_moves": non_ebook_moves,
        "shortcuts": shortcut_ops,
        "legacy_root_folders": legacy_roots,
        "empty_folders_to_trash_count": len(empty_rows),
    }
    (out_dir / "dry_run_operations.json").write_text(json.dumps(ops_payload, ensure_ascii=False), encoding="utf-8")
    with gzip.open(out_dir / "dry_run_plan.json.gz", "wt", encoding="utf-8") as gz:
        json.dump({**ops_payload, "catalog_records": catalog_records}, gz, ensure_ascii=False)

    # Sample renames across key categories
    samples = []
    for label, pred in [
        ("Bangla Literature", lambda op, rec: rec["category"] == "01_Bangla_Books" and op["needs_rename"]),
        ("English Books", lambda op, rec: rec["category"] == "02_English_Books" and op["needs_rename"]),
        ("Education / NCTB", lambda op, rec: rec["category"] == "03_Education_and_Textbooks" and op["needs_rename"]),
        ("Islamic Books", lambda op, rec: rec["category"] == "04_Islamic_Books" and op["needs_rename"]),
        ("Reference & Magazines", lambda op, rec: rec["category"] == "07_Reference_and_Research" and op["needs_rename"]),
    ]:
        rec_by_id = {b["drive_file_id"]: b for b in catalog_records}
        picked = []
        for op in move_rename_ops:
            rec = rec_by_id[op["drive_file_id"]]
            if pred(op, rec) and op["old_name"] != op["target_name"]:
                picked.append({
                    "group": label,
                    "drive_file_id": op["drive_file_id"],
                    "before_name": op["old_name"],
                    "after_name": op["target_name"],
                    "before_path": op["old_path"],
                    "after_path": f"{op['target_folder']}/{op['target_name']}",
                    "author": rec["author"],
                    "language": rec["language"],
                })
                if len(picked) >= 10:
                    break
        samples.extend(picked)
    (out_dir / "sample_renames.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")

    # 7. Self-verification invariants
    triaged_ids = (
        {b["drive_file_id"] for b in catalog_records}
        | {x["drive_file_id"] for x in broken_html}
        | {x["drive_file_id"] for x in corrupted}
        | {x["dup_id"] for x in exact_duplicates}
    )
    all_ebook_ids = {r["id"] for r in ebooks}
    assert triaged_ids == all_ebook_ids, f"ID mismatch: missing={len(all_ebook_ids - triaged_ids)}, extra={len(triaged_ids - all_ebook_ids)}"
    assert len(catalog_records) + len(broken_html) + len(corrupted) + len(exact_duplicates) == len(ebooks), "Count conservation violated!"
    target_folders_used = {op["target_folder"] for op in move_rename_ops} | {s["shortcut_folder"] for s in shortcut_ops}
    assert not any('"' in tf for tf in target_folders_used), "Literal double quote found in target folder!"
    assert ops_payload["delete_count"] == 0, "Permanent deletes must be 0!"

    cat_tree = collections.Counter(f"{b['category']}/{b['subcategory']}" for b in catalog_records)
    cat_bytes = collections.Counter()
    for b in catalog_records:
        cat_bytes[f"{b['category']}/{b['subcategory']}"] += b["file_size"]

    summary = {
        "total_audited_drive_items": len(inv_rows),
        "total_audited_ebook_files": len(ebooks),
        "broken_html_redirects": len(broken_html),
        "corrupted_or_empty_ebooks": len(corrupted),
        "exact_md5_duplicates_quarantined": len(exact_duplicates),
        "unique_valid_ebooks_in_catalog": len(catalog_records),
        "unique_valid_bytes": sum(b["file_size"] for b in catalog_records),
        "recovered_bangla_titles_from_history": recovered_bn_count,
        "ebooks_needing_move": sum(1 for o in move_rename_ops if o["needs_move"]),
        "ebooks_needing_rename": sum(1 for o in move_rename_ops if o["needs_rename"]),
        "needs_manual_review_opaque": len(needs_review_rows),
        "needs_review_author_unknown": sum(1 for b in catalog_records if "Author Unknown" in b["verification_status"]),
        "needs_review_romanized_bangla": sum(1 for b in catalog_records if "Romanized" in b["verification_status"]),
        "verified_clean": sum(1 for b in catalog_records if b["verification_status"] == "Verified"),
        "languages": dict(collections.Counter(b["language"] for b in catalog_records).most_common()),
        "unique_known_authors": len({b["author"] for b in catalog_records if b["author"] not in ("Unknown", "NCTB", "এনসিটিবি")}),
        "author_folders_count": len(author_folders),
        "author_shortcuts_count": sum(1 for s in shortcut_ops if s["type"] == "author"),
        "series_folders_count": len(series_folders),
        "series_shortcuts_count": sum(1 for s in shortcut_ops if s["type"] == "series"),
        "top_authors": sorted([(k, v) for k, v in author_folders.items()], key=lambda x: -x[1])[:25],
        "series_breakdown": sorted([(k, v) for k, v in series_folders.items()], key=lambda x: -x[1]),
        "category_breakdown": {k: {"count": v, "gb": round(cat_bytes[k] / 1e9, 3)} for k, v in sorted(cat_tree.items())},
        "non_ebook_assets_to_organize": dict(collections.Counter(m["target_folder"] for m in non_ebook_moves)),
        "empty_legacy_folders_to_trash": len(empty_rows),
        "invariants": "ALL DRY-RUN INVARIANTS PASSED",
    }
    (out_dir / "dry_run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ALL DRY-RUN INVARIANTS PASSED")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("category_breakdown", "top_authors")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
