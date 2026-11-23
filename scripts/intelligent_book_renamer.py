#!/usr/bin/env python3
"""
Google Drive eBook Library — Intelligent Book Identification, Cover/OCR Inspection,
Safe Renaming & AnaBook Website/App Catalog Sync.

Strictly obeys all library preservation rules:
- Never creates, deletes, or renames folders.
- Never moves files between folders.
- Never deletes, modifies, or overwrites file contents.
- Never renames Google Drive shortcuts, Google Docs/Sheets, or Library Management files.
- Preserves original file extensions and original title languages/scripts.
- Any file with doubt is marked REQUIRES REVIEW and is NEVER renamed.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import datetime as dt
import io
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image, ImageStat

ROOT_ID = os.environ.get("LIBRARY_ROOT_ID", "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq")
DRIVE_API = "https://www.googleapis.com/drive/v3"
FOLDER_MIME = "application/vnd.google-apps.folder"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"
SKIP_TOP_FOLDERS = {"Library Management"}
SKIP_SUBFOLDERS = {"Qawmi Madrasa"}
BOOK_EXTS = {".pdf", ".epub", ".mobi", ".azw", ".azw3", ".djvu", ".txt", ".doc", ".docx", ".rtf"}
INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

NOISE_PATTERNS = [
    re.compile(r"\(?\s*(?:www\.)?[a-z0-9-]+\.(?:com|org|net|blogspot\.com|wordpress\.com|info|bd)\s*\)?", re.I),
    re.compile(r"\(\s*Unknown Author\s*\)", re.I),
    re.compile(r"\[\s*(?:pdfdrive|z-lib(?:\.org)?|oceanofpdf|anna['’]?s archive|telegram|@[\w]+)\s*\]", re.I),
    re.compile(r"(?:^|\s)@[A-Za-z0-9_]+(?:\s|$)"),
    re.compile(r"\b(?:fivedownload|boierpathshala|bengaliebook|pdfbooks|ebookbd|amarboi|banglabook)\b", re.I),
    re.compile(r"\s*[-—–]\s*Copy(?:\s*\(\d+\))?$", re.I),
    re.compile(r"(?:^|\s)unicode$", re.I),
]

GIBBERISH_STEM_RE = re.compile(
    r"^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|"
    r"\d{5,}|"
    r"1[A-Za-z0-9_-]{20,}(?:\s*\([^)]*\))?|"
    r"[0-9]+\s*\([A-Za-z0-9_-]{12,}\)|"
    r"[A-Za-z0-9_-]{5,}\s*\([A-Za-z0-9_-]{8,}\))$",
    re.I,
)

# ---------------------------------------------------------------------------
# Minimal Thread-Safe Google Drive v3 OAuth Client
# ---------------------------------------------------------------------------
_tok_lock = threading.Lock()
_tok_val: str | None = None
_tok_exp = 0.0


def get_access_token() -> str:
    global _tok_val, _tok_exp
    with _tok_lock:
        if _tok_val and time.time() < _tok_exp - 120:
            return _tok_val
        raw = os.environ.get("GDRIVE_OAUTH_JSON", "").strip()
        if not raw:
            raise RuntimeError("GDRIVE_OAUTH_JSON environment variable is not set.")
        creds = json.loads(raw)
        if "installed" in creds:
            creds = {**creds["installed"], **{k: v for k, v in creds.items() if k != "installed"}}
        body = urllib.parse.urlencode(
            {
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type": "refresh_token",
            }
        ).encode()
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        _tok_val = data["access_token"]
        _tok_exp = time.time() + float(data.get("expires_in", 3600))
        return _tok_val


def drive_request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    raw: bool = False,
    timeout: int = 90,
    retries: int = 8,
) -> Any:
    url = path if path.startswith("http") else f"{DRIVE_API}{path}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    for attempt in range(retries):
        headers = {"Authorization": f"Bearer {get_access_token()}"}
        if payload is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                return data if raw else (json.loads(data) if data else {})
        except urllib.error.HTTPError as e:
            msg = e.read()[:400].decode("utf-8", "replace")
            if e.code == 401:
                global _tok_val
                with _tok_lock:
                    _tok_val = None
            retryable = e.code in (401, 408, 429, 500, 502, 503, 504) or (
                e.code == 403 and any(k in msg for k in ("rateLimit", "userRateLimitExceeded", "quotaExceeded"))
            )
            if not retryable or attempt == retries - 1:
                raise RuntimeError(f"Drive API {method} {path} -> {e.code}: {msg}") from None
            time.sleep(min(2 ** attempt, 20))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(min(2 ** attempt, 10))


def list_children(folder_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(id, name, mimeType, size, md5Checksum, parents, thumbnailLink, modifiedTime)",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token
        res = drive_request("GET", "/files", params=params)
        items.extend(res.get("files", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return items


def resolve_folder_path(target_path: str) -> tuple[str, str]:
    """Resolve a slash-separated path under ROOT_ID without modifying anything."""
    cleaned = target_path.strip().strip("/")
    if not cleaned or cleaned.upper() == "ALL":
        return ROOT_ID, ""
    cur_id = ROOT_ID
    parts = [p.strip() for p in cleaned.split("/") if p.strip()]
    resolved: list[str] = []
    for part in parts:
        children = list_children(cur_id)
        match = next(
            (c for c in children if c.get("mimeType") == FOLDER_MIME and c.get("name", "").lower() == part.lower()),
            None,
        )
        if not match:
            raise RuntimeError(f"Folder segment '{part}' not found under '{'/'.join(resolved) or 'ROOT'}'")
        cur_id = match["id"]
        resolved.append(match["name"])
    return cur_id, "/".join(resolved)


def walk_inventory(folder_id: str, prefix: str, include_qawmi: bool = False) -> tuple[list[dict], list[dict], list[dict]]:
    """Stage A: recursive read-only inventory."""
    files: list[dict] = []
    skipped_items: list[dict] = []
    folders_seen: list[dict] = [{"id": folder_id, "path": prefix or "ROOT"}]

    def _walk(fid: str, cur_path: str) -> None:
        for it in list_children(fid):
            mime = it.get("mimeType", "")
            name = it.get("name", "")
            iid = it.get("id", "")
            if mime == FOLDER_MIME:
                if not cur_path and name in SKIP_TOP_FOLDERS:
                    skipped_items.append({"id": iid, "name": name, "path": cur_path, "reason": "library_management_folder"})
                    continue
                if not include_qawmi and name in SKIP_SUBFOLDERS:
                    skipped_items.append({"id": iid, "name": name, "path": cur_path, "reason": "protected_subfolder"})
                    continue
                sub = f"{cur_path}/{name}" if cur_path else name
                folders_seen.append({"id": iid, "path": sub})
                _walk(iid, sub)
            elif mime == SHORTCUT_MIME or mime.startswith("application/vnd.google-apps."):
                skipped_items.append({"id": iid, "name": name, "path": cur_path, "reason": f"google_native_or_shortcut:{mime}"})
            else:
                ext = os.path.splitext(name)[1].lower()
                if ext not in BOOK_EXTS:
                    skipped_items.append({"id": iid, "name": name, "path": cur_path, "reason": f"non_ebook_ext:{ext}"})
                    continue
                files.append(
                    {
                        "id": iid,
                        "name": name,
                        "ext": ext,
                        "mimeType": mime,
                        "size": int(it.get("size") or 0),
                        "md5": it.get("md5Checksum") or "",
                        "folder": cur_path,
                        "parentId": fid,
                        "thumbnailLink": it.get("thumbnailLink") or "",
                        "modifiedTime": it.get("modifiedTime") or "",
                    }
                )

    _walk(folder_id, prefix)
    files.sort(key=lambda x: (x["folder"].lower(), x["name"].lower()))
    return files, skipped_items, folders_seen


# ---------------------------------------------------------------------------
# Stage B: Cover Image Audit + PDF/EPUB Metadata & OCR Inspection
# ---------------------------------------------------------------------------
ARABIC_HINT_RE = re.compile(
    r"(?:arabic|urdu|quran|hadith|tafsir|fiqh|seerah|কুরআন|হাদিস|তাফসীর|উর্দু|আরবি|ইসলাম)",
    re.I,
)


def pick_ocr_langs(rec: dict[str, Any]) -> str:
    hint = f"{rec.get('folder', '')} {rec.get('name', '')}"
    return "ben+eng+ara" if ARABIC_HINT_RE.search(hint) else "ben+eng"


def ocr_image_pil(img: Image.Image, langs: str = "ben+eng") -> str:
    if not shutil.which("tesseract"):
        return ""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tmp_path = tf.name
    try:
        work = img.convert("RGB")
        if max(work.size) > 1200:
            work.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        work.save(tmp_path, format="PNG")
        res = subprocess.run(
            ["tesseract", tmp_path, "stdout", "-l", langs, "--oem", "1", "--psm", "6"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            timeout=15,
        )
        return res.stdout.strip() if res.returncode == 0 else ""
    except Exception:
        return ""
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def inspect_cover_thumbnail(file_rec: dict[str, Any]) -> tuple[dict[str, Any], bytes | None]:
    """Fetch Drive cover thumbnail and audit dimensions & blankness (lazy OCR later if needed)."""
    fid = file_rec["id"]
    url = f"https://drive.google.com/thumbnail?id={fid}&sz=w600"
    info = {"cover_status": "MISSING", "cover_width": 0, "cover_height": 0, "cover_ocr": ""}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if "image" not in ctype or len(data) < 500:
                return info, None
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        info["cover_width"] = w
        info["cover_height"] = h
        gray = img.convert("L")
        stddev = ImageStat.Stat(gray).stddev[0]
        if stddev < 6.0:
            info["cover_status"] = "BLANK"
        elif w < 180 or h < 220:
            info["cover_status"] = "LOW_RES"
        else:
            info["cover_status"] = "OK"
        return info, data
    except Exception:
        return info, None


def download_drive_file_head(file_id: str, dest_path: str, max_bytes: int | None = None) -> bool:
    """Download file content via Drive API (read-only) for metadata/page inspection."""
    url = f"{DRIVE_API}/files/{file_id}?alt=media&supportsAllDrives=true"
    headers = {"Authorization": f"Bearer {get_access_token()}"}
    if max_bytes is not None:
        headers["Range"] = f"bytes=0-{max_bytes - 1}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp, open(dest_path, "wb") as out:
            shutil.copyfileobj(resp, out, length=1024 * 256)
        return os.path.getsize(dest_path) > 0
    except Exception:
        return False


def inspect_pdf_content(pdf_path: str, ocr_langs: str = "ben+eng") -> dict[str, Any]:
    out: dict[str, Any] = {
        "pdf_title": "",
        "pdf_author": "",
        "pdf_subject": "",
        "pdf_pages": 0,
        "text_sample": "",
        "page1_ocr": "",
        "is_scanned": False,
        "access_error": "",
    }
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        out["access_error"] = f"pdf_open_error: {str(e)[:120]}"
        return out
    try:
        if doc.is_encrypted:
            out["access_error"] = "encrypted_pdf"
            return out
        out["pdf_pages"] = len(doc)
        meta = doc.metadata or {}
        out["pdf_title"] = (meta.get("title") or "").strip()
        out["pdf_author"] = (meta.get("author") or "").strip()
        out["pdf_subject"] = (meta.get("subject") or "").strip()

        chunks: list[str] = []
        for pno in range(min(5, len(doc))):
            txt = (doc[pno].get_text("text") or "").strip()
            if txt:
                chunks.append(txt)
        joined = "\n".join(chunks).strip()
        out["text_sample"] = joined[:3000]

        if len(joined) < 120 and len(doc) > 0:
            out["is_scanned"] = True
            ocr_chunks: list[str] = []
            pix1 = doc[0].get_pixmap(dpi=130)
            pil1 = Image.frombytes("RGB", [pix1.width, pix1.height], pix1.samples)
            t1 = ocr_image_pil(pil1, langs=ocr_langs)
            if t1:
                ocr_chunks.append(t1)
            if len(t1.strip()) < 30 and len(doc) > 1:
                pix2 = doc[1].get_pixmap(dpi=130)
                pil2 = Image.frombytes("RGB", [pix2.width, pix2.height], pix2.samples)
                t2 = ocr_image_pil(pil2, langs=ocr_langs)
                if t2:
                    ocr_chunks.append(t2)
            out["page1_ocr"] = "\n".join(ocr_chunks)[:2000]
    except Exception as e:
        out["access_error"] = f"pdf_read_error: {str(e)[:120]}"
    finally:
        doc.close()
    return out


def inspect_epub_content(epub_path: str) -> dict[str, Any]:
    out = {"pdf_title": "", "pdf_author": "", "pdf_subject": "", "text_sample": "", "access_error": ""}
    try:
        with zipfile.ZipFile(epub_path, "r") as zf:
            opf_name = next((n for n in zf.namelist() if n.lower().endswith(".opf")), None)
            if not opf_name:
                return out
            root = ET.fromstring(zf.read(opf_name))
            ns = {"dc": "http://purl.org/dc/elements/1.1/"}
            t = root.find(".//dc:title", ns)
            a = root.find(".//dc:creator", ns)
            s = root.find(".//dc:subject", ns)
            p = root.find(".//dc:publisher", ns)
            d = root.find(".//dc:date", ns)
            out["pdf_title"] = (t.text or "").strip() if t is not None and t.text else ""
            out["pdf_author"] = (a.text or "").strip() if a is not None and a.text else ""
            out["pdf_subject"] = " | ".join(
                x for x in [
                    (s.text or "").strip() if s is not None and s.text else "",
                    (p.text or "").strip() if p is not None and p.text else "",
                    (d.text or "").strip() if d is not None and d.text else "",
                ] if x
            )
    except Exception as e:
        out["access_error"] = f"epub_error: {str(e)[:120]}"
    return out


# ---------------------------------------------------------------------------
# Classification & Strict Rule-Based Naming (No Guessing / No Fabrication)
# ---------------------------------------------------------------------------
def clean_text(s: str) -> str:
    s = re.sub(r"[\r\n\t]+", " ", s or "")
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def sanitize_filename(stem: str, ext: str) -> str:
    stem = INVALID_FS_CHARS.sub(" ", stem)
    stem = re.sub(r"\s{2,}", " ", stem).strip(" .-_")
    if len(stem) > 160:
        stem = stem[:160].rstrip(" .-_")
    return f"{stem}{ext}"


def strip_filename_noise(stem: str) -> str:
    s = stem.replace("_", " ")
    for pat in NOISE_PATTERNS:
        s = pat.sub(" ", s)
    s = re.sub(r"\s*[-–—]\s*$", "", s)
    s = re.sub(r"^\d{1,3}\.\s+", "", s)
    return clean_text(s)


CAMELCASE_ALLOWLIST = {
    "javascript", "typescript", "mcgraw", "macmillan", "mcdonald", "latex", "phd",
    "openai", "ios", "macos", "iphone", "ipad", "youtube", "github", "linkedin",
    "ebook", "ebooks", "wifi", "defi", "devops", "nosql", "postgresql", "pytorch",
    "tensorflow", "autocad", "wordpress", "mysql", "jquery", "fastapi", "nextjs",
    "graphql", "dubois", "mccarthy", "leguin", "deitel", "mcquail",
}

BIJOY_GLYPH_RE = re.compile(
    r"[\x00-\x1f\x7f-\x9f\ufffd¨¬¶‡†±÷×¾©®°µ¹²³¼½¿^~|`¡¢£¤¥¦§ª«¯´·¸º»ÀÂÃÄÅÆÈÊËÌÎÏÐÒÔÕÖØÙÛÜÝÞßãåæìðòõøþ]"
)

URL_DOMAIN_STAMP_RE = re.compile(
    r"(?:https?://|www\.|@|"
    r"(?:^|[\s(\[-])[a-z0-9-]+\.(?:com|org|net|info|bd|edu|gov|io|co|uk|in|pk|biz|me|blogspot|wordpress)(?:\.[a-z]{2,3})?(?:$|[\s)\],.;:-])|"
    r"\b(?:amarboi|grontho|banglainternet|banglabook|banglakitab|icsbook|quraneralo|durjoybook|"
    r"exambd|sikshanmandir|besturdubooks|waytojannah|tanbircox|fivedownload|boierpathshala|"
    r"bengaliebook|pdfbooks|ebookbd|students\.bd|educationblog24|"
    r"uploaded\s+by|this\s+book\s+is\s+from|downloaded\s+from|pdf\s+creator|converted\s+by|scanned\s+by|compiled\s+by)\b)",
    re.I,
)


def norm_unicode(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")


def is_bijoy_or_mojibake(val: str) -> bool:
    s = val or ""
    if not s:
        return False
    if BIJOY_GLYPH_RE.search(s):
        return True
    # Multiple accented Latin-1 chars rarely occur in genuine English/Bengali/Arabic titles
    if len(re.findall(r"[\u00C0-\u00FF]", s)) >= 2:
        return True
    for tok in re.findall(r"[A-Za-z']+", s):
        low = tok.lower()
        if low in CAMELCASE_ALLOWLIST or len(tok) < 3:
            continue
        if re.match(r"^(?:Ma?c|De|La|Le|Di|Du|Van|Von|O')[A-Z][a-z]+$", tok):
            continue
        if (
            re.match(r"^[a-z]{1,3}[A-Z][A-Za-z]*$", tok)
            or re.search(r"[a-z][A-Z]{2,}", tok)
            or re.match(r"^(?:Av[a-z]{2,}|Iqv|kv[A-Z]|evsj|wZb|bv[A-Z])", tok)
        ):
            return True
    return False


def contains_url_or_domain(val: str) -> bool:
    s = (val or "").strip()
    if not s:
        return False
    if re.fullmatch(r"(?:com|org|net|info|bd|edu|gov|www|http|https)", s, re.I):
        return True
    return bool(URL_DOMAIN_STAMP_RE.search(s))


def is_valid_meta_title(val: str) -> bool:
    s = clean_text(val)
    if len(s) < 3 or is_bijoy_or_mojibake(s) or contains_url_or_domain(s):
        return False
    if "/" in s or "\\" in s:
        return False
    low = s.lower()
    bad_exact = {
        "untitled", "unknown", "unknown author", "document", "microsoft word", "microsoft powerpoint",
        "microsoft excel", "adobe", "pdf", "scan", "camscanner", "wps", "wps office", "admin",
        "administrator", "user", "hp", "dell", "lenovo", "asus", "acer", "samsung", "pc",
        "owner", "guest", "laptop", "desktop", "author", "writer", "default", "noname",
        "book", "ebook", "cover", "chapter 1", "chapter", "contents", "preface", "title",
        "index", "introduction", "part 1", "calibre",
    }
    bad_substrings = (
        "microsoft word", "microsoft powerpoint", "microsoft excel", "[compatibility mode]",
        "untitled art", "camscanner", "ilovepdf", "smallpdf", "pdf creator", "coreldraw",
        "adobe acrobat", "adobe indesign",
    )
    bad_prefixes = ("untitled", "layout ", "slide ", "scan", "img_", "doc ", "adobe ", "indesign", "quark", "presentation")
    bad_exts = (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".pmd", ".indd", ".cdr", ".txt", ".qxd", ".psd", ".html", ".htm", ".rar", ".zip", ".exe")
    if (
        low in bad_exact
        or any(sub in low for sub in bad_substrings)
        or any(low.startswith(p) for p in bad_prefixes)
        or any(low.endswith(e) for e in bad_exts)
    ):
        return False
    if re.fullmatch(r"[\d\W_]+", low) or re.fullmatch(r"[A-Za-z]?\d{2,6}", s):
        return False
    # Reject raw unformatted slugs like he_provu_ami_upostit or multi-hyphen web slugs without spaces
    if ("_" in s and " " not in s) or (s.count("-") >= 2 and " " not in s):
        return False
    return True


def is_valid_meta_author(val: str, body_content: str = "") -> bool:
    s = clean_text(val)
    if not s or not is_valid_meta_title(s):
        return False
    low = s.lower()
    extra_bad = {
        "administrator", "admin", "user", "owner", "guest", "pc", "laptop", "desktop",
        "default", "unknown", "unknown author", "author", "writer", "editor", "publisher",
        "calibre", "nitro", "foxit", "wps", "hp", "dell", "lenovo", "asus", "acer",
        "samsung", "microsoft",
    }
    if low in extra_bad or re.search(r"[@]|(?:[-_]pc\b)", low):
        return False
    # Single-token ASCII handle/username (no whitespace) must actually appear in book body
    if re.fullmatch(r"[A-Za-z0-9._-]{2,25}", s):
        return len(body_content) > 0 and corroborated_in_body(s, body_content)
    return True


def extract_tokens(phrase: str) -> list[str]:
    norm = norm_unicode(phrase).lower()
    raw_tokens = re.findall(r"[\w\u0980-\u09FF\u0600-\u06FF\u0900-\u097F\u0D00-\u0D7F]+", norm)
    tokens: list[str] = []
    for tok in raw_tokens:
        is_latin = bool(re.fullmatch(r"[a-z0-9]+", tok))
        min_len = 3 if is_latin else 2
        if len(tok) >= min_len:
            tokens.append(tok)
    return tokens


def corroborated_in_body(phrase: str, body_content: str) -> bool:
    if not phrase or not body_content:
        return False
    tokens = extract_tokens(phrase)
    if not tokens:
        return False
    body_low = norm_unicode(body_content).lower()
    hits = sum(1 for t in tokens if t in body_low)
    needed = max(1, math.ceil(len(tokens) * 0.5))
    return hits >= needed


def detect_category(combined_text: str, filename: str) -> str:
    t = norm_unicode(f"{filename}\n{combined_text}").lower()
    if any(k in t for k in ("question paper", "প্রশ্নপত্র", "board question", "past paper", "model test")):
        return "Question Papers"
    if any(k in t for k in ("admission", "ভর্তি পরীক্ষা", "medical admission", "buet", "du admission", "গুচ্ছ")):
        return "Admission Preparation"
    if any(k in t for k in ("bcs", "বিসিএস", "bank job", "ielts", "gre ", "gmat", "ntrca")):
        return "Competitive Examination Preparation"
    if any(k in t for k in ("nctb", "জাতীয় শিক্ষাক্রম", "class 1", "class 2", "class 3", "class 4", "class 5",
                            "class 6", "class 7", "class 8", "class 9", "class 10", "ষষ্ঠ শ্রেণি", "সপ্তম শ্রেণি",
                            "অষ্টম শ্রেণি", "নবম-দশম", "প্রাথমিক")):
        return "School Textbooks"
    if any(k in t for k in ("hsc", "একাদশ-দ্বাদশ", "উচ্চ মাধ্যমিক", "1st paper", "2nd paper", "প্রথম পত্র", "দ্বিতীয় পত্র")):
        return "College Textbooks"
    if any(k in t for k in ("dictionary", "অভিধান", "encyclopedia", "বিশ্বকোষ", "lexicon")):
        return "Dictionaries & Encyclopedias"
    if any(k in t for k in ("quran", "কুরআন", "কোরআন", "hadith", "হাদিস", "বুখারী", "সহীহ বুখারী",
                            "সহীহ মুসলিম", "সহিহ মুসলিম", "sahih muslim", "sahih bukhari", "মুসলিম শরীফ",
                            "তাফসীর", "তফসীর", "tafsir", "হিসনুল মুসলিম", "hisnul muslim", "bible", "gita", "বেদ")):
        return "Religious Scriptures"
    if any(k in t for k in ("ইসলাম", "islam", "ফিকহ", "fiqh", "সীরাত", "seerah", "নামাজ", "রোজা", "আকীদা", "aqeedah", "দাওয়াহ")):
        return "Religious Studies"
    if any(k in t for k in ("python", "javascript", "java ", "c++", "algorithm", "data structure", "machine learning", "programming", "linux", "sql", "computer science")):
        return "Computer Science & IT"
    if any(k in t for k in ("biography", "autobiography", "জীবনী", "আত্মজীবনী", "স্মৃতিকথা", "ডায়েরি", "diary")):
        return "Biography & Autobiography"
    if any(k in t for k in ("কবিতা", "কাব্যগ্রন্থ", "poetry", "poems", "সঞ্চয়িতা")):
        return "Poetry"
    if any(k in t for k in ("নাটক", "drama", "play by")):
        return "Drama"
    if any(k in t for k in ("গল্পসমগ্র", "ছোটগল্প", "short stories", "গল্পসংগ্রহ")):
        return "Short Stories"
    if any(k in t for k in ("উপন্যাস", "novel", "রচনাবলী", "সমগ্র")):
        return "Novels"
    if any(k in t for k in ("history", "ইতিহাস", "মুক্তিযুদ্ধ", "সভ্যতা", "civilization")):
        return "History & Civilization"
    if any(k in t for k in ("mathematics", "গণিত", "calculus", "algebra", "statistics", "পরিসংখ্যান")):
        return "Mathematics & Statistics"
    if any(k in t for k in ("physics", "chemistry", "biology", "পদার্থবিজ্ঞান", "রসায়ন", "জীববিজ্ঞান", "science", "বিজ্ঞান")):
        return "Science & Technology"
    if any(k in t for k in ("philosophy", "দর্শন", "ethics", "নীতিশাস্ত্র")):
        return "Philosophy & Ethics"
    if any(k in t for k in ("economics", "অর্থনীতি", "politics", "রাজনীতি", "রাষ্ট্রবিজ্ঞান")):
        return "Politics & Economics"
    if any(k in t for k in ("law", "আইন", "constitution", "সংবিধান")):
        return "Law & Constitution"
    if any(k in t for k in ("medicine", "medical", "স্বাস্থ্য", "চিকিৎসা", "pharmacology", "anatomy")):
        return "Health & Medicine"
    if any(k in t for k in ("grammar", "ব্যাকরণ", "linguistics", "ভাষাতত্ত্ব")):
        return "Language & Linguistics"
    if any(k in t for k in ("comic", "tintin", "টিনটিন", "চাচা চৌধুরী", "graphic novel")):
        return "Comics & Graphic Novels"
    if any(k in t for k in ("কিশোর", "ছোটদের", "children", "রূপকথা")):
        return "Children's Books"
    if any(k in t for k in ("journal", "vol.", "volume", "issn", "magazine", "ম্যাগাজিন", "সংখ্যা")):
        return "Journals & Magazines"
    if any(k in t for k in ("abstract", "doi:", "arxiv", "proceedings", "et al.")):
        return "Research Papers"
    return "Unclassified / General"


def extract_year(text: str) -> str:
    years = re.findall(r"\b(19[5-9]\d|20[0-2]\d)\b", text)
    return years[0] if years else ""


def extract_edition(text: str) -> str:
    m = re.search(r"\b(\d+(?:st|nd|rd|th)\s+Ed(?:ition)?)\b", text, re.I)
    return m.group(1) if m else ""


EMBEDDED_ATTRIBUTION_RE = re.compile(
    r"(?:কুরআন|হাদিস|সহীহ|সহিহ|বুখারী|মুসলিম|তাফসীর|তফসীর|হিসনুল|বিশ্বকোষ|"
    r"quran|qur'an|hadith|sahih|tafsir|bukhari|muslim|ibn\s+ka(?:s|th)ir|hisnul)",
    re.I,
)


def propose_name(rec: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    """
    Combine filename + PDF/EPUB metadata + cover OCR + inner text.
    Never trusts metadata alone; strictly marks any uncertainty as REQUIRES REVIEW.
    """
    orig_name = rec["name"]
    stem, ext = os.path.splitext(orig_name)
    cleaned_stem = strip_filename_noise(stem)
    is_gibberish = bool(GIBBERISH_STEM_RE.match(stem.strip()))

    meta_title = clean_text(signals.get("pdf_title", ""))
    meta_author = clean_text(signals.get("pdf_author", ""))
    cover_ocr = clean_text(signals.get("cover_ocr", ""))
    text_sample = clean_text(signals.get("text_sample", ""))
    page1_ocr = clean_text(signals.get("page1_ocr", ""))
    body_content = "\n".join(x for x in [cover_ocr, text_sample, page1_ocr] if x)

    has_meta_title = is_valid_meta_title(meta_title)
    has_meta_author = is_valid_meta_author(meta_author, body_content)

    safe_meta_for_cat = "\n".join(x for x in ([meta_title] if has_meta_title else []) + ([meta_author] if has_meta_author else []))
    category = detect_category(f"{body_content}\n{safe_meta_for_cat}", orig_name)
    year = extract_year(f"{orig_name} {signals.get('pdf_subject', '')} {text_sample[:800]} {cover_ocr[:400]}")
    edition = extract_edition(f"{orig_name} {text_sample[:800]} {cover_ocr[:400]}")

    fn_title, fn_author = "", ""
    if not is_gibberish and cleaned_stem:
        m_by = re.match(r"^(.+?)\s+by\s+(.+)$", cleaned_stem, re.I)
        m_dash = re.match(r"^(.+?)\s+[-–—]\s+(.+)$", cleaned_stem)
        if m_by:
            fn_title, fn_author = clean_text(m_by.group(1)), clean_text(m_by.group(2))
        elif m_dash:
            fn_title, fn_author = clean_text(m_dash.group(1)), clean_text(m_dash.group(2))
        else:
            fn_title = cleaned_stem
    valid_fn_author = fn_author if is_valid_meta_author(fn_author, body_content) else ""

    title = ""
    author = ""
    confidence = "REQUIRES REVIEW"
    reason = ""

    if signals.get("access_error"):
        return {
            "identified_book": "UNACCESSIBLE",
            "category": category,
            "proposed_filename": "REQUIRES REVIEW",
            "confidence": "REQUIRES REVIEW",
            "reason": signals["access_error"],
        }

    # Case A: Clean PDF/EPUB metadata title genuinely corroborated inside body/cover text
    if has_meta_title and corroborated_in_body(meta_title, body_content):
        title = meta_title
        if has_meta_author and corroborated_in_body(meta_author, body_content):
            author = meta_author
            confidence = "HIGH"
            reason = "verified_metadata_corroborated_in_body"
        elif valid_fn_author and corroborated_in_body(valid_fn_author, body_content):
            author = valid_fn_author
            confidence = "HIGH"
            reason = "verified_meta_title_and_fn_author"
        elif category in ("Religious Scriptures", "Religious Studies") and EMBEDDED_ATTRIBUTION_RE.search(title):
            author = ""
            confidence = "HIGH"
            reason = "verified_scripture_title_in_body"
        elif category in ("School Textbooks", "College Textbooks", "Question Papers") and year:
            author = ""
            confidence = "HIGH"
            reason = "academic_meta_corroborated_with_year"
        else:
            author = meta_author if has_meta_author else valid_fn_author
            confidence = "REQUIRES REVIEW"
            reason = "metadata_author_missing_or_uncorroborated"

    # Case B: Gibberish / random ID filename — keep OCR clue for manual review, never auto-rename
    elif is_gibberish:
        candidate_lines = [
            clean_text(ln)
            for ln in (signals.get("text_sample", "") + "\n" + signals.get("cover_ocr", "") + "\n" + signals.get("page1_ocr", "")).splitlines()
            if len(clean_text(ln)) >= 4
            and not re.fullmatch(r"[\d\W_]+", clean_text(ln))
            and not is_bijoy_or_mojibake(ln)
            and not contains_url_or_domain(ln)
        ]
        if candidate_lines:
            title = candidate_lines[0][:100]
            confidence = "REQUIRES REVIEW"
            reason = "gibberish_filename_ocr_candidate_only"
        else:
            return {
                "identified_book": "Unidentified (no readable metadata/OCR)",
                "category": category,
                "proposed_filename": "REQUIRES REVIEW",
                "confidence": "REQUIRES REVIEW",
                "reason": "gibberish_filename_no_text",
            }

    # Case C: Non-gibberish filename corroborated in actual cover/body text (plus verified author)
    else:
        title = fn_title
        cand_author = meta_author if has_meta_author else valid_fn_author
        if is_bijoy_or_mojibake(fn_title) or contains_url_or_domain(fn_title):
            confidence = "REQUIRES REVIEW"
            reason = "bijoy_or_unreliable_title"
        elif is_valid_meta_title(fn_title) and corroborated_in_body(fn_title, body_content):
            if cand_author and corroborated_in_body(cand_author, body_content):
                author = cand_author
                confidence = "HIGH"
                reason = "verified_filename_and_author_in_body"
            elif category in ("School Textbooks", "College Textbooks", "Question Papers") and year:
                author = ""
                confidence = "HIGH"
                reason = "academic_filename_corroborated_with_year"
            else:
                author = cand_author
                confidence = "REQUIRES REVIEW"
                reason = "filename_corroborated_author_missing_or_unverified"
        else:
            author = cand_author
            confidence = "REQUIRES REVIEW"
            reason = "insufficient_content_corroboration"

    # Final safety gate before ever permitting HIGH confidence
    if confidence == "HIGH" and (
        not title
        or not is_valid_meta_title(title)
        or (author and not is_valid_meta_author(author, body_content))
    ):
        confidence = "REQUIRES REVIEW"
        reason = "final_safety_gate_triggered"

    parts = [title]
    if category in ("University Textbooks", "Computer Science & IT", "Academic Reference Books"):
        if author:
            parts.append(author)
        if edition:
            parts.append(edition)
    elif category in ("School Textbooks", "College Textbooks"):
        if author and author.lower() not in title.lower():
            parts.append(author)
        if year and year not in title:
            parts.append(year)
    else:
        if author and author.lower() not in title.lower():
            parts.append(author)

    proposed = sanitize_filename(" - ".join(p for p in parts if p), ext) if title else ""
    identified_desc = " — ".join(p for p in [title, author, edition, year] if p)

    if confidence != "HIGH":
        return {
            "identified_book": identified_desc or cleaned_stem or orig_name,
            "category": category,
            "proposed_filename": f"REQUIRES REVIEW (candidate: {proposed})" if title and not is_bijoy_or_mojibake(title) else "REQUIRES REVIEW",
            "confidence": "REQUIRES REVIEW",
            "reason": reason,
        }

    return {
        "identified_book": identified_desc,
        "category": category,
        "proposed_filename": proposed,
        "confidence": "HIGH",
        "reason": reason,
    }


def inspect_single_file(rec: dict[str, Any], tmp_root: str) -> dict[str, Any]:
    """Run Stage B inspection on one file (cover thumbnail + PDF/EPUB metadata/pages)."""
    ocr_langs = pick_ocr_langs(rec)
    cov, cov_bytes = inspect_cover_thumbnail(rec)
    signals: dict[str, Any] = {**cov}
    ext = rec["ext"]
    local_p = os.path.join(tmp_root, f"{rec['id']}{ext}")

    try:
        if ext == ".pdf":
            cap = None if rec["size"] <= 35 * 1024 * 1024 else 15 * 1024 * 1024
            ok = download_drive_file_head(rec["id"], local_p, max_bytes=cap)
            if ok:
                signals.update(inspect_pdf_content(local_p, ocr_langs=ocr_langs))
            else:
                signals["access_error"] = "download_failed"
        elif ext == ".epub":
            ok = download_drive_file_head(rec["id"], local_p)
            if ok:
                signals.update(inspect_epub_content(local_p))
            else:
                signals["access_error"] = "download_failed"
        elif ext == ".txt":
            ok = download_drive_file_head(rec["id"], local_p, max_bytes=32768)
            if ok:
                with open(local_p, "r", encoding="utf-8", errors="replace") as f:
                    signals["text_sample"] = f.read(3000)
    finally:
        try:
            if os.path.exists(local_p):
                os.remove(local_p)
        except OSError:
            pass

    if (
        len((signals.get("text_sample") or "").strip()) < 120
        and len((signals.get("page1_ocr") or "").strip()) < 30
        and cov.get("cover_status") == "OK"
        and cov_bytes
    ):
        try:
            signals["cover_ocr"] = ocr_image_pil(Image.open(io.BytesIO(cov_bytes)), langs=ocr_langs)[:1200]
        except Exception:
            pass

    proposal = propose_name(rec, signals)
    return {
        **rec,
        "cover_status": signals.get("cover_status", "MISSING"),
        "cover_dims": f"{signals.get('cover_width', 0)}x{signals.get('cover_height', 0)}",
        "pdf_pages": signals.get("pdf_pages", 0),
        "is_scanned": signals.get("is_scanned", False),
        "meta_title": signals.get("pdf_title", ""),
        "meta_author": signals.get("pdf_author", ""),
        "access_error": signals.get("access_error", ""),
        **proposal,
    }


def detect_duplicates(results: list[dict[str, Any]], repo_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Detect exact MD5 duplicates, multi-volume sets, same-book groups, proposed collisions, and cross-catalog matches."""
    by_md5: dict[str, list[dict]] = collections.defaultdict(list)
    by_norm_title: dict[str, list[dict]] = collections.defaultdict(list)
    by_proposed_name: dict[str, list[dict]] = collections.defaultdict(list)
    series_groups: dict[str, list[dict]] = collections.defaultdict(list)

    series_pattern = re.compile(
        r"^(.*?)(?:[\s_-]+(?:part|vol|volume|খন্ড|খণ্ড|পর্ব|issue|no|edition|[\(\[])\s*([0-9ivx০-৯]+)[\)\]]?)(.*)$",
        re.I,
    )

    for r in results:
        if r.get("md5"):
            by_md5[r["md5"]].append(r)

        raw_name = r.get("name", "")
        m_ser = series_pattern.match(os.path.splitext(raw_name)[0])
        if m_ser:
            base_prefix = re.sub(r"[\W_]+", "", m_ser.group(1).lower())
            if len(base_prefix) >= 4:
                series_groups[base_prefix].append(r)

        norm = re.sub(r"[\W_]+", "", r.get("identified_book", "").lower())
        if len(norm) >= 6 and norm != "unaccessible":
            by_norm_title[norm].append(r)

        prop = r.get("proposed_filename", "")
        if prop and not prop.startswith("REQUIRES REVIEW") and r.get("confidence") == "HIGH":
            by_proposed_name[prop.lower()].append(r)

    exact_md5 = [
        {"md5": k, "count": len(v), "files": [{"id": x["id"], "name": x["name"], "folder": x["folder"]} for x in v]}
        for k, v in by_md5.items() if len(v) > 1
    ]
    multi_volume = [
        {"series_base": k, "count": len(v), "files": [{"id": x["id"], "name": x["name"], "folder": x["folder"]} for x in v]}
        for k, v in series_groups.items() if len(v) > 1
    ]
    same_book = [
        {"key": k, "count": len(v), "files": [{"id": x["id"], "name": x["name"], "folder": x["folder"], "size": x["size"]} for x in v]}
        for k, v in by_norm_title.items() if len(v) > 1
    ]
    proposed_collisions = [
        {"proposed_filename": v[0]["proposed_filename"], "count": len(v), "files": [{"id": x["id"], "name": x["name"], "folder": x["folder"]} for x in v]}
        for k, v in by_proposed_name.items() if len(v) > 1
    ]

    cross_catalog: list[dict] = []
    books_json_p = repo_dir / "books.json"
    if books_json_p.exists():
        cat = json.loads(books_json_p.read_text(encoding="utf-8"))
        cats = cat.get("cats", [])
        size_idx: dict[int, list[dict]] = collections.defaultdict(list)
        for b in cat.get("books", []):
            size_idx[b[7]].append({"id": b[0], "title": b[1], "author": b[2], "cat": cats[b[3]]})
        for r in results:
            matches = [m for m in size_idx.get(r["size"], []) if m["id"] != r["id"]]
            if matches:
                cross_catalog.append({"id": r["id"], "name": r["name"], "size": r["size"], "catalog_matches": matches[:5]})

    return {
        "exact_md5_duplicates": exact_md5,
        "multi_volume_series": multi_volume,
        "same_book_different_filename": same_book,
        "proposed_filename_collisions": proposed_collisions,
        "cross_catalog_size_matches": cross_catalog,
    }


def write_stage_c_reports(
    results: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    duplicates: dict[str, Any],
    target_label: str,
    out_dir: Path,
    slug: str,
) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"rename_report_{slug}.json"
    csv_path = out_dir / f"rename_report_{slug}.csv"
    md_path = out_dir / f"rename_report_{slug}.md"

    high = [r for r in results if r["confidence"] == "HIGH"]
    will_rename = [r for r in high if r["proposed_filename"] != r["name"]]
    review = [r for r in results if r["confidence"] != "HIGH"]
    unaccessible = [r for r in results if r.get("access_error")]
    covers_ok = sum(1 for r in results if r["cover_status"] == "OK")
    covers_missing = sum(1 for r in results if r["cover_status"] == "MISSING")
    covers_blank = sum(1 for r in results if r["cover_status"] in ("BLANK", "LOW_RES"))

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target_folder": target_label,
        "summary": {
            "total_inspected": len(results),
            "skipped_protected_or_non_book": len(skipped),
            "high_confidence_identified": len(high),
            "proposed_renames_high_confidence": len(will_rename),
            "requires_review": len(review),
            "unaccessible": len(unaccessible),
            "covers_ok": covers_ok,
            "covers_missing": covers_missing,
            "covers_blank_or_low_res": covers_blank,
        },
        "duplicates": duplicates,
        "results": results,
        "skipped": skipped,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["File ID", "Folder", "Current filename", "Identified book", "Category", "Proposed filename", "Confidence", "Cover Status", "Reason"])
        for r in results:
            w.writerow([r["id"], r["folder"], r["name"], r["identified_book"], r["category"], r["proposed_filename"], r["confidence"], r["cover_status"], r["reason"]])

    lines = [
        f"# Stage C Rename Report — `{target_label}`",
        "",
        f"- **Generated:** `{payload['generated_at']}`",
        f"- **Total files inspected:** `{len(results)}`",
        f"- **High-confidence verified:** `{len(high)}` (`{len(will_rename)}` with cleaner proposed filenames)",
        f"- **Marked `REQUIRES REVIEW`:** `{len(review)}` (untouched on Drive)",
        f"- **Unaccessible / Read errors:** `{len(unaccessible)}`",
        f"- **Cover Image Audit:** `{covers_ok}` OK · `{covers_missing}` Missing · `{covers_blank}` Blank/Low-res",
        f"- **Duplicates Detected (not deleted):** `{len(duplicates.get('exact_md5_duplicates', []))}` exact MD5 groups · `{len(duplicates.get('multi_volume_series', []))}` multi-volume/part series · `{len(duplicates.get('same_book_different_filename', []))}` same-book groups · `{len(duplicates.get('proposed_filename_collisions', []))}` proposed collisions · `{len(duplicates.get('cross_catalog_size_matches', []))}` cross-catalog size matches",
        "",
        "## Rename Table",
        "",
        "| Current filename | Identified book | Category | Proposed filename | Confidence | Cover |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        def esc(s: str) -> str:
            return (s or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {esc(r['name'])} | {esc(r['identified_book'])} | {esc(r['category'])} | {esc(r['proposed_filename'])} | {r['confidence']} | {r['cover_status']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, csv_path, md_path


# ---------------------------------------------------------------------------
# Stage D (Safe Rename) + Stage E (Verification) + Website/App Catalog Sync
# ---------------------------------------------------------------------------
def apply_and_verify_renames(report_json_path: Path, repo_dir: Path, slug: str) -> dict[str, Any]:
    data = json.loads(report_json_path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = data["results"]

    existing_by_parent: dict[str, set[str]] = collections.defaultdict(set)
    for r in results:
        existing_by_parent[r["parentId"]].add(r["name"].lower())

    rename_log: list[dict[str, Any]] = []
    skipped_collisions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for r in results:
        if r["confidence"] != "HIGH":
            continue
        old_name = r["name"]
        new_name = r["proposed_filename"]
        if not new_name or new_name.startswith("REQUIRES REVIEW") or new_name == old_name:
            continue
        if os.path.splitext(old_name)[1].lower() != os.path.splitext(new_name)[1].lower():
            errors.append({"id": r["id"], "old": old_name, "new": new_name, "error": "extension_mismatch_blocked"})
            continue
        if new_name.lower() in existing_by_parent[r["parentId"]]:
            skipped_collisions.append({"id": r["id"], "old": old_name, "new": new_name, "folder": r["folder"]})
            continue
        try:
            drive_request(
                "PATCH",
                f"/files/{r['id']}",
                params={"supportsAllDrives": "true", "fields": "id,name,parents"},
                body={"name": new_name},
            )
            existing_by_parent[r["parentId"]].discard(old_name.lower())
            existing_by_parent[r["parentId"]].add(new_name.lower())
            rename_log.append(
                {
                    "id": r["id"],
                    "folder": r["folder"],
                    "parentId": r["parentId"],
                    "old_name": old_name,
                    "new_name": new_name,
                    "identified_book": r["identified_book"],
                    "category": r["category"],
                }
            )
        except Exception as e:
            errors.append({"id": r["id"], "old": old_name, "new": new_name, "error": str(e)[:200]})

    # Stage E — Verification: re-fetch every renamed file from Google Drive
    verified = 0
    verification_failures: list[dict[str, Any]] = []
    for entry in rename_log:
        try:
            meta = drive_request(
                "GET",
                f"/files/{entry['id']}",
                params={"supportsAllDrives": "true", "fields": "id,name,parents,trashed"},
            )
            ok = (
                meta.get("name") == entry["new_name"]
                and not meta.get("trashed", False)
                and entry["parentId"] in (meta.get("parents") or [])
            )
            if ok:
                verified += 1
            else:
                verification_failures.append({"entry": entry, "live": meta})
        except Exception as e:
            verification_failures.append({"entry": entry, "error": str(e)[:200]})

    # Sync updated titles into root books.json and visualize/public/books.json (Website + App)
    renamed_map = {e["id"]: e for e in rename_log}
    catalog_updated_count = 0
    if renamed_map:
        for rel in ("books.json", "visualize/public/books.json"):
            p = repo_dir / rel
            if not p.exists():
                continue
            cat = json.loads(p.read_text(encoding="utf-8"))
            updated_here = 0
            for b in cat.get("books", []):
                bid = b[0]
                if bid in renamed_map:
                    stem = os.path.splitext(renamed_map[bid]["new_name"])[0]
                    if " - " in stem:
                        t_part, a_part = stem.rsplit(" - ", 1)
                        b[1] = t_part.strip()
                        if a_part.strip() and b[2] == "Unknown":
                            b[2] = a_part.strip()
                    else:
                        b[1] = stem.strip()
                    updated_here += 1
            if updated_here:
                cat["generated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
                p.write_text(json.dumps(cat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                catalog_updated_count = max(catalog_updated_count, updated_here)

    summary = {
        "applied_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "renamed_count": len(rename_log),
        "verified_count": verified,
        "verification_failures": len(verification_failures),
        "skipped_collisions": len(skipped_collisions),
        "errors": len(errors),
        "website_and_app_catalog_entries_synced": catalog_updated_count,
        "rename_log": rename_log,
        "collision_details": skipped_collisions,
        "error_details": errors,
        "verification_failure_details": verification_failures,
    }
    log_path = report_json_path.parent / f"rename_log_{slug}.json"
    log_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Intelligent Google Drive eBook Inspector & Safe Renamer")
    ap.add_argument("--target-folder", default="Review & Unclassified/Pending Review", help="Folder path under library root (or ALL)")
    ap.add_argument("--mode", choices=["dry_run", "apply_verified"], default="dry_run")
    ap.add_argument("--max-files", type=int, default=0, help="Optional cap for testing (0 = unlimited)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--include-qawmi", action="store_true")
    args = ap.parse_args()

    repo_dir = Path(args.repo_dir).resolve()
    out_dir = repo_dir / "reports" / "renamer"
    slug = re.sub(r"[^a-z0-9]+", "_", args.target_folder.lower()).strip("_") or "all"

    if args.mode == "apply_verified":
        report_json = out_dir / f"rename_report_{slug}.json"
        if not report_json.exists():
            raise RuntimeError(f"Stage C report not found at {report_json}. Run dry_run first.")
        summary = apply_and_verify_renames(report_json, repo_dir, slug)
        print(json.dumps({k: v for k, v in summary.items() if not k.endswith("details") and k != "rename_log"}, indent=2))
        return 0 if summary["verification_failures"] == 0 else 1

    print(f"[Stage A] Resolving & inventorying: {args.target_folder}", flush=True)
    fid, resolved_path = resolve_folder_path(args.target_folder)
    files, skipped, folders = walk_inventory(fid, resolved_path, include_qawmi=args.include_qawmi)
    print(f"[Stage A] Found {len(files)} book files across {len(folders)} folders ({len(skipped)} skipped/protected)", flush=True)

    if args.max_files > 0:
        files = files[: args.max_files]

    print(f"[Stage B] Inspecting covers, PDF/EPUB metadata & OCR with {args.workers} workers...", flush=True)
    t0 = time.time()
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="anabook_inspect_") as tmp_root:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(inspect_single_file, rec, tmp_root) for rec in files]
            for idx, fut in enumerate(concurrent.futures.as_completed(futs), 1):
                results.append(fut.result())
                if idx % 50 == 0 or idx == len(files):
                    print(f"  inspected {idx}/{len(files)} files ({time.time() - t0:.1f}s)...", flush=True)

    results.sort(key=lambda x: (x["folder"].lower(), x["name"].lower()))
    duplicates = detect_duplicates(results, repo_dir)
    json_p, csv_p, md_p = write_stage_c_reports(results, skipped, duplicates, resolved_path or "ROOT", out_dir, slug)
    summary = json.loads(json_p.read_text(encoding="utf-8"))["summary"]
    print("[Stage C] Complete:", json.dumps(summary, indent=2), flush=True)
    print(f"[Stage C] Reports written: {md_p}, {csv_p}, {json_p}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
