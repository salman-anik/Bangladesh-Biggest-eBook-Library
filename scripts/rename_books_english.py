"""Rename all Google Drive book folders and files to English transliteration.

Format:
  - With author:    Bookname_Author (folders) / Bookname_Author.ext (files)
  - Without author: Bookname (folders)        / Bookname.ext (files)

Uses data/merged_books.json from the Bangladesh-Biggest-eBook-Library repo
and tracks progress in data/english_rename_state.json for safe resumption.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LANGUAGE_SERVER = r"C:\Users\USER\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"
GDRIVE_BASE = (
    [LANGUAGE_SERVER, "plugin-cli", "gdrive"]
    if Path(LANGUAGE_SERVER).exists()
    else [shutil.which("gdrive") or "gdrive"]
)

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"

UNKNOWN_AUTHORS = {
    "",
    "various / unknown",
    "various / compiled (সংকলিত)",
    "various / compiled",
    "unknown",
    "n/a",
    "none",
    "anonymous",
}

# Common Bengali names & terms -> standard English spellings
KNOWN_WORDS: dict[str, str] = {
    "বাংলাদেশ": "Bangladesh",
    "বাংলা": "Bangla",
    "বাঙলা": "Bangla",
    "বাঙালী": "Bangali",
    "বাঙালি": "Bangali",
    "ইসলাম": "Islam",
    "ইসলামী": "Islami",
    "ইসলামিক": "Islamic",
    "মুহাম্মদ": "Muhammad",
    "মোহাম্মদ": "Mohammad",
    "মুহম্মদ": "Muhammed",
    "আহমেদ": "Ahmed",
    "আহমদ": "Ahmad",
    "রহমান": "Rahman",
    "হোসেন": "Hossain",
    "হাসান": "Hasan",
    "আলী": "Ali",
    "খাঁ": "Khan",
    "খান": "Khan",
    "চৌধুরী": "Chowdhury",
    "সরকার": "Sarkar",
    "মুখোপাধ্যায়": "Mukhopadhyay",
    "চট্টোপাধ্যায়": "Chattopadhyay",
    "বন্দ্যোপাধ্যায়": "Bandyopadhyay",
    "ভট্টাচার্য": "Bhattacharya",
    "গঙ্গোপাধ্যায়": "Gangopadhyay",
    "ঠাকুর": "Tagore",
    "রবীন্দ্রনাথ": "Rabindranath",
    "কাজী": "Kazi",
    "নজরুল": "Nazrul",
    "হুমায়ূন": "Humayun",
    "শরৎচন্দ্র": "Sarat Chandra",
    "বঙ্কিমচন্দ্র": "Bankim Chandra",
    "বিভূতিভূষণ": "Bibhutibhushan",
    "মানিক": "Manik",
    "তারাশঙ্কর": "Tarashankar",
    "জীবনানন্দ": "Jibanananda",
    "সুভাষ": "Subhash",
    "সুকান্ত": "Sukanta",
    "সত্যজিৎ": "Satyajit",
    "রায়": "Ray",
    "সেন": "Sen",
    "দাস": "Das",
    "দাশ": "Das",
    "গুপ্ত": "Gupta",
    "ঘোষ": "Ghosh",
    "বসু": "Basu",
    "মিত্র": "Mitra",
    "দত্ত": "Dutta",
    "দেবী": "Devi",
    "জাফর": "Zafar",
    "ইকবাল": "Iqbal",
    "আল": "Al",
    "কুরআন": "Quran",
    "কোরআন": "Quran",
    "হাদীস": "Hadith",
    "হাদিস": "Hadith",
    "তাফসীর": "Tafsir",
    "তাফসির": "Tafsir",
    "সীরাত": "Seerat",
    "সিরাত": "Sirat",
    "নবী": "Nabi",
    "রাসূল": "Rasul",
    "রাসুল": "Rasul",
    "আল্লাহ": "Allah",
    "ঢাকা": "Dhaka",
    "কলকাতা": "Kolkata",
    "ভারত": "Bharat",
    "ইতিহাস": "Itihas",
    "সাহিত্য": "Sahitya",
    "কবিতা": "Kobita",
    "গল্প": "Golpo",
    "ছোটগল্প": "Chotogolpo",
    "উপন্যাস": "Uponyas",
    "সমগ্র": "Somogro",
    "রচনাবলী": "Rochonaboli",
    "রচনাসমগ্র": "Rochonasomogro",
    "খণ্ড": "Khondo",
    "পর্ব": "Porbo",
    "অধ্যায়": "Odhyay",
    "কৃষি": "Krishi",
    "বিজ্ঞান": "Bigyan",
    "দর্শন": "Dorshon",
    "শ্রেণির": "Shrenir",
    "শ্রেণী": "Shreni",
    "মাধ্যমিক": "Madhyamik",
    "উচ্চমাধ্যমিক": "Ucchomadhyamik",
    "প্রাথমিক": "Prathomik",
    "জাতীয় শিক্ষাক্রম ও পাঠ্যপুস্তক বোর্ড": "NCTB",
}

VOWELS = {
    "অ": "o",
    "আ": "a",
    "ই": "i",
    "ঈ": "i",
    "উ": "u",
    "ঊ": "u",
    "ঋ": "ri",
    "এ": "e",
    "ঐ": "oi",
    "ও": "o",
    "ঔ": "ou",
}

MATRAS = {
    "া": "a",
    "ি": "i",
    "ী": "i",
    "ু": "u",
    "ূ": "u",
    "ৃ": "ri",
    "ে": "e",
    "ৈ": "oi",
    "ো": "o",
    "ৌ": "ou",
}

CONSONANTS = {
    "ক": "k",
    "খ": "kh",
    "গ": "g",
    "ঘ": "gh",
    "ঙ": "ng",
    "চ": "ch",
    "ছ": "chh",
    "জ": "j",
    "ঝ": "jh",
    "ঞ": "n",
    "ট": "t",
    "ঠ": "th",
    "ড": "d",
    "ঢ": "dh",
    "ণ": "n",
    "ত": "t",
    "থ": "th",
    "দ": "d",
    "ধ": "dh",
    "ন": "n",
    "প": "p",
    "ফ": "ph",
    "ব": "b",
    "ভ": "bh",
    "ম": "m",
    "য": "j",
    "র": "r",
    "ল": "l",
    "শ": "sh",
    "ষ": "sh",
    "স": "s",
    "হ": "h",
    "ড়": "r",
    "ঢ়": "rh",
    "য়": "y",
    "ৎ": "t",
    "ং": "ng",
    "ঃ": "h",
    "ঁ": "",
}

DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
BN_RE = re.compile(r"[\u0980-\u09ff]")

WATERMARK_PATTERNS = [
    r"\(?\s*(?:www\.)?(?:banglabook|bdebooks|ebanglalibrary|amarbooks|boimate|banglapdf|bengaliebooks|banglabooks|pdfbd|murchona|banglaebook|ebookbd|islamicbook|kitabghor|pathagar)\.(?:com|org|net|info|xyz)\s*\)?",
    r"[\[(]\s*(?:www\.)?[a-z0-9-]+\.(?:com|org|net|xyz|info)\s*[\])]",
    r"-?tanbircox(?:\.blogspot\.com)?",
    r"\[?\s*fb\.com/[^\]]+\]?",
    r"[\[(]\s*(?:downloaded|uploaded|scanned|courtesy)\s+by[^\])\n]*[\])]",
    r"\s+by\s+(?:bdebooks|boimate|amarbooks|banglabook)\s*$",
]

NON_AUTHOR_RIGHT_RE = re.compile(
    r"^(?:"
    r"part\s*\d+|vol\.?\s*\d+|volume\s*\d+|khondo\s*\d+|"
    r"\d+(?:st|nd|rd|th)?\s*(?:part|vol|khondo|edition)|"
    r"১ম|২য়|৩য়|৪র্থ|৫ম|৬ষ্ঠ|৭ম|৮ম|৯ম|১০ম|"
    r"nctb\s*\d*|ev|bv|"
    r".*\(nctb\s*\d*\)|"
    r".*শ্রেণি.*"
    r")$",
    re.I,
)


def transliterate_bn_word(word: str) -> str:
    """Transliterate a single Bengali Unicode word to phonetic English."""
    word = unicodedata.normalize("NFC", word).translate(DIGITS)
    word = word.replace("য\u09bc", "য়").replace("ড\u09bc", "ড়").replace("ঢ\u09bc", "ঢ়")
    if word in KNOWN_WORDS:
        return KNOWN_WORDS[word]
    if not BN_RE.search(word):
        return word

    out: list[str] = []
    n = len(word)
    i = 0
    while i < n:
        ch = word[i]
        if ch in VOWELS:
            out.append(VOWELS[ch])
            i += 1
        elif ch in CONSONANTS:
            c_sound = CONSONANTS[ch]
            if i + 2 < n and word[i + 1] == "্":
                next_c = word[i + 2]
                if next_c == "ব":
                    out.append(c_sound + ("w" if i == 0 else ""))
                    i += 3
                    if i < n and word[i] in MATRAS:
                        out.append(MATRAS[word[i]])
                        i += 1
                    elif i < n and word[i] in CONSONANTS and i + 1 < n:
                        out.append("o")
                    continue
                if next_c == "য":
                    # য-ফলা (ja-phala): initial 'y'/'ya', medial/final geminates consonant
                    if i == 0:
                        out.append(c_sound + "y")
                    else:
                        out.append(c_sound + c_sound)
                    i += 3
                    if i < n and word[i] in MATRAS:
                        out.append(MATRAS[word[i]])
                        i += 1
                    elif i < n and word[i] in ("ং", "ঃ", "ঁ", "ৎ"):
                        out.append("o")
                    elif i < n and word[i] in CONSONANTS and i + 1 < n:
                        out.append("o")
                    elif i == n:
                        out.append("o")
                    continue
                out.append(c_sound)
                i += 2
                continue

            out.append(c_sound)
            if i + 1 < n and word[i + 1] in MATRAS:
                out.append(MATRAS[word[i + 1]])
                i += 2
            elif i + 1 < n and word[i + 1] == "্":
                i += 2
            elif ch in ("ং", "ঃ", "ঁ", "ৎ"):
                i += 1
            else:
                if i + 1 < n and (word[i + 1] in CONSONANTS or word[i + 1] in ("ং", "ঃ")):
                    out.append("o")
                i += 1
        elif ch in MATRAS:
            out.append(MATRAS[ch])
            i += 1
        elif ch == "্":
            i += 1
        elif ch in ("।", "॥", "\u09bc"):
            i += 1
        else:
            out.append(ch)
            i += 1

    res = "".join(out)
    res = re.sub(r"([bcdfghjklmnpqrstvwxyz])\1{2,}", r"\1\1", res)
    return res


def to_english_translit(text: str) -> str:
    """Transliterate mixed Bengali/English text to clean Title-Case English."""
    if not text:
        return ""
    s = unicodedata.normalize("NFC", text).translate(DIGITS)
    for k, v in KNOWN_WORDS.items():
        if k in s and len(k) > 6:
            s = s.replace(k, v)

    tokens = re.split(r"(\s+|[-_/.,:;()\[\]{}]+)", s)
    out_tokens: list[str] = []
    for tok in tokens:
        if not tok:
            continue
        if BN_RE.search(tok):
            tr = transliterate_bn_word(tok)
            if tr and tr[0].islower():
                tr = tr[0].upper() + tr[1:]
            out_tokens.append(tr)
        else:
            out_tokens.append(tok)
    res = "".join(out_tokens)
    res = re.sub(r"\s+", " ", res).strip()
    return res


def sanitize_filename(name: str, max_len: int = 140) -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", name)
    s = re.sub(r"\s+", " ", s).strip(" ._-'")
    if len(s) > max_len:
        s = s[:max_len].strip(" ._-'")
    return s


def strip_noise(text: str) -> str:
    s = text.strip()
    if BN_RE.search(s) or any(sep in s for sep in ("_–_", "_—_", "_-_")):
        s = s.replace("_", " ")
    for pat in WATERMARK_PATTERNS:
        s = re.sub(pat, " ", s, flags=re.I)
    s = re.sub(r"\(\s*\d+\s*\)\s*$", "", s).strip()
    s = re.sub(r"\(\s*\)|\[\s*\]", "", s)
    s = re.sub(r"\s+", " ", s).strip(" -_")
    return s


def resolve_book_and_author(rec: dict) -> tuple[str, str]:
    """Return (english_bookname, english_author) for a merged_books.json record."""
    raw_title = strip_noise(rec.get("title") or rec.get("name") or "")
    raw_author = strip_noise(rec.get("author") or "")
    if raw_author.lower() in UNKNOWN_AUTHORS:
        raw_author = ""

    # Simplify NCTB author
    if "NCTB" in raw_author or "জাতীয় শিক্ষাক্রম" in raw_author:
        raw_author = "NCTB"

    # Strip duplicate " - <author>" from title if author is already known
    if raw_author and raw_title:
        for sep in (" - ", " – ", " — ", " ।। ", " || "):
            if raw_title.endswith(sep + raw_author):
                raw_title = raw_title[: -len(sep + raw_author)].strip()
                break
            elif raw_author in raw_title and sep in raw_title:
                parts = raw_title.rsplit(sep, 1)
                if raw_author.lower() in parts[1].lower():
                    raw_title = parts[0].strip()
                    break

    # If author is still empty, try splitting "Bookname - Author" (or en-dash/em-dash)
    if not raw_author:
        m_split = re.match(r"^(.+?)\s*(?:[-–—]{1,2}\s+|\s+[-–—]{1,2})\s*(.+)$", raw_title)
        if m_split:
            left, right = m_split.group(1).strip(), m_split.group(2).strip()
            if left and right and not NON_AUTHOR_RIGHT_RE.match(right) and len(right.split()) <= 6:
                raw_title = left
                raw_author = right

    en_title = sanitize_filename(to_english_translit(raw_title), max_len=110)
    en_author = sanitize_filename(to_english_translit(raw_author), max_len=60) if raw_author else ""

    if not en_title:
        en_title = sanitize_filename(to_english_translit(rec.get("name") or "Untitled"), max_len=110) or "Untitled"

    return en_title, en_author


def format_target_stem(en_title: str, en_author: str) -> str:
    if en_author and en_author.lower() != en_title.lower():
        return sanitize_filename(f"{en_title}_{en_author}", max_len=145)
    return sanitize_filename(en_title, max_len=145)


_TOKEN_LOCK = threading.Lock()
_ACCESS_TOKEN: str = ""
_TOKEN_EXPIRY: float = 0.0


def _get_drive_access_token() -> str | None:
    """Return a Google Drive OAuth2 access token from env secrets if configured."""
    global _ACCESS_TOKEN, _TOKEN_EXPIRY
    oauth_raw = os.environ.get("GDRIVE_OAUTH_JSON", "").strip()
    sa_raw = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON", "").strip()
    if not oauth_raw and not sa_raw:
        return None

    with _TOKEN_LOCK:
        if _ACCESS_TOKEN and time.time() < _TOKEN_EXPIRY - 60:
            return _ACCESS_TOKEN

        if oauth_raw:
            creds = json.loads(oauth_raw)
            body = urllib.parse.urlencode(
                {
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                    "refresh_token": creds["refresh_token"],
                    "grant_type": "refresh_token",
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                tok = json.loads(resp.read().decode("utf-8"))
            _ACCESS_TOKEN = tok["access_token"]
            _TOKEN_EXPIRY = time.time() + float(tok.get("expires_in", 3600))
            return _ACCESS_TOKEN

        if sa_raw:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request as GoogleAuthRequest

            sa_info = json.loads(sa_raw)
            creds = service_account.Credentials.from_service_account_info(
                sa_info, scopes=["https://www.googleapis.com/auth/drive"]
            )
            creds.refresh(GoogleAuthRequest())
            _ACCESS_TOKEN = creds.token
            _TOKEN_EXPIRY = time.time() + 3000
            return _ACCESS_TOKEN
    return None


def _gd_rename_rest(file_id: str, new_name: str, retries: int = 4) -> tuple[bool, str]:
    for attempt in range(retries):
        try:
            token = _get_drive_access_token()
            if not token:
                return False, "No Drive API token"
            url = f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(file_id)}?supportsAllDrives=true"
            payload = json.dumps({"name": new_name}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                method="PATCH",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if 200 <= resp.status < 300:
                    return True, ""
                return False, f"HTTP {resp.status}"
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", "ignore")[:150]
            if exc.code in (403, 429, 500, 502, 503):
                time.sleep(min(16.0, 2.0 ** (attempt + 1)))
                continue
            return False, f"HTTP {exc.code}: {err_body}"
        except Exception as exc:
            if attempt + 1 < retries:
                time.sleep(1.5)
                continue
            return False, str(exc)[:150]
    return False, "max retries exceeded"


def _gd_get_meta_rest(file_id: str) -> dict:
    for attempt in range(3):
        try:
            token = _get_drive_access_token()
            if not token:
                return {}
            url = (
                f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(file_id)}"
                "?supportsAllDrives=true&fields=name,size"
            )
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return {}


def gd_rename(file_id: str, new_name: str, retries: int = 3) -> tuple[bool, str]:
    if os.environ.get("GDRIVE_OAUTH_JSON") or os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON"):
        return _gd_rename_rest(file_id, new_name, retries=retries)
    for attempt in range(retries):
        try:
            res = subprocess.run(
                GDRIVE_BASE + ["mutate", "rename", file_id, new_name],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if res.returncode == 0:
                return True, ""
            err = (res.stderr or res.stdout or "").strip()
            if any(k in err.lower() for k in ("429", "500", "502", "503", "rate", "quota", "eof", "timeout", "backend error")):
                time.sleep(2 ** (attempt + 1))
                continue
            return False, err[:150]
        except Exception as exc:
            if attempt + 1 < retries:
                time.sleep(1.5)
                continue
            return False, str(exc)[:150]
    return False, "max retries exceeded"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Rename Drive book folders & files to English Bookname_Author.")
    parser.add_argument("--category", default="", help="Filter by top_category (e.g. 'Agriculture and Nature')")
    parser.add_argument("--dry-run", action="store_true", help="Preview renames without modifying Google Drive")
    parser.add_argument("--csv-out", default="", help="Optional CSV path to write rename preview/log")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent rename workers (default: 8)")
    parser.add_argument("--limit", type=int, default=0, help="Max number of books to process (0 = all)")
    args = parser.parse_args()

    merged_path = DATA_DIR / "merged_books.json"
    state_path = DATA_DIR / "english_rename_state.json"

    all_books = json.loads(merged_path.read_text(encoding="utf-8"))
    books = all_books
    if args.category:
        books = [b for b in all_books if (b.get("top_category") or "").lower() == args.category.lower()]
    if args.limit > 0:
        books = books[: args.limit]

    # Backfill real title & byte size for 0-size / raw-Drive-ID books via Drive REST API
    if not args.dry_run and _get_drive_access_token():
        zero_books = [
            b for b in books
            if not b.get("size") or re.fullmatch(r"[A-Za-z0-9_-]{25,45}", b.get("name") or "")
        ]
        if zero_books:
            print(f"Backfilling Drive metadata (name/size) for {len(zero_books)} books...", flush=True)

            def _backfill_one(b: dict) -> bool:
                changed = False
                raw_n = b.get("name") or ""
                is_raw_id = bool(re.fullmatch(r"[A-Za-z0-9_-]{25,45}", raw_n))
                meta = _gd_get_meta_rest(raw_n if is_raw_id else (b.get("file_id") or ""))
                if not meta.get("size") and b.get("file_id"):
                    meta2 = _gd_get_meta_rest(b["file_id"])
                    if meta2.get("size"):
                        meta["size"] = meta2["size"]
                if is_raw_id and meta.get("name"):
                    real_stem = Path(meta["name"]).stem
                    if real_stem and not re.fullmatch(r"[A-Za-z0-9_-]{25,45}", real_stem):
                        b["name"] = real_stem
                        b["title"] = real_stem
                        changed = True
                if meta.get("size") and not b.get("size"):
                    sz = int(meta["size"])
                    b["size"] = sz
                    for f in b.get("files") or []:
                        if not f.get("size"):
                            f["size"] = sz
                    changed = True
                return changed

            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                bf_results = list(pool.map(_backfill_one, zero_books))
            print(f"Backfilled metadata for {sum(1 for x in bf_results if x)}/{len(zero_books)} books.", flush=True)

    state = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.exists()
        else {"renamed": {}}
    )
    renamed_map: dict[str, str] = state.setdefault("renamed", {})

    # Collect (id, old_name, new_name, kind, category)
    ops: list[tuple[str, str, str, str, str]] = []
    seen_ids: set[str] = set()
    book_targets: list[tuple[dict, str, str, str]] = []

    for b in books:
        en_title, en_author = resolve_book_and_author(b)
        target_stem = format_target_stem(en_title, en_author)
        cat = b.get("top_category") or ""
        book_targets.append((b, en_title, en_author, target_stem))

        fid = b.get("folder_id") or ""
        old_folder_name = b.get("name") or ""
        if fid and fid not in seen_ids and renamed_map.get(fid) != target_stem:
            seen_ids.add(fid)
            if target_stem and target_stem != old_folder_name:
                ops.append((fid, old_folder_name, target_stem, "folder", cat))

        for f in b.get("files") or []:
            f_id = f.get("id") or ""
            f_old = f.get("name") or ""
            if not f_id or f_id in seen_ids:
                continue
            seen_ids.add(f_id)
            ext = Path(f_old).suffix.lower()
            if not ext:
                mt = (f.get("mimeType") or "").lower()
                if "pdf" in mt:
                    ext = ".pdf"
                elif "epub" in mt:
                    ext = ".epub"
                elif "json" in mt:
                    ext = ".json"
                elif "jpeg" in mt or "jpg" in mt:
                    ext = ".jpg"
                elif "text" in mt:
                    ext = ".txt"
            new_fname = f"{target_stem}{ext}"
            if new_fname != f_old and renamed_map.get(f_id) != new_fname:
                ops.append((f_id, f_old, new_fname, "file", cat))

    print(f"Books matched: {len(books)} | Pending Drive renames: {len(ops)}", flush=True)

    if args.csv_out:
        csv_p = Path(args.csv_out)
        csv_p.parent.mkdir(parents=True, exist_ok=True)
        with csv_p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "kind", "category", "old_name", "new_name"])
            for oid, old_n, new_n, kind, cat in ops:
                w.writerow([oid, kind, cat, old_n, new_n])
        print(f"Wrote preview CSV to {csv_p}", flush=True)

    if args.dry_run:
        for oid, old_n, new_n, kind, cat in ops[:30]:
            print(f"  [{kind}] {old_n!r} -> {new_n!r}")
        if len(ops) > 30:
            print(f"  ... and {len(ops) - 30} more.")
        return

    done = 0
    failed = 0
    total = len(ops)

    if ops:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(gd_rename, oid, new_n): (oid, old_n, new_n)
                for oid, old_n, new_n, _, _ in ops
            }
            for fut in concurrent.futures.as_completed(futures):
                oid, old_n, new_n = futures[fut]
                ok, err = fut.result()
                if ok:
                    renamed_map[oid] = new_n
                    done += 1
                else:
                    failed += 1
                    print(f"  FAIL {oid} ({old_n!r} -> {new_n!r}): {err}", flush=True)
                if (done + failed) % 100 == 0 or (done + failed) == total:
                    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
                    print(f"Progress: {done}/{total} renamed ({failed} failed)", flush=True)

    # Sync English names, extracted authors, and filenames back into data/merged_books.json
    updated_records = 0
    for b, en_title, en_author, target_stem in book_targets:
        if not target_stem:
            continue
        if b.get("name") != target_stem:
            b["name"] = target_stem
            updated_records += 1
        if en_title and b.get("title") != en_title:
            b["title"] = en_title
        cur_auth = (b.get("author") or "").strip()
        if en_author and (cur_auth.lower() in UNKNOWN_AUTHORS or BN_RE.search(cur_auth)):
            b["author"] = en_author
        elif cur_auth and BN_RE.search(cur_auth):
            b["author"] = sanitize_filename(to_english_translit(cur_auth), max_len=60) or cur_auth
        for f in b.get("files") or []:
            f_old = f.get("name") or ""
            ext = Path(f_old).suffix.lower() or ".pdf"
            f["name"] = f"{target_stem}{ext}"

    merged_path.write_text(json.dumps(all_books, ensure_ascii=False), encoding="utf-8")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Finished! Drive renamed: {done} (failed: {failed}) | Updated {updated_records} records in merged_books.json",
        flush=True,
    )


if __name__ == "__main__":
    main()
