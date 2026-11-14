import concurrent.futures
import html as html_lib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
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

REQ_HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def clean_tax_segment(raw: str) -> str:
    if not re.search(r"[A-Za-z]", raw):
        return raw
    s = re.sub(r"^\d+_", "", raw)
    s2 = re.sub(r"[\u0980-\u09FF]+", "", s)
    s2 = re.sub(r"_+", " ", s2).strip()
    return re.sub(r"\s+", " ", s2) or raw


def clean_tax_path(raw_path: str) -> str:
    return "/".join(clean_tax_segment(seg) for seg in raw_path.split("/"))


def fetch_text(url: str, timeout: int = 20) -> str:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=REQ_HDR)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception:
            if attempt == 2:
                return ""
            time.sleep(1.0 * (attempt + 1))
    return ""


def sanitize_filename(name: str) -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", name)
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:120].strip() or "book"


def parse_size_bytes(label: str) -> int:
    bn_digits = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    s = label.translate(bn_digits).upper()
    m = re.search(r"([\d.]+)\s*(KB|MB|GB|B)", s)
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2)
    mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}.get(unit, 1)
    return int(val * mult)


def parse_bde_book_page(url: str) -> dict | None:
    body = fetch_text(url)
    if not body:
        return None

    title_m = re.search(r"<title>(.*?)</title>", body, re.S)
    raw_title = html_lib.unescape(title_m.group(1).strip()) if title_m else ""
    parts = [p.strip() for p in raw_title.split("·")]
    title = parts[0] if parts else url.rstrip("/").split("/")[-1]
    author = parts[1] if len(parts) >= 3 else ""

    og_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', body)
    if not og_m:
        og_m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', body)
    cover_url = og_m.group(1) if og_m else ""

    thumb_m = re.search(r'<img[^>]+class="[^"]*bkp-cover__img[^"]*"[^>]+src=["\']([^"\']+)["\']', body)
    thumb_url = thumb_m.group(1) if thumb_m else cover_url
    if thumb_url.startswith("/"):
        thumb_url = "https://bdebooks.com" + thumb_url

    # Extract download buttons (PDF, EPUB)
    downloads = []
    for block in re.findall(r'<li class="bk-dl__row">(.*?)</li>', body, re.S):
        fmt_m = re.search(r'bkp-dl__fmt[^>]*>(.*?)</span>', block, re.S)
        sz_m = re.search(r'bk-dl__size[^>]*>(.*?)</span>', block, re.S)
        val_m = re.search(r'value=["\'](download\.\d+)["\']', block)
        if val_m:
            fmt = re.sub(r"<[^>]+>", "", fmt_m.group(1)).strip().upper() if fmt_m else "PDF"
            sz_lbl = re.sub(r"<[^>]+>", "", sz_m.group(1)).strip() if sz_m else ""
            downloads.append({
                "token": val_m.group(1),
                "format": fmt,
                "size_label": sz_lbl,
                "size_bytes": parse_size_bytes(sz_lbl),
            })

    # Fallback if <li class="bk-dl__row"> didn't match
    if not downloads:
        for tok in dict.fromkeys(re.findall(r'value=["\'](download\.\d+)["\']', body)):
            downloads.append({"token": tok, "format": "PDF", "size_label": "", "size_bytes": 0})

    # Subject / breadcrumb tags
    subjects = [
        html_lib.unescape(re.sub(r"<[^>]+>", "", s).strip())
        for s in re.findall(r'href=["\']/bn/(?:subjects|tags|genre)/[^"\']+["\'][^>]*>(.*?)</a>', body, re.S)
    ]

    return {
        "url": url,
        "slug": url.rstrip("/").split("/")[-1],
        "title": title,
        "author": author,
        "subjects": [s for s in subjects if s],
        "cover_url": cover_url,
        "thumbnail_url": thumb_url,
        "downloads": downloads,
    }


def download_bde_file(book_url: str, dl_token: str, ext: str, tmp_dir: Path, fname_base: str) -> Path | None:
    opener = urllib.request.build_opener(NoRedirect)
    post_data = urllib.parse.urlencode({"go": dl_token}).encode("utf-8")
    req = urllib.request.Request(
        book_url,
        data=post_data,
        headers={**REQ_HDR, "Referer": book_url, "Origin": "https://bdebooks.com"},
    )
    signed_url = ""
    try:
        opener.open(req, timeout=20)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            signed_url = urllib.parse.urljoin(book_url, e.headers["Location"])
        elif e.code == 429:
            time.sleep(62)
            return download_bde_file(book_url, dl_token, ext, tmp_dir, fname_base)
    except Exception:
        return None

    if not signed_url or "/bndl/" not in signed_url:
        return None

    out_path = tmp_dir / f"{fname_base}{ext}"
    try:
        dl_req = urllib.request.Request(signed_url, headers={**REQ_HDR, "Referer": book_url})
        with urllib.request.urlopen(dl_req, timeout=60) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "text/html" in ctype:
                return None
            data = resp.read()
        if len(data) < 4096:
            return None
        out_path.write_bytes(data)
        return out_path
    except Exception:
        return None


def parse_gdrive_id(out: str) -> str | None:
    txt = out.strip()
    if txt.startswith("{"):
        try:
            obj = json.loads(txt)
            if obj.get("id"):
                return obj["id"]
        except Exception:
            pass
    m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", txt)
    return m.group(1) if m else None


def gd_upload(local_path: Path, parent_id: str) -> str | None:
    for attempt in range(4):
        try:
            res = subprocess.run(
                GDRIVE_BASE + ["mutate", "upload", str(local_path), "--parent", parent_id],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
            )
            if res.returncode == 0:
                fid = parse_gdrive_id(res.stdout)
                if fid:
                    return fid
        except Exception:
            pass
        time.sleep(1.0 * (attempt + 1))
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(REPO_DIR / "scripts"))
    import build_25cat_library as b25  # noqa: E402

    clean_folders = json.loads((DATA_DIR / "clean_folders.json").read_text(encoding="utf-8"))
    covers_bde_id = clean_folders["covers/BDeBooks"]

    cache_file = DATA_DIR / "bdebooks_catalog.json"
    if cache_file.exists():
        catalog = json.loads(cache_file.read_text(encoding="utf-8"))
        print(f"Loaded {len(catalog)} cached BDeBooks records.", flush=True)
    else:
        print("Step 1: Fetching BDeBooks sitemap_index.xml & book-sitemap1..13...", flush=True)
        idx_xml = fetch_text("https://bdebooks.com/bn/sitemap_index.xml")
        sitemaps = re.findall(r"<loc>(https://bdebooks\.com/bn/book-sitemap[^<]+)</loc>", idx_xml)
        if not sitemaps:
            sitemaps = [f"https://bdebooks.com/bn/book-sitemap{i}.xml" for i in range(1, 14)]
        book_urls = []
        for sm in sitemaps:
            xml = fetch_text(sm)
            locs = [u for u in re.findall(r"<loc>(.*?)</loc>", xml) if "/books/" in u]
            book_urls.extend(locs)
            print(f"  {sm} -> {len(locs)} book URLs", flush=True)
        book_urls = list(dict.fromkeys(book_urls))
        print(f"Total BDeBooks URLs: {len(book_urls)}", flush=True)

        catalog = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=28) as ex:
            futs = {ex.submit(parse_bde_book_page, u): u for u in book_urls}
            done = 0
            for f in concurrent.futures.as_completed(futs):
                rec = f.result()
                if rec:
                    catalog.append(rec)
                done += 1
                if done % 500 == 0:
                    print(f"  Scraped {done}/{len(book_urls)} BDeBooks pages", flush=True)
        cache_file.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(catalog)} records to bdebooks_catalog.json", flush=True)

    # Track covers for ALL BDeBooks in book_covers.json immediately
    covers_file = DATA_DIR / "book_covers.json"
    book_covers = json.loads(covers_file.read_text(encoding="utf-8")) if covers_file.exists() else {}

    extra_file = DATA_DIR / "extra_books.json"
    extra_books = json.loads(extra_file.read_text(encoding="utf-8")) if extra_file.exists() else []
    books_json = REPO_DIR / "books.json"
    existing_all = json.loads(books_json.read_text(encoding="utf-8")) if books_json.exists() else []
    known_norms = {
        re.sub(r"[^a-z0-9\u0980-\u09ff]+", "", Path(b["name"]).stem.lower())
        for b in existing_all + extra_books
    }

    bde_state_file = DATA_DIR / "bde_ingest_state.json"
    bde_state = (
        json.loads(bde_state_file.read_text(encoding="utf-8"))
        if bde_state_file.exists()
        else {"processed_slugs": {}, "covers_uploaded": {}}
    )

    for r in catalog:
        slug = r["slug"]
        cov_id = bde_state["covers_uploaded"].get(slug, "")
        fid_or_key = bde_state["processed_slugs"].get(slug) or f"bde:{slug}"
        if fid_or_key not in book_covers:
            book_covers[fid_or_key] = {
                "title": r["title"],
                "author": r.get("author", ""),
                "source": "bdebooks.com",
                "book_url": r["url"],
                "cover_url": r.get("cover_url", ""),
                "thumbnail_url": r.get("thumbnail_url", ""),
                "cover_drive_id": cov_id,
            }
    covers_file.write_text(json.dumps(book_covers, ensure_ascii=False, indent=2), encoding="utf-8")

    # Select candidates with PDF/EPUB downloads not already duplicated by normalized title
    candidates = []
    for r in catalog:
        if r["slug"] in bde_state["processed_slugs"]:
            continue
        if not r.get("downloads"):
            continue
        # Prefer PDF (or EPUB) under 35 MB so downloads succeed quickly and don't blow Drive quota
        dls = r["downloads"]
        pdf_dls = [d for d in dls if d["format"] == "PDF"]
        epub_dls = [d for d in dls if d["format"] == "EPUB"]
        chosen = None
        for d in pdf_dls + epub_dls:
            if d["size_bytes"] == 0 or d["size_bytes"] <= 35 * 1024 * 1024:
                chosen = d
                break
        if not chosen:
            chosen = dls[0]

        norm_t = re.sub(r"[^a-z0-9\u0980-\u09ff]+", "", re.sub(r"\([^)]*\)", "", r["title"]).lower())
        if len(norm_t) >= 4 and norm_t in known_norms:
            bde_state["processed_slugs"][r["slug"]] = "duplicate"
            continue
        candidates.append((r, chosen, norm_t))

    bde_state_file.write_text(json.dumps(bde_state, ensure_ascii=False), encoding="utf-8")
    print(f"Non-duplicate BDeBooks with downloadable PDF/EPUB: {len(candidates)}", flush=True)

    # Download & upload respecting ~55 req/min POST limit on /bn/books/... (1.1s interval)
    added = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for idx, (r, dl, norm_t) in enumerate(candidates, 1):
            t0 = time.time()
            ext = ".epub" if dl["format"] == "EPUB" else ".pdf"
            title_clean = re.sub(r"\s*\([^)]*\)", "", r["title"]).strip()
            author_clean = re.sub(r"\s*\([^)]*\)", "", r.get("author", "")).strip()
            fname_base = sanitize_filename(f"{title_clean} - {author_clean}" if author_clean else title_clean)

            f_path = download_bde_file(r["url"], dl["token"], ext, tmp_dir, fname_base)
            if not f_path:
                bde_state["processed_slugs"][r["slug"]] = "failed"
            else:
                raw_item = {
                    "name": f_path.name,
                    "category": " ".join(r.get("subjects", [])),
                    "subfolder": author_clean,
                    "source_path": f"{' '.join(r.get('subjects', []))} {r['title']}",
                    "size": f_path.stat().st_size,
                }
                top_path, leaf, _, _ = b25.classify_book_leaf(raw_item)
                clean_top = clean_tax_segment(top_path.split("/")[0])
                clean_lp = clean_tax_path(f"{top_path}/{leaf}")
                clean_leaf = clean_tax_segment(leaf)
                dest_fid = clean_folders.get(f"pdf/{clean_lp}") or clean_folders["pdf/Literature/Novels"]
                new_fid = gd_upload(f_path, dest_fid)

                # Also upload cover image to covers/BDeBooks
                cov_fid = ""
                if r.get("cover_url"):
                    try:
                        cov_ext = Path(urllib.parse.urlparse(r["cover_url"]).path).suffix or ".webp"
                        cov_path = tmp_dir / f"{fname_base}{cov_ext}"
                        cov_req = urllib.request.Request(r["cover_url"], headers=REQ_HDR)
                        with urllib.request.urlopen(cov_req, timeout=15) as cr:
                            cov_path.write_bytes(cr.read())
                        cov_fid = gd_upload(cov_path, covers_bde_id) or ""
                        cov_path.unlink(missing_ok=True)
                    except Exception:
                        pass

                f_path.unlink(missing_ok=True)
                if new_fid:
                    bde_state["processed_slugs"][r["slug"]] = new_fid
                    if cov_fid:
                        bde_state["covers_uploaded"][r["slug"]] = cov_fid
                    known_norms.add(norm_t)
                    src_id = f"bde:{r['slug']}"
                    rec = {
                        "source_id": src_id,
                        "file_id": new_fid,
                        "name": f"{fname_base}{ext}",
                        "size": raw_item["size"],
                        "mimeType": "application/epub+zip" if ext == ".epub" else "application/pdf",
                        "top_category": clean_top,
                        "leaf_path": clean_lp,
                        "leaf_category": clean_leaf,
                        "subfolder": None,
                        "author": author_clean or "Various / Compiled (সংকলিত)",
                        "publication": "BDeBooks (bdebooks.com)",
                        "link": f"https://drive.google.com/file/d/{new_fid}/view",
                        "cover_url": r.get("cover_url", ""),
                        "thumbnail_url": r.get("thumbnail_url", ""),
                        "cover_drive_id": cov_fid,
                        "source_url": r["url"],
                    }
                    extra_books.append(rec)
                    book_covers[new_fid] = {
                        "title": title_clean,
                        "author": author_clean,
                        "source": "bdebooks.com",
                        "book_url": r["url"],
                        "cover_url": r.get("cover_url", ""),
                        "thumbnail_url": r.get("thumbnail_url", ""),
                        "cover_drive_id": cov_fid,
                        "cover_drive_link": f"https://drive.google.com/file/d/{cov_fid}/view" if cov_fid else "",
                    }
                    added += 1

            if idx % 25 == 0:
                print(f"  BDeBooks {idx}/{len(candidates)} processed (added {added})", flush=True)
                bde_state_file.write_text(json.dumps(bde_state, ensure_ascii=False), encoding="utf-8")
                extra_file.write_text(json.dumps(extra_books, ensure_ascii=False, indent=2), encoding="utf-8")
                covers_file.write_text(json.dumps(book_covers, ensure_ascii=False, indent=2), encoding="utf-8")

            elapsed = time.time() - t0
            if elapsed < 1.15:
                time.sleep(1.15 - elapsed)

    bde_state_file.write_text(json.dumps(bde_state, ensure_ascii=False), encoding="utf-8")
    extra_file.write_text(json.dumps(extra_books, ensure_ascii=False, indent=2), encoding="utf-8")
    covers_file.write_text(json.dumps(book_covers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"BDeBooks Done! Added {added} books and updated book_covers.json ({len(book_covers)} total).", flush=True)


if __name__ == "__main__":
    main()
