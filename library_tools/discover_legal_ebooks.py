"""READ-ONLY Legal eBook Discovery across verified public-domain / open-license sources.

Sources:
  1. Bengali Wikisource (bn.wikisource.org + ws-export.wmcloud.org EPUB export)
  2. Project Gutenberg (gutendex.com Bengali + top English classics EPUB)
  3. NCTB Official Government Textbooks (nctbbook.bd -> drive.egovcloud.gov.bd PDF)
  4. Open-Access Academic & Historical Collections:
       - OpenStax (openstax.org CMS API -> CC-licensed college/science PDFs)
       - Internet Archive (strictly filtered to licenseurl publicdomain / creativecommons)

Strictly READ-ONLY: discovers candidates, verifies rights/license metadata, and
checks against existing Drive books (including pre-romanization Bangla titles
recovered from git history) without downloading book files or modifying Drive.
"""
from __future__ import annotations

import argparse
import collections
import csv
import html
import json
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "BangladeshBiggestEBookLibraryBot/1.0 (+https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library)"

WIKISOURCE_AUTHORS: list[tuple[str, str]] = [
    ("রবীন্দ্রনাথ ঠাকুর", "রবীন্দ্রনাথ ঠাকুর"),
    ("বঙ্কিমচন্দ্র চট্টোপাধ্যায়", "বঙ্কিমচন্দ্র চট্টোপাধ্যায়"),
    ("শরৎচন্দ্র চট্টোপাধ্যায়", "শরৎচন্দ্র চট্টোপাধ্যায়"),
    ("মাইকেল মধুসূদন দত্ত", "মাইকেল মধুসূদন দত্ত"),
    ("বিভূতিভূষণ বন্দ্যোপাধ্যায়", "বিভূতিভূষণ বন্দ্যোপাধ্যায়"),
    ("কাজী নজরুল ইসলাম", "কাজী নজরুল ইসলাম"),
    ("বেগম রোকেয়া", "বেগম রোকেয়া সাখাওয়াত হোসেন"),
    ("ঈশ্বরচন্দ্র বিদ্যাসাগর", "ঈশ্বরচন্দ্র বিদ্যাসাগর"),
    ("সুকুমার রায়", "সুকুমার রায়"),
    ("উপেন্দ্রকিশোর রায়চৌধুরী", "উপেন্দ্রকিশোর রায়চৌধুরী"),
    ("অবনীন্দ্রনাথ ঠাকুর", "অবনীন্দ্রনাথ ঠাকুর"),
    ("দ্বিজেন্দ্রলাল রায়", "দ্বিজেন্দ্রলাল রায়"),
    ("জীবনানন্দ দাশ", "জীবনানন্দ দাশ"),
    ("মীর মশাররফ হোসেন", "মীর মশাররফ হোসেন"),
    ("প্রমথ চৌধুরী", "প্রমথ চৌধুরী"),
]


def http_get(url: str, timeout: int = 30, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def norm_key(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").lower()
    s = re.sub(r"\.[a-z0-9]{1,5}$", "", s)
    s = re.sub(r"[\(\)\[\]\{\}—–\-_:,;!?।\"'‘’“”\.]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_existing_title_index(audit_csv: Path, repo_dir: Path) -> set[str]:
    """Build normalized title/filename keys for books already present in Drive."""
    keys: set[str] = set()
    drive_ids: set[str] = set()
    if audit_csv.exists():
        with open(audit_csv, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if r.get("kind") == "ebook":
                    drive_ids.add(r["id"])
                    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", r["name"])
                    for part in [stem, re.split(r"\s+[—\-]\s+|\s*\(", stem)[0]]:
                        nk = norm_key(part)
                        if len(nk) >= 3:
                            keys.add(nk)

    # Also pull pre-English-rename Bangla titles from git history and local meta
    def add_records(items):
        for it in items:
            ids = [it.get("file_id"), it.get("pdf_file_id"), it.get("epub_file_id")]
            for f in it.get("files") or []:
                ids.append(f.get("id"))
            if drive_ids and not any(i in drive_ids for i in ids if i):
                continue
            for field in ("title", "name", "original_title"):
                val = it.get(field) or ""
                for part in [val, re.split(r"\s+[—\-]\s+|\s*\(", val)[0]]:
                    nk = norm_key(part)
                    if len(nk) >= 3:
                        keys.add(nk)

    eb_meta = repo_dir / "data" / "ebanglalibrary_meta.json"
    if eb_meta.exists():
        for m in json.load(open(eb_meta, encoding="utf-8")):
            t = (m.get("title") or "").split(" - ")[0].strip()
            nk = norm_key(t)
            if len(nk) >= 3:
                keys.add(nk)

    try:
        raw = subprocess.check_output(
            ["git", "-C", str(repo_dir), "show", "e7b362e1f~1:data/merged_books.json"],
            stderr=subprocess.DEVNULL,
        )
        add_records(json.loads(raw))
    except Exception:
        pass
    return keys


def is_present(title: str, existing: set[str]) -> bool:
    nk = norm_key(title)
    if not nk:
        return False
    if nk in existing:
        return True
    base = norm_key(re.sub(r"\(.*?\)|\[.*?\]", "", title))
    return bool(base and len(base) >= 4 and base in existing)


def discover_wikisource(existing: set[str]) -> list[dict]:
    out: list[dict] = []
    seen_pages: set[str] = set()
    skip_re = re.compile(r"^(?:প্রধান পাতা|সূচীপত্র|মুখবন্ধ|অধ্যায়|পর্ব|সংখ্যা|১|২|৩|৪|৫|৬|৭|৮|৯|০|/)|/")
    for ws_author, canonical_author in WIKISOURCE_AUTHORS:
        try:
            url = (
                "https://bn.wikisource.org/w/api.php?action=parse&page="
                + urllib.parse.quote(f"লেখক:{ws_author}")
                + "&prop=links&format=json"
            )
            data = json.loads(http_get(url, 25))
            links = data.get("parse", {}).get("links", [])
        except Exception as e:
            print(f"[wikisource] {ws_author} error: {e}", file=sys.stderr)
            continue

        # Also filter out likely individual short poems if huge; keep book/collection pages
        page_titles = [
            l["*"] for l in links
            if l.get("ns") == 0 and "exists" in l and not skip_re.search(l["*"])
        ]
        # Batch query page lengths & categories (50 per request) to skip tiny stubs (<800 bytes) or redirect pages
        for i in range(0, len(page_titles), 40):
            batch = page_titles[i:i + 40]
            qurl = (
                "https://bn.wikisource.org/w/api.php?action=query&prop=info|categories&cllimit=20&redirects=1&titles="
                + urllib.parse.quote("|".join(batch))
                + "&format=json"
            )
            try:
                qdata = json.loads(http_get(qurl, 25))
            except Exception:
                continue
            pages = qdata.get("query", {}).get("pages", {})
            for p in pages.values():
                if "missing" in p:
                    continue
                ptitle = p.get("title", "")
                if not ptitle or ptitle in seen_pages or "/" in ptitle:
                    continue
                if p.get("length", 0) < 400:
                    continue
                cats = " ".join(c.get("title", "") for c in p.get("categories", []))
                # Skip single-poem stubs only if explicitly categorized as single poem AND small
                clean_title = re.sub(r"\s*\([^)]*" + re.escape(ws_author.split()[0]) + r"[^)]*\)\s*$", "", ptitle).strip()
                clean_title = re.sub(r"\s*\([১-৯০0-9]{4}\)\s*$", "", clean_title).strip() or ptitle
                if any(k in cats for k in ("কবিতা",)) and "কাব্যগ্রন্থ" not in cats and p.get("length", 0) < 3000:
                    continue
                seen_pages.add(ptitle)
                subcat = "অন্যান্য"
                if any(k in cats for k in ("উপন্যাস",)):
                    subcat = "উপন্যাস"
                elif any(k in cats for k in ("ছোটগল্প", "গল্পগ্রন্থ", "গল্প")):
                    subcat = "গল্প ও ছোটগল্প"
                elif any(k in cats for k in ("কাব্যগ্রন্থ", "কবিতা", "সনেট")):
                    subcat = "কবিতা"
                elif any(k in cats for k in ("নাটক", "প্রহসন")):
                    subcat = "নাটক"
                elif any(k in cats for k in ("প্রবন্ধ", "রচনা")):
                    subcat = "প্রবন্ধ"
                elif any(k in cats for k in ("শিশু", "কিশোর")):
                    subcat = "শিশু-কিশোর সাহিত্য"
                elif any(k in cats for k in ("ভ্রমণ",)):
                    subcat = "ভ্রমণ"
                elif any(k in cats for k in ("জীবনী", "আত্মজীবনী", "স্মৃতিকথা")):
                    subcat = "জীবনী ও আত্মজীবনী"

                dl_url = "https://ws-export.wmcloud.org/?lang=bn&format=epub&page=" + urllib.parse.quote(ptitle)
                src_url = "https://bn.wikisource.org/wiki/" + urllib.parse.quote(ptitle.replace(" ", "_"))
                out.append({
                    "title": clean_title,
                    "author": canonical_author,
                    "language": "Bangla",
                    "category": "01_Bangla_Books",
                    "subcategory": subcat,
                    "series": "",
                    "format": "EPUB",
                    "source_name": "Bengali Wikisource",
                    "source_url": src_url,
                    "download_url": dl_url,
                    "license": "Public Domain (Work) / CC-BY-SA-4.0 (Wikisource transcription)",
                    "copyright_status": "Public Domain",
                    "already_in_library": is_present(clean_title, existing),
                })
    return out


def discover_gutenberg(existing: set[str], en_limit: int = 160) -> list[dict]:
    out: list[dict] = []
    # 1. Bengali Gutenberg (may be sparse or slow)
    for lang, max_items in (("bn", 50), ("en", en_limit)):
        url = f"https://gutendex.com/books?languages={lang}&sort=popular"
        fetched = 0
        while url and fetched < max_items:
            try:
                data = json.loads(http_get(url, timeout=45, retries=3))
            except Exception as e:
                print(f"[gutenberg {lang}] error: {e}", file=sys.stderr)
                break
            for b in data.get("results", []):
                if fetched >= max_items:
                    break
                formats = b.get("formats") or {}
                epub_url = formats.get("application/epub+zip") or formats.get("application/epub3+zip")
                if not epub_url:
                    continue
                if b.get("copyright") is True:
                    continue
                authors = b.get("authors") or []
                raw_auth = authors[0]["name"] if authors else "Unknown"
                if "," in raw_auth:
                    parts = [p.strip() for p in raw_auth.split(",", 1)]
                    author = f"{parts[1]} {parts[0]}".strip()
                else:
                    author = raw_auth
                title = (b.get("title") or "").split(";")[0].split("\r")[0].split("\n")[0].strip()
                subjects = " ".join(b.get("subjects") or []).lower()
                bookshelves = " ".join(b.get("bookshelves") or []).lower()
                blob = f"{subjects} {bookshelves}"
                if lang == "bn":
                    cat, sub, lang_label = "01_Bangla_Books", "অন্যান্য", "Bangla"
                else:
                    lang_label = "English"
                    cat = "02_English_Books"
                    if "philosophy" in blob or "ethics" in blob:
                        sub = "Philosophy"
                    elif "history" in blob:
                        sub = "History"
                    elif "biography" in blob or "autobiography" in blob:
                        sub = "Biography"
                    elif "science" in blob or "physics" in blob or "biology" in blob or "mathematics" in blob:
                        sub = "Science"
                    elif "fiction" in blob or "literature" in blob or "novel" in blob or "poetry" in blob or "drama" in blob:
                        sub = "Fiction"
                    else:
                        sub = "Non_Fiction"
                out.append({
                    "title": title,
                    "author": author,
                    "language": lang_label,
                    "category": cat,
                    "subcategory": sub,
                    "series": "",
                    "format": "EPUB",
                    "source_name": "Project Gutenberg",
                    "source_url": f"https://www.gutenberg.org/ebooks/{b['id']}",
                    "download_url": epub_url,
                    "license": "Public Domain (Project Gutenberg)",
                    "copyright_status": "Public Domain",
                    "already_in_library": is_present(title, existing),
                })
                fetched += 1
            url = data.get("next")
    return out


def discover_nctb(existing_rows: list[dict]) -> list[dict]:
    """Query nctbbook.bd WP REST API for all 2025/2026 NCTB & Madrasa textbook links."""
    out: list[dict] = []
    # Build set of normalized existing NCTB titles + class numbers
    nctb_existing: set[str] = set()
    for r in existing_rows:
        if r.get("kind") == "ebook" and ("NCTB" in r["name"] or r.get("top") == "01_EDUCATION"):
            nctb_existing.add(norm_key(r["name"]))

    posts: list[dict] = []
    for page in range(1, 5):
        try:
            raw = http_get(f"https://nctbbook.bd/wp-json/wp/v2/posts?per_page=100&page={page}", 25)
            batch = json.loads(raw)
            if not batch:
                break
            posts.extend(batch)
            if len(batch) < 100:
                break
        except urllib.error.HTTPError as e:
            if e.code == 400:
                break
            print(f"[nctb] wp api page {page}: {e}", file=sys.stderr)
            break
        except Exception as e:
            print(f"[nctb] wp api page {page}: {e}", file=sys.stderr)
            break

    seen_urls: set[str] = set()
    for post in posts:
        slug = post.get("slug", "")
        post_url = post.get("link", "")
        post_title = html.unescape(re.sub(r"<[^>]+>", "", (post.get("title") or {}).get("rendered", ""))).strip()
        content = (post.get("content") or {}).get("rendered", "")
        # Determine class & track from slug / post title
        is_madrasa = any(k in slug.lower() or k in post_title for k in ("ibteda", "dakhil", "alim", "ইবতেদায়ী", "দাখিল", "আলিম", "মাদ্রাসা"))
        m_cls = re.search(r"class[- ](\d{1,2})", slug, re.I) or re.search(r"Class\s*(\d{1,2})", post_title, re.I)
        cls_num = int(m_cls.group(1)) if m_cls else None
        m_yr = re.search(r"(202[4-7])", slug + " " + post_title)
        year = m_yr.group(1) if m_yr else "2026"

        if is_madrasa:
            subcat = f"Madrasa/Class_{cls_num:02d}" if cls_num else "Madrasa"
        elif cls_num and 1 <= cls_num <= 10:
            subcat = f"School/Class_{cls_num:02d}"
        elif cls_num and cls_num in (11, 12):
            subcat = "HSC_Class_11-12"
        else:
            subcat = "School"

        for rm in re.finditer(r"<tr[^>]*>(.*?)</tr>", content, re.S):
            row_html = rm.group(1)
            if "egovcloud" not in row_html and ".pdf" not in row_html.lower():
                continue
            cols = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S)]
            urls = re.findall(r'href="(https?://[^"]+)"', row_html)
            dl_url = next((u for u in urls if "egovcloud.gov.bd" in u or u.lower().endswith(".pdf")), "")
            if not dl_url or dl_url in seen_urls:
                continue
            seen_urls.add(dl_url)
            subj = cols[1] if len(cols) >= 2 and len(cols[1]) > 2 else (cols[0] if cols else post_title)
            subj = re.sub(r"\s+", " ", subj).strip()
            is_ev = bool(re.search(r"english\s*version|\bEV\b|ইংরেজি\s*ভার্সন", row_html + " " + post_title, re.I)) or bool(re.fullmatch(r"[A-Za-z0-9\s,&\-\(\)\.]+", subj))
            cls_tag = f"Class {cls_num}" if cls_num else ""
            ver_tag = "English Version" if is_ev else "Bangla Version"
            if is_madrasa:
                ver_tag = "Madrasa"
            full_title = f"{subj} ({cls_tag}, {ver_tag}, NCTB {year})".replace("(, ", "(").strip()
            lang = "English" if is_ev else "Bangla"
            # Check if present in existing NCTB set
            nk_subj = norm_key(subj)
            already = any(
                nk_subj in ex and (not cls_num or str(cls_num) in ex or (year in ex))
                for ex in nctb_existing
            ) if nk_subj else False
            out.append({
                "title": full_title,
                "author": "NCTB" if is_ev else "এনসিটিবি",
                "language": lang,
                "category": "03_Education_and_Textbooks",
                "subcategory": subcat,
                "series": f"NCTB Textbooks {year}",
                "format": "PDF",
                "source_name": "NCTB / nctbbook.bd (eGovCloud)",
                "source_url": post_url,
                "download_url": dl_url,
                "license": "Government of Bangladesh Free Educational Distribution (NCTB)",
                "copyright_status": "Official Free Textbook",
                "already_in_library": already,
            })
    return out


def discover_openstax(existing: set[str]) -> list[dict]:
    out: list[dict] = []
    try:
        raw = http_get(
            "https://openstax.org/apps/cms/api/v2/pages/?type=books.Book"
            "&fields=title,slug,book_subjects,authors,license_name,license_url,pdf_url,high_resolution_pdf_url,webview_rex_link&limit=200",
            timeout=30,
        )
        items = json.loads(raw).get("items", [])
    except Exception as e:
        print(f"[openstax] error: {e}", file=sys.stderr)
        return out

    for b in items:
        pdf_url = b.get("pdf_url") or b.get("high_resolution_pdf_url")
        lic_url = b.get("license_url") or ""
        if not pdf_url or "creativecommons.org" not in lic_url:
            continue
        title = (b.get("title") or "").strip()
        authors = [a.get("name", "") for a in (b.get("authors") or []) if isinstance(a, dict) and a.get("name")]
        author = ", ".join(authors[:2]) if authors else "OpenStax"
        subjs = [s.get("subject_name", "") for s in (b.get("book_subjects") or []) if isinstance(s, dict)]
        sub_blob = " ".join(subjs).lower()
        cat = "02_English_Books"
        if "computer" in sub_blob or "programming" in sub_blob:
            sub = "Technology"
        elif any(k in sub_blob for k in ("science", "math", "physics", "chem", "bio", "astronomy", "nursing", "anatomy")):
            sub = "Science"
        elif "history" in sub_blob:
            sub = "History"
        elif "philosophy" in sub_blob:
            sub = "Philosophy"
        else:
            sub = "Non_Fiction"
        lic_name = b.get("license_name") or lic_url
        out.append({
            "title": title,
            "author": author,
            "language": "English",
            "category": cat,
            "subcategory": sub,
            "series": "OpenStax Open Textbooks",
            "format": "PDF",
            "source_name": "OpenStax (Rice University)",
            "source_url": b.get("webview_rex_link") or f"https://openstax.org/details/books/{b.get('meta', {}).get('slug', '')}",
            "download_url": pdf_url,
            "license": f"{lic_name} ({lic_url})",
            "copyright_status": "Open Access (Creative Commons)",
            "already_in_library": is_present(title, existing),
        })
    return out


def discover_archive(existing: set[str], rows_per_query: int = 80) -> list[dict]:
    out: list[dict] = []
    seen_ids: set[str] = set()
    queries = [
        ("Bangla Historical PD", "mediatype:texts AND language:ben AND (licenseurl:*publicdomain* OR licenseurl:*creativecommons*)", "Bangla", "01_Bangla_Books", "অন্যান্য"),
        ("Open CS/Math Textbooks", "mediatype:texts AND language:eng AND (subject:\"computer science\" OR subject:\"python\" OR subject:\"algorithms\") AND (licenseurl:*creativecommons* OR licenseurl:*publicdomain*)", "English", "02_English_Books", "Technology"),
    ]
    for label, q, lang, cat, sub in queries:
        url = (
            "https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q)
            + f"&fl[]=identifier,title,creator,year,licenseurl,rights&sort[]=downloads+desc&rows={rows_per_query}&page=1&output=json"
        )
        try:
            docs = json.loads(http_get(url, 30)).get("response", {}).get("docs", [])
        except Exception as e:
            print(f"[archive {label}] error: {e}", file=sys.stderr)
            continue
        for doc in docs:
            ident = doc.get("identifier", "")
            lic = doc.get("licenseurl") or doc.get("rights") or ""
            if not ident or ident in seen_ids or not lic:
                continue
            if not any(k in lic.lower() for k in ("publicdomain", "creativecommons", "zero/1.0")):
                continue
            seen_ids.add(ident)
            title = doc.get("title")
            if isinstance(title, list):
                title = title[0]
            creator = doc.get("creator")
            if isinstance(creator, list):
                creator = creator[0]
            title = str(title or ident).strip()
            author = str(creator or "Unknown").strip()
            if not title or len(title) < 2:
                continue
            c_stat = "Public Domain" if "publicdomain" in lic.lower() or "zero" in lic.lower() else "Open Access (Creative Commons)"
            out.append({
                "title": title[:160],
                "author": author[:100],
                "language": lang,
                "category": cat,
                "subcategory": sub,
                "series": "",
                "format": "PDF",
                "source_name": f"Internet Archive ({label})",
                "source_url": f"https://archive.org/details/{ident}",
                "download_url": f"https://archive.org/download/{ident}/{ident}.pdf",
                "license": lic,
                "copyright_status": c_stat,
                "already_in_library": is_present(title, existing),
            })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-csv", required=True)
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    audit_csv = Path(args.audit_csv)
    repo_dir = Path(args.repo_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    existing_rows = list(csv.DictReader(open(audit_csv, encoding="utf-8-sig"))) if audit_csv.exists() else []
    existing = load_existing_title_index(audit_csv, repo_dir)
    print(f"Existing title keys loaded: {len(existing)}", flush=True)

    all_cands: list[dict] = []
    for name, fn in [
        ("wikisource", lambda: discover_wikisource(existing)),
        ("gutenberg", lambda: discover_gutenberg(existing, en_limit=160)),
        ("nctb", lambda: discover_nctb(existing_rows)),
        ("openstax", lambda: discover_openstax(existing)),
        ("archive", lambda: discover_archive(existing, rows_per_query=80)),
    ]:
        res = fn()
        new_cnt = sum(1 for r in res if not r["already_in_library"])
        print(f"  {name:12s}: total={len(res):4d}  new_not_in_library={new_cnt:4d}", flush=True)
        all_cands.extend(res)

    # Deduplicate candidates by normalized (title, author)
    deduped: list[dict] = []
    seen_ta: set[tuple[str, str]] = set()
    for c in all_cands:
        key = (norm_key(c["title"]), norm_key(c["author"]))
        if key in seen_ta:
            continue
        seen_ta.add(key)
        deduped.append(c)

    fields = [
        "title", "author", "language", "category", "subcategory", "series",
        "format", "source_name", "source_url", "download_url", "license",
        "copyright_status", "already_in_library",
    ]
    with open(out_dir / "legal_discovery_candidates.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(deduped)

    new_only = [c for c in deduped if not c["already_in_library"]]
    summary = {
        "total_discovered": len(deduped),
        "already_in_library": len(deduped) - len(new_only),
        "new_candidates_ready_for_approval": len(new_only),
        "by_source_total": dict(collections.Counter(c["source_name"] for c in deduped)),
        "by_source_new": dict(collections.Counter(c["source_name"] for c in new_only)),
        "by_language_new": dict(collections.Counter(c["language"] for c in new_only)),
        "by_category_new": dict(collections.Counter(c["category"] for c in new_only)),
        "by_copyright_new": dict(collections.Counter(c["copyright_status"] for c in new_only)),
    }
    (out_dir / "legal_discovery_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("SUMMARY:", json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
