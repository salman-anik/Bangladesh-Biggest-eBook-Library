import concurrent.futures
import html as html_lib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR / "scripts"))

import build_25cat_library as b25  # noqa: E402

GDRIVE = shutil.which("gdrive") or "gdrive"
DATA_DIR = REPO_DIR / "data"
TMP_DIR = REPO_DIR / "tmp_downloads"
EXTRA_FILE = DATA_DIR / "extra_books.json"
STATE_FILE = DATA_DIR / "taxonomy_state.json"

LOCK = threading.Lock()
BOOK_EXTS = (".pdf", ".epub", ".djvu", ".mobi", ".azw3", ".doc", ".docx", ".txt", ".ppt", ".pptx", ".json")

NCTB_SEED_PAGES = [
    "695b97ffc4774958d7b70329",  # 2026 textbooks root
    "695b9b7cc4774958d7b70a12",  # 2026 pre-primary & primary
    "695b98afc4774958d7b7044c",  # 2026 secondary, dakhil, vocational, higher secondary
    "6922df2c933eb65569e20586",  # 2025 textbooks root
    "6922de68933eb65569e1a70c",  # 2024 textbooks root
]

SHARED_AND_PUBLIC_DRIVE_FOLDERS = [
    ("1DPvEvhugj1GukZpmjYmlc24QSyoHKLHf", "Shared Engineering BOOKS"),
    ("1lLK2PXw6pkDfcnbfTBtdqtIxiMSSXdyO", "Shared Islamic Books (israt)"),
    ("1Y9ZV7qi-DC6qe_FXnO4GsUIbZQJMxe4t", "Shared Islamic & General Books (irfan)"),
    ("1-6tRHRU79tAH2_n-h6TrqJwLdkTs07P3", "BD Public e-Library (ই-লাইব্রেরি)"),
    ("1Xgx-1iYultvaFUesabcqQkmn41pCxVYV", "COVID-19 Health Books (tanbircox)"),
    ("16ava6Q1Rd8mXr9ncqcYKz66gDv_iH-Xa", "University Physics - Properties of Matter"),
    ("1xJws1mFpc2oI0M5a02GEHH3kH3A5wN05", "University Physics - Medical Physics"),
    ("1dIexu2wqI-WgnrchDkyyuLz8JLJi6tb0", "University Physics - Gravitation and Gravity"),
    ("16Xzib_UdoMmkFasq6kIGFUYOwHYiKlG1", "University Physics - Lasers and Fiber Optics"),
    ("1YBKQPNTk5DVpXtVPCODo-3FrwOz2IJfa", "University Physics - Mechanics"),
    ("1ExW_LYI4il2T6gbTVleTjmpvdGOUxnmf", "University Physics - Classical Electrodynamics II"),
    ("1fkYHdgSDE9_oy5cNREb9Zg-5qrOlBcbN", "University Physics - Waves Oscillations & Optics"),
    ("11teOGLddeiq4JJebZUI7z1TnIm1TKV22", "University Physics - Geophysics & 4th Year"),
    ("1gYfUSW2DszezgTdomHPgvGtdkiueSt8g", "University Physics - Classical Electrodynamics I"),
    ("1Q_eJnsDNn7igVbzcoBrUz3PRVHOiCKbw", "University Physics - Fundamentals of Physics"),
    ("1vOrfTq4mKAnDEUINAdH1F__-2GRVHeNU", "University Physics - Waves and Sound"),
    ("1bNImnMOgiMGgZIzu_FNanlijI-__VXf7", "University Physics - 1st Year"),
    ("1bdFSO34xjDxA_1awNYiw4Ujql4yaTkon", "University Physics - Reactor Physics"),
    ("1cJUm6ddAsL2vqQkEMKNtDm3dYdoOUuAr", "University Physics - PHY 1109"),
]

# Subject mapping for Archive.org to fill all 25 categories and BD / Bangla books
ARCHIVE_CATEGORY_QUERIES = [
    ("bengali_general_1", 'mediatype:texts AND (language:ben OR language:bengali) AND format:"Text PDF"', None, 80),
    ("05_cs", 'mediatype:texts AND subject:("computer science" OR "programming") AND format:"Text PDF"', "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Computer_Science_কম্পিউটার_বিজ্ঞান", 12),
    ("10_psych", 'mediatype:texts AND subject:("psychology" OR "cognitive psychology") AND format:"Text PDF"', "10_Psychology_and_Mind_মনোবিজ্ঞান_ও_মানসিকতা/Cognitive_Psychology", 12),
    ("11_biz", 'mediatype:texts AND subject:("economics" OR "accounting" OR "finance") AND format:"Text PDF"', "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Finance_ফাইন্যান্স", 12),
    ("12_law", 'mediatype:texts AND (title:"Bangladesh" OR subject:("constitutional law" OR "international law")) AND subject:"law" AND format:"Text PDF"', "12_Law_and_Legal_আইন_ও_বিচার/Constitutional_Law_সাংবিধানিক_আইন", 12),
    ("14_eng", 'mediatype:texts AND subject:("electrical engineering" OR "mechanical engineering" OR "civil engineering") AND format:"Text PDF"', "14_Engineering_প্রকৌশল/Electrical_Engineering", 12),
    ("17_bio", 'mediatype:texts AND (language:ben OR title:"Bengal" OR title:"Tagore" OR title:"Bangladesh") AND subject:"biography" AND format:"Text PDF"', "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী/Historical_Personalities", 10),
    ("20_agri", 'mediatype:texts AND subject:("agriculture" OR "botany") AND format:"Text PDF"', "20_Agriculture_and_Nature_কৃষি_ও_প্রকৃতি/Agriculture_কৃষি", 12),
    ("21_travel", 'mediatype:texts AND (title:"Bengal" OR title:"Bangladesh" OR subject:"travel") AND format:"Text PDF"', "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল/Bangladesh_বাংলাদেশ", 12),
    ("24_mag", 'mediatype:texts AND (language:ben OR title:"Bengal") AND (subject:"periodicals" OR title:"magazine" OR title:"journal") AND format:"Text PDF"', "24_Magazines_and_Periodicals_সাময়িকী/Literary_Magazines", 12),
    ("25_rare", 'mediatype:texts AND (language:ben OR language:bengali) AND (subject:"manuscripts" OR title:"puthi" OR title:"পুঁথি") AND format:"Text PDF"', "25_Others_and_Unclassified_অন্যান্য/Rare_Books", 10),
]


def norm_name(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\.[a-z0-9]{2,5}$", "", s)
    s = s.replace("_compressed", "").replace("-compressed", "")
    s = re.sub(r"[\s_\-]+", " ", s).strip()
    return s


def safe_filename(name: str, default_ext: str = ".pdf") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n\t]+', " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    if not cleaned:
        cleaned = "untitled"
    if not re.search(r"\.[a-zA-Z0-9]{2,5}$", cleaned):
        cleaned += default_ext
    if len(cleaned) > 150:
        stem, ext = os.path.splitext(cleaned)
        cleaned = stem[:145].strip() + ext
    return cleaned


def parse_gdrive_id(output: str) -> str | None:
    txt = output.strip()
    if txt.startswith("{"):
        try:
            obj = json.loads(txt)
            if obj.get("id"):
                return obj["id"]
        except Exception:
            pass
    m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", txt)
    if m:
        return m.group(1)
    return None


def gdrive_ls(folder_id: str) -> list[dict]:
    for attempt in range(3):
        res = subprocess.run(
            [GDRIVE, "readonly", "ls", folder_id, "--max", "0", "--json"],
            capture_output=True, text=True, encoding="utf-8"
        )
        if res.returncode == 0 and res.stdout.strip():
            try:
                return json.loads(res.stdout)
            except Exception:
                pass
        time.sleep(0.5 * (attempt + 1))
    return []


def gdrive_info(file_id: str) -> dict | None:
    res = subprocess.run(
        [GDRIVE, "readonly", "info", file_id, "--json"],
        capture_output=True, text=True, encoding="utf-8"
    )
    if res.returncode == 0 and res.stdout.strip():
        try:
            return json.loads(res.stdout)
        except Exception:
            pass
    return None


def gdrive_cp(source_id: str, new_name: str, parent_id: str) -> str | None:
    for attempt in range(3):
        res = subprocess.run(
            [GDRIVE, "mutate", "cp", source_id, new_name, "--parent", parent_id],
            capture_output=True, text=True, encoding="utf-8"
        )
        if res.returncode == 0:
            fid = parse_gdrive_id(res.stdout)
            if fid:
                return fid
        err = (res.stderr or "") + (res.stdout or "")
        if any(x in err.lower() for x in ["not found", "404", "403", "cannot copy", "permission"]):
            return None
        time.sleep(0.8 * (attempt + 1))
    return None


def gdrive_upload(local_path: Path, parent_id: str) -> str | None:
    for attempt in range(3):
        res = subprocess.run(
            [GDRIVE, "mutate", "upload", str(local_path), "--parent", parent_id],
            capture_output=True, text=True, encoding="utf-8"
        )
        if res.returncode == 0:
            fid = parse_gdrive_id(res.stdout)
            if fid:
                return fid
        time.sleep(1.0 * (attempt + 1))
    return None


def build_rec(
    source_id: str,
    file_id: str,
    name: str,
    size: int,
    mime: str,
    leaf_path: str,
    author: str,
    publication: str,
    subfolder: str | None = None,
) -> dict:
    parts = leaf_path.split("/")
    return {
        "source_id": source_id,
        "file_id": file_id,
        "name": name,
        "size": int(size or 0),
        "mimeType": mime or ("application/epub+zip" if name.lower().endswith(".epub") else "application/pdf"),
        "top_category": parts[0],
        "leaf_path": leaf_path,
        "leaf_category": parts[-1],
        "subfolder": subfolder,
        "author": author,
        "publication": publication,
        "link": f"https://drive.google.com/file/d/{file_id}/view",
    }


def classify_nctb(title: str, page_title: str) -> str:
    text = f"{title} {page_title}".lower()
    if any(k in text for k in ["তথ্য ও যোগাযোগ প্রযুক্তি", "information and communication technology", "কম্পিউটার", "প্রোগ্রামিং"]):
        return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Computer_Science_কম্পিউটার_বিজ্ঞান"
    if any(k in text for k in ["হিসাববিজ্ঞান", "accounting"]):
        return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Accounting_হিসাববিজ্ঞান"
    if any(k in text for k in ["ফিন্যান্স", "ব্যাংকিং", "finance", "banking"]):
        return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Finance_ফাইন্যান্স"
    if any(k in text for k in ["ব্যবসায় উদ্যোগ", "ব্যবসায় উদ্যোগ", "entrepreneurship"]):
        return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Entrepreneurship_উদ্যোক্তা"
    if any(k in text for k in ["ব্যবসায় সংগঠন", "ব্যবসায় সংগঠন", "উৎপাদন ব্যবস্থাপনা", "বিপণন", "marketing", "business"]):
        return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Business_Management_ব্যবসা_পরিচালনা"
    if any(k in text for k in ["কৃষি", "agriculture"]):
        return "20_Agriculture_and_Nature_কৃষি_ও_প্রকৃতি/Agriculture_কৃষি"
    if any(k in text for k in ["ভূগোল", "geography"]):
        return "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল/Bangladesh_বাংলাদেশ"
    if any(k in text for k in ["মনোবিজ্ঞান", "psychology"]):
        return "10_Psychology_and_Mind_মনোবিজ্ঞান_ও_মানসিকতা/Cognitive_Psychology"
    if any(k in text for k in ["পৌরনীতি", "civics", "আইন", "সংবিধান"]):
        return "12_Law_and_Legal_আইন_ও_বিচার/Constitutional_Law_সাংবিধানিক_আইন"
    if any(k in text for k in ["ইলেকট্রিক্যাল", "ইঞ্জিনিয়ারিং", "মেকানিক্যাল", "সিভিল", "অটোমোবাইল", "ওয়েল্ডিং", "রেফ্রিজারেশন", "ড্রাফটিং", "engineering", "electrical", "electronics", "civil", "mechanical"]):
        return "14_Engineering_প্রকৌশল/Electrical_Engineering"

    # Otherwise classify by education level
    if any(k in page_title for k in ["প্রাক-প্রাথমিক", "প্রথম", "১ম", "দ্বিতীয়", "২য়", "তৃতীয়", "৩য়", "চতুর্থ", "৪র্থ", "পঞ্চম", "৫ম", "প্রাথমিক", "ইবতেদায়ি", "ইবতেদায়ী"]):
        return "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Primary_Education"
    if any(k in page_title for k in ["ষষ্ঠ", "৬ষ্ঠ", "সপ্তম", "৭ম", "অষ্টম", "৮ম", "নবম", "দশম", "৯ম", "১০ম", "মাধ্যমিক", "দাখিল", "কারিগরি", "ভোকেশনাল"]):
        if "উচ্চ মাধ্যমিক" in page_title:
            return "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Higher_Secondary"
        return "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Secondary_Education"
    if any(k in page_title for k in ["উচ্চ মাধ্যমিক", "একাদশ", "দ্বাদশ", "আলিম"]):
        return "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Higher_Secondary"
    return "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Academic_Textbooks"


def classify_general_bd_book(name: str, folder_path: str = "", source_label: str = "") -> str:
    text = f"{folder_path} {name} {source_label}".lower()

    if any(k in text for k in ["mano", "tocci", "digital logic", "electrical", "electronics", "circuit", "power system"]):
        return "14_Engineering_প্রকৌশল/Electrical_Engineering"
    if any(k in text for k in ["mechanical", "thermodynamics", "fluid mechanics", "manufacturing"]):
        return "14_Engineering_প্রকৌশল/Mechanical_Engineering"
    if any(k in text for k in ["civil engineering", "structural", "concrete", "surveying"]):
        return "14_Engineering_প্রকৌশল/Civil_Engineering"
    if any(k in text for k in ["covid", "coronavirus", "clinical", "medical", "health", "medicine", "চিকিৎসা", "স্বাস্থ্য", "রোগ", "ডাক্তার"]):
        return "13_Medicine_and_Health_চিকিৎসা_ও_স্বাস্থ্য/Public_Health_জনস্বাস্থ্য"
    if any(k in text for k in ["reactor physics", "gravitation", "electrodynamics", "mechanics", "optics", "waves", "physics", "পদার্থ"]):
        return "04_Science_বিজ্ঞান/Physics_পদার্থবিজ্ঞান"
    if any(k in text for k in ["programming", "python", "javascript", "java", "c++", "algorithm", "software", "computer", "প্রোগ্রামিং", "কম্পিউটার", "ডাটাবেজ", "হ্যাকিং"]):
        return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Computer_Science_কম্পিউটার_বিজ্ঞান"
    if any(k in text for k in ["magazine", "tahreek", "তাহরীক", "dawatul haq", "মাসিক", "পত্রিকা", "সাময়িকী", "সবুজপত্র", "সওগাত"]):
        return "24_Magazines_and_Periodicals_সাময়িকী/Religious_Magazines" if "tahreek" in text or "তাহরীক" in text or "dawatul" in text else "24_Magazines_and_Periodicals_সাময়িকী/Literary_Magazines"
    if any(k in text for k in ["bcs", "বিসিএস", "job solution", "জব সলিউশন", "প্রাইমারি শিক্ষক", "নিবন্ধন", "bank job"]):
        return "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Competitive_Exams"
    if any(k in text for k in ["admission", "ভর্তি", "buet", "medical admission", "university question"]):
        return "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Admission_Preparation"
    if any(k in text for k in ["accounting", "finance", "marketing", "business", "investment", "অর্থনীতি", "ব্যাংকিং"]):
        return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Finance_ফাইন্যান্স"
    if any(k in text for k in ["psychology", "মনোবিজ্ঞান", "মানসিক", "মস্তিষ্ক"]):
        return "10_Psychology_and_Mind_মনোবিজ্ঞান_ও_মানসিকতা/Cognitive_Psychology"
    if any(k in text for k in ["law", "constitution", "penal code", "আইন", "সংবিধান", "ফৌজদারি"]):
        return "12_Law_and_Legal_আইন_ও_বিচার/Bangladesh_Law_বাংলাদেশের_আইন"
    if any(k in text for k in ["agriculture", "কৃষি", "বাগান", "মাছ চাষ", "বনায়ন"]):
        return "20_Agriculture_and_Nature_কৃষি_ও_প্রকৃতি/Agriculture_কৃষি"
    if any(k in text for k in ["travel", "ভ্রমণ", "পথে প্রবাসে", "দেশ বিদেশে"]):
        return "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল/Travel_Memoirs_ভ্রমণ_স্মৃতিকথা"

    # Reuse build_25cat_library.classify_book_leaf for Islamic / Literature / History / Arabic
    cat_hint = "01 - Quran & Tafsir"
    if any(k in text for k in ["hadith", "হাদিস", "হাদীস", "বুখারী", "মুসলিম", "তিরমিযী", "albani", "সহীহ"]):
        cat_hint = "02 - Hadith & Sunnah"
    elif any(k in text for k in ["arabic", "আরবি", "আরবী", "arbi", "ব্যাকরণ"]):
        cat_hint = "05 - Arabic Language & Dictionaries"
    elif any(k in text for k in ["উপন্যাস", "গল্প", "কবিতা", "সাহিত্য", "রবীন্দ্র", "নজরুল", "শরৎচন্দ্র", "বঙ্কিম", "হুমায়ূন", "হুমায়ূন", "সত্যজিৎ", "আনিসুল", "আহসান হাবীব", "মানিক", "জীবনানন্দ", "সুনীল", "শীর্ষেন্দু", "সমরেশ", "বিভূতিভূষণ", "মাইকেল", "মীর মশাররফ", "বেগম রোকেয়া", "সুকুমার"]):
        cat_hint = "06 - Literature & Authors (Mrinal e-Library)"

    dummy_item = {
        "category": cat_hint,
        "subfolder": "General",
        "name": name,
        "source_path": folder_path,
    }
    tp, leaf, _, _ = b25.classify_book_leaf(dummy_item)
    return f"{tp}/{leaf}"


def extract_author_clean(name: str, folder_hint: str = "", default: str = "Various / Compiled (সংকলিত)") -> str:
    if folder_hint and "/" not in folder_hint and folder_hint not in {"General", "অজ্ঞাত", "Translation", "Discussion"}:
        # e.g. eedeidk/bongboi author folder
        pass
    item = {"category": "06 - Literature & Authors (Mrinal e-Library)", "subfolder": "বিবিধ", "name": name}
    auth = b25.extract_author(item)
    if auth != "Various / Compiled (সংকলিত)":
        return auth
    return default


def crawl_nctb_books() -> list[dict]:
    visited = set()
    to_visit = list(NCTB_SEED_PAGES)
    found = {}  # fid -> {title, page_title, year, version}

    def fetch(url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")

    for _depth in range(3):
        next_batch = []
        for pid in to_visit:
            if pid in visited:
                continue
            visited.add(pid)
            try:
                html = fetch(f"https://nctb.gov.bd/pages/static-pages/{pid}")
            except Exception as e:
                print(f"  [NCTB warn] failed {pid}: {e}", flush=True)
                continue

            m_title = re.search(r"<title>(.*?)</title>", html, re.S)
            raw_title = html_lib.unescape(m_title.group(1)).strip() if m_title else "NCTB Textbook"
            page_title = raw_title.split("|")[0].strip()

            m_yr = re.search(r"(২০২[৩-৭]|202[3-7])", page_title)
            yr_map = {"২০২৪": "2024", "২০২৫": "2025", "২০২৬": "2026", "২০২৭": "2027"}
            year = yr_map.get(m_yr.group(1), m_yr.group(1)) if m_yr else "2026"

            m_rt = re.search(r"<rt-renderer[^>]*>(.*?)</rt-renderer>", html, re.S)
            body = m_rt.group(1) if m_rt else html

            for sub_pid in re.findall(r"/pages/static-pages/([a-zA-Z0-9_-]+)", body):
                if sub_pid not in visited:
                    next_batch.append(sub_pid)

            # Parse rows inside tables for crisp subject titles
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S)
            for row in rows:
                tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
                if not tds:
                    continue
                last_label = ""
                for idx, td in enumerate(tds):
                    txt = html_lib.unescape(re.sub(r"<[^>]+>", " ", td))
                    txt = re.sub(r"\s+", " ", txt).strip()
                    ids = re.findall(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", td)
                    ids += re.findall(r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)", td)
                    if ids:
                        subject = last_label or page_title
                        # Clean noise phrases
                        if any(skip in subject for skip in ["পাঠ্যপুস্তকের নাম", "ক্রমিক", "ডাউনলোড"]):
                            subject = page_title
                        ver = "EV" if (idx >= 3 and len(tds) >= 5) else "BV"
                        for fid in ids:
                            if fid not in found:
                                found[fid] = {
                                    "fid": fid,
                                    "subject": subject,
                                    "page_title": page_title,
                                    "year": year,
                                    "ver": ver,
                                }
                    elif txt and "ডাউনলোড" not in txt and not re.match(r"^[০-৯0-9।.\s]+$", txt):
                        last_label = txt

            # Also pick up any standalone drive links in <rt-renderer> outside <tr>
            for m_link in re.finditer(r'<a[^>]*href=["\']([^"\']*drive\.google\.com/(?:file/d/|open\?id=)([a-zA-Z0-9_-]+)[^"\']*)["\'][^>]*>(.*?)</a>', body, re.S):
                fid = m_link.group(2)
                if fid not in found:
                    ltxt = html_lib.unescape(re.sub(r"<[^>]+>", " ", m_link.group(3)))
                    ltxt = re.sub(r"\s+", " ", ltxt).strip()
                    if not ltxt or "ডাউনলোড" in ltxt or "লিংক" in ltxt:
                        ltxt = page_title
                    found[fid] = {
                        "fid": fid,
                        "subject": ltxt,
                        "page_title": page_title,
                        "year": year,
                        "ver": "",
                    }
        to_visit = next_batch

    print(f"Crawled {len(visited)} NCTB pages -> {len(found)} unique NCTB Google Drive PDFs.", flush=True)
    return list(found.values())


def scan_drive_folder_recursive(root_fid: str, label: str, max_depth: int = 4) -> list[dict]:
    results = []
    seen_folders = set()

    def walk(fid: str, rel_path: str, depth: int):
        if fid in seen_folders or depth > max_depth:
            return
        seen_folders.add(fid)
        items = gdrive_ls(fid)
        for it in items:
            mt = it.get("mimeType", "")
            name = it.get("name", "")
            iid = it.get("id", "")
            if mt == "application/vnd.google-apps.folder":
                walk(iid, f"{rel_path}/{name}" if rel_path else name, depth + 1)
            elif mt == "application/vnd.google-apps.shortcut":
                sc = it.get("shortcutDetails", {})
                t_id = sc.get("targetId")
                t_mime = sc.get("targetMimeType", "")
                if t_id and t_mime == "application/vnd.google-apps.folder":
                    walk(t_id, f"{rel_path}/{name}" if rel_path else name, depth + 1)
                elif t_id and name.lower().endswith(BOOK_EXTS):
                    results.append({
                        "source_id": t_id,
                        "name": name,
                        "size": int(it.get("size") or 0),
                        "mimeType": t_mime or "application/pdf",
                        "folder_path": rel_path,
                        "source_label": label,
                    })
            else:
                if name.lower().endswith(BOOK_EXTS) and name.lower() != "readme.md":
                    results.append({
                        "source_id": iid,
                        "name": name,
                        "size": int(it.get("size") or 0),
                        "mimeType": mt or "application/pdf",
                        "folder_path": rel_path,
                        "source_label": label,
                    })

    walk(root_fid, "", 0)
    print(f"  Scanned {label} ({root_fid}) -> {len(results)} book files", flush=True)
    return results


def fetch_github_tree(repo: str, branch: str) -> list[str]:
    url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    return [x["path"] for x in data.get("tree", []) if x.get("type") == "blob" and x["path"].lower().endswith((".pdf", ".epub"))]


def download_file(url: str, dest: Path) -> bool:
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    continue
                data = resp.read()
                if len(data) < 1024:
                    return False
                dest.write_bytes(data)
                return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    base_books = json.loads((REPO_DIR / "books.json").read_text(encoding="utf-8"))
    extra_books = json.loads(EXTRA_FILE.read_text(encoding="utf-8")) if EXTRA_FILE.exists() else []

    seen_source_ids = {b.get("source_id") for b in base_books + extra_books if b.get("source_id")}
    seen_file_ids = {b["file_id"] for b in base_books + extra_books}
    seen_norm_names = {norm_name(b["name"]) for b in base_books + extra_books}

    def save_extra():
        with LOCK:
            EXTRA_FILE.write_text(json.dumps(extra_books, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # PART A: Copy remaining Hadith JSON files from 1ABszP5MlIEu9hQSiK_6odBtN_fF9TFAF
    # ------------------------------------------------------------------
    print("\n=== PART A: Copying Hadith JSON collections ===", flush=True)
    hadith_leaf = "01_Religion_ধর্ম/Islam_ইসলাম/Hadith_হাদিস"
    hadith_folder_id = state["folders"][hadith_leaf]
    hadith_items = gdrive_ls("1ABszP5MlIEu9hQSiK_6odBtN_fF9TFAF")
    for it in hadith_items:
        sid = it["id"]
        name = it["name"]
        if not name.endswith(".json") or sid in seen_source_ids:
            continue
        new_id = gdrive_cp(sid, name, hadith_folder_id)
        if new_id:
            seen_source_ids.add(sid)
            seen_norm_names.add(norm_name(name))
            extra_books.append(
                build_rec(
                    sid,
                    new_id,
                    name,
                    int(it.get("size") or 0),
                    it.get("mimeType") or "application/json",
                    hadith_leaf,
                    "Hadith Compilers (হাদিস সংকলন)",
                    "Sunnah / Hadith Digital JSON Archive",
                )
            )
            print(f"  + Hadith JSON copied: {name} -> {new_id}", flush=True)
    save_extra()

    # ------------------------------------------------------------------
    # PART B: NCTB All Textbooks (~1,256 Drive PDFs)
    # ------------------------------------------------------------------
    print("\n=== PART B: Collecting & copying all NCTB Textbooks ===", flush=True)
    nctb_items = crawl_nctb_books()
    nctb_todo = []
    for item in nctb_items:
        fid = item["fid"]
        if fid in seen_source_ids:
            continue
        leaf_path = classify_nctb(item["subject"], item["page_title"])
        # Clean class label from page_title
        pt = re.sub(r"শিক্ষাবর্ষের|পাঠ্যপুস্তক|স্তরের|তালিকা", "", item["page_title"]).strip()
        pt = re.sub(r"\s+", " ", pt)
        ver_tag = f" ({item['ver']})" if item["ver"] else ""
        fname = safe_filename(f"NCTB {item['year']} - {item['subject']}{ver_tag} [{pt}].pdf")
        if leaf_path not in state["folders"]:
            leaf_path = "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Academic_Textbooks"
        nctb_todo.append((fid, fname, leaf_path))

    print(f"NCTB files to copy: {len(nctb_todo)}", flush=True)
    if nctb_todo:
        done_cnt = 0
        fail_cnt = 0

        def do_nctb(entry):
            sid, fname, leaf_path = entry
            parent_id = state["folders"][leaf_path]
            new_id = gdrive_cp(sid, fname, parent_id)
            return entry, new_id

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            for fut in concurrent.futures.as_completed([ex.submit(do_nctb, e) for e in nctb_todo]):
                (sid, fname, leaf_path), new_id = fut.result()
                done_cnt += 1
                if new_id:
                    seen_source_ids.add(sid)
                    seen_file_ids.add(new_id)
                    seen_norm_names.add(norm_name(fname))
                    extra_books.append(
                        build_rec(
                            sid,
                            new_id,
                            fname,
                            0,
                            "application/pdf",
                            leaf_path,
                            "NCTB (জাতীয় শিক্ষাক্রম ও পাঠ্যপুস্তক বোর্ড)",
                            "NCTB (National Curriculum and Textbook Board)",
                        )
                    )
                else:
                    fail_cnt += 1
                if done_cnt % 50 == 0:
                    print(f"  NCTB progress: {done_cnt}/{len(nctb_todo)} (copied: {done_cnt - fail_cnt}, skipped/restricted: {fail_cnt})", flush=True)
                    save_extra()
        save_extra()
        print(f"  NCTB complete! Copied {done_cnt - fail_cnt}, skipped {fail_cnt}.", flush=True)

    # ------------------------------------------------------------------
    # PART C: Scan & copy accessible Shared & Public BD Drive Book Folders
    # ------------------------------------------------------------------
    print("\n=== PART C: Scanning Shared & Public BD Drive Book Folders ===", flush=True)
    public_files = []
    for folder_id, label in SHARED_AND_PUBLIC_DRIVE_FOLDERS:
        public_files.extend(scan_drive_folder_recursive(folder_id, label))

    pub_todo = []
    for pf in public_files:
        sid = pf["source_id"]
        nname = norm_name(pf["name"])
        if sid in seen_source_ids or nname in seen_norm_names:
            continue
        seen_norm_names.add(nname)
        leaf_path = classify_general_bd_book(pf["name"], pf["folder_path"], pf["source_label"])
        if leaf_path not in state["folders"]:
            leaf_path = "25_Others_and_Unclassified_অন্যান্য/Rare_Books"
        pub_todo.append((pf, leaf_path))

    print(f"Unique public Drive books to copy: {len(pub_todo)}", flush=True)
    if pub_todo:
        done_cnt = 0

        def do_pub(entry):
            pf, leaf_path = entry
            parent_id = state["folders"][leaf_path]
            new_id = gdrive_cp(pf["source_id"], pf["name"], parent_id)
            return pf, leaf_path, new_id

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            for fut in concurrent.futures.as_completed([ex.submit(do_pub, e) for e in pub_todo]):
                pf, leaf_path, new_id = fut.result()
                done_cnt += 1
                if new_id:
                    seen_source_ids.add(pf["source_id"])
                    seen_file_ids.add(new_id)
                    author = extract_author_clean(pf["name"], pf["folder_path"])
                    extra_books.append(
                        build_rec(
                            pf["source_id"],
                            new_id,
                            pf["name"],
                            pf["size"],
                            pf["mimeType"],
                            leaf_path,
                            author,
                            pf["source_label"],
                        )
                    )
                if done_cnt % 50 == 0:
                    print(f"  Public Drive progress: {done_cnt}/{len(pub_todo)}", flush=True)
                    save_extra()
        save_extra()

    # ------------------------------------------------------------------
    # PART D: Download & Upload GitHub Bangla eBooks + Archive.org BD/Subject Books
    # ------------------------------------------------------------------
    print("\n=== PART D: Downloading & Uploading GitHub Bangla eBooks ===", flush=True)
    gh_specs = [
        ("SM-Collection/Bangla-eBook", "master", "SM-Collection Bangla eBook Archive"),
        ("eedeidk/bongboi", "main", "BongBoi Open Bengali EPUB Archive"),
    ]
    gh_items = []
    for repo, branch, pub_name in gh_specs:
        try:
            paths = fetch_github_tree(repo, branch)
            print(f"  {repo}: {len(paths)} book files", flush=True)
            for p in paths:
                fname = Path(p).name
                sid = f"gh:{repo}/{p}"
                nname = norm_name(fname)
                if sid in seen_source_ids or nname in seen_norm_names:
                    continue
                seen_norm_names.add(nname)
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/" + urllib.parse.quote(p)
                parent_folder = Path(p).parts[0] if len(Path(p).parts) > 1 else ""
                gh_items.append((sid, fname, url, parent_folder, pub_name))
        except Exception as e:
            print(f"  [GH warn] {repo}: {e}", flush=True)

    print(f"GitHub Bangla books to download & upload: {len(gh_items)}", flush=True)
    if gh_items:
        done_cnt = 0

        def do_gh(entry):
            sid, fname, url, parent_folder, pub_name = entry
            leaf_path = classify_general_bd_book(fname, parent_folder, pub_name)
            if leaf_path not in state["folders"]:
                leaf_path = "02_Literature_সাহিত্য/Collected_Works_রচনাবলী"
            local_p = TMP_DIR / safe_filename(fname, os.path.splitext(fname)[1] or ".pdf")
            if not download_file(url, local_p):
                return entry, None, leaf_path, 0
            fsize = local_p.stat().st_size
            parent_id = state["folders"][leaf_path]
            new_id = gdrive_upload(local_p, parent_id)
            try:
                local_p.unlink(missing_ok=True)
            except Exception:
                pass
            return entry, new_id, leaf_path, fsize

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            for fut in concurrent.futures.as_completed([ex.submit(do_gh, e) for e in gh_items]):
                (sid, fname, url, parent_folder, pub_name), new_id, leaf_path, fsize = fut.result()
                done_cnt += 1
                if new_id:
                    seen_source_ids.add(sid)
                    seen_file_ids.add(new_id)
                    author = parent_folder if (parent_folder and parent_folder != "অজ্ঞাত") else extract_author_clean(fname)
                    mime = "application/epub+zip" if fname.lower().endswith(".epub") else "application/pdf"
                    extra_books.append(
                        build_rec(sid, new_id, fname, fsize, mime, leaf_path, author, pub_name)
                    )
                if done_cnt % 25 == 0:
                    print(f"  GitHub upload progress: {done_cnt}/{len(gh_items)}", flush=True)
                    save_extra()
        save_extra()

    # ------------------------------------------------------------------
    # PART E: Internet Archive BD Bengali Books + Fill All Sparse Categories
    # ------------------------------------------------------------------
    print("\n=== PART E: Fetching Internet Archive Bangla & Sparse-Category PDFs ===", flush=True)
    for tag, query, forced_leaf, max_rows in ARCHIVE_CATEGORY_QUERIES:
        try:
            search_url = (
                "https://archive.org/advancedsearch.php?q="
                + urllib.parse.quote(query + " AND NOT collection:inlibrary")
                + f"&fl[]=identifier,title,creator,subject&rows={max_rows * 2}&page=1&output=json"
            )
            req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
            docs = data.get("response", {}).get("docs", [])
            print(f"  Archive [{tag}]: {len(docs)} candidate records", flush=True)
        except Exception as e:
            print(f"  [Archive warn] {tag}: {e}", flush=True)
            continue

        added_here = 0
        for doc in docs:
            if added_here >= max_rows:
                break
            ident = doc.get("identifier")
            if not ident:
                continue
            sid = f"ia:{ident}"
            if sid in seen_source_ids:
                continue
            title_raw = doc.get("title") or ident
            if isinstance(title_raw, list):
                title_raw = title_raw[0]
            creator_raw = doc.get("creator") or "Various / Internet Archive"
            if isinstance(creator_raw, list):
                creator_raw = ", ".join(str(x) for x in creator_raw[:2])

            fname = safe_filename(f"{title_raw}.pdf")
            if norm_name(fname) in seen_norm_names:
                continue

            # Find PDF filename from archive metadata
            try:
                meta_req = urllib.request.Request(f"https://archive.org/metadata/{ident}/files", headers={"User-Agent": "Mozilla/5.0"})
                meta = json.loads(urllib.request.urlopen(meta_req, timeout=15).read().decode("utf-8"))
                pdfs = [
                    f for f in meta.get("result", [])
                    if f.get("name", "").lower().endswith(".pdf") and 50_000 <= int(f.get("size") or 0) <= 30_000_000
                ]
                if not pdfs:
                    continue
                # Prefer text-based / smallest clean PDF
                pdfs.sort(key=lambda f: int(f.get("size") or 0))
                pdf_meta = pdfs[0]
                dl_url = f"https://archive.org/download/{ident}/" + urllib.parse.quote(pdf_meta["name"])
            except Exception:
                continue

            local_p = TMP_DIR / safe_filename(f"{ident}.pdf")
            if not download_file(dl_url, local_p):
                continue

            leaf_path = forced_leaf or classify_general_bd_book(f"{title_raw} {creator_raw}", "", "Internet Archive")
            if leaf_path not in state["folders"]:
                leaf_path = "25_Others_and_Unclassified_অন্যান্য/Rare_Books"

            fsize = local_p.stat().st_size
            new_id = gdrive_upload(local_p, state["folders"][leaf_path])
            # Rename uploaded file on Drive if needed? Easier: upload with desired filename!
            try:
                local_p.unlink(missing_ok=True)
            except Exception:
                pass
            if new_id:
                # Rename in Drive to readable Bangla/English title
                subprocess.run([GDRIVE, "mutate", "rename", new_id, fname], capture_output=True, text=True, encoding="utf-8")
                seen_source_ids.add(sid)
                seen_file_ids.add(new_id)
                seen_norm_names.add(norm_name(fname))
                extra_books.append(
                    build_rec(
                        sid,
                        new_id,
                        fname,
                        fsize,
                        "application/pdf",
                        leaf_path,
                        str(creator_raw)[:80],
                        "Internet Archive Open Library (archive.org)",
                    )
                )
                added_here += 1
                print(f"    + [{tag}] ({added_here}/{max_rows}) {fname[:60]}", flush=True)
                if added_here % 10 == 0:
                    save_extra()
        save_extra()

    # ------------------------------------------------------------------
    # PART F: Backfill exact Google Drive file sizes for size==0 entries
    # ------------------------------------------------------------------
    print("\n=== PART F: Syncing exact sizes/mimeTypes from modified Drive folders ===", flush=True)
    need_size_fids = {b["file_id"] for b in extra_books if not b.get("size")}
    if need_size_fids:
        touched_leaves = sorted({b["leaf_path"] for b in extra_books if not b.get("size")})
        id_to_meta = {}
        for lp in touched_leaves:
            folder_id = state["folders"].get(lp)
            if not folder_id:
                continue
            for it in gdrive_ls(folder_id):
                id_to_meta[it["id"]] = it
        updated = 0
        for b in extra_books:
            if not b.get("size") and b["file_id"] in id_to_meta:
                it = id_to_meta[b["file_id"]]
                b["size"] = int(it.get("size") or 0)
                if it.get("mimeType"):
                    b["mimeType"] = it["mimeType"]
                updated += 1
        print(f"Updated sizes for {updated} newly added books.", flush=True)
        save_extra()

    all_now = base_books + extra_books
    tc_counts = Counter(b["top_category"] for b in all_now)
    print(f"\nDONE! Total catalog size now: {len(all_now)} books across {len(tc_counts)}/25 top categories.", flush=True)
    for tc in b25.TAXONOMY:
        print(f"  {tc}: {tc_counts[tc]}", flush=True)


if __name__ == "__main__":
    main()
