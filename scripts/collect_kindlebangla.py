import concurrent.futures
import html as html_lib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

UNRAR_EXE = Path(r"C:\Users\USER\.gemini\antigravity\scratch\tools\unrar\UnRAR.exe")

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

EBOOK_EXTS = {".pdf", ".epub", ".mobi", ".azw3", ".djvu"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


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
    safe_url = quote_iri(url)
    for attempt in range(3):
        try:
            req = urllib.request.Request(safe_url, headers=REQ_HDR)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception:
            if attempt == 2:
                return ""
            time.sleep(1.0 * (attempt + 1))
    return ""


def quote_iri(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(p.path), safe="/:@")
    query = urllib.parse.quote(urllib.parse.unquote(p.query), safe="=&:@/+")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, query, ""))


def resolve_redirect(url: str) -> str:
    opener = urllib.request.build_opener(NoRedirect)
    cur = quote_iri(url)
    for attempt in range(4):
        try:
            u = cur
            for _ in range(6):
                req = urllib.request.Request(quote_iri(u), headers=REQ_HDR)
                try:
                    resp = opener.open(req, timeout=20)
                    return resp.url
                except urllib.error.HTTPError as e:
                    if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                        nxt = urllib.parse.urljoin(u, e.headers["Location"])
                        if "drive.google.com" in nxt or "docs.google.com" in nxt:
                            return nxt
                        u = nxt
                        continue
                    return ""
            return u
        except Exception:
            time.sleep(1.0 * (attempt + 1))
    return ""


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


def gd_run(args: list[str], timeout: int = 45) -> subprocess.CompletedProcess:
    return subprocess.run(
        GDRIVE_BASE + args,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def gd_ls(folder_id: str) -> list[dict]:
    for attempt in range(3):
        try:
            res = gd_run(["readonly", "ls", folder_id, "--max", "0", "--json"])
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception:
            pass
        time.sleep(0.8 * (attempt + 1))
    return []


def gd_stream_ls(folder_ids: list[str]) -> dict[str, list[dict]]:
    if not folder_ids:
        return {}
    inp = DATA_DIR / "kb_stream_in.jsonl"
    out = DATA_DIR / "kb_stream_out.jsonl"
    inp.write_text("\n".join(json.dumps({"id": fid}) for fid in folder_ids) + "\n", encoding="utf-8")
    out.unlink(missing_ok=True)
    res_map: dict[str, list[dict]] = {}
    try:
        gd_run(["readonly", "stream", "ls", "-i", str(inp), "-o", str(out), "-c", "16", "--max", "100"], timeout=300)
        if out.exists():
            for line in out.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                fid = obj.get("id") or obj.get("target")
                if fid and obj.get("_ok") and isinstance(obj.get("data"), list):
                    res_map[fid] = obj["data"]
    finally:
        inp.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
    return res_map


def gd_info(file_id: str) -> dict | None:
    try:
        res = gd_run(["readonly", "info", file_id, "--json"])
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
    except Exception:
        pass
    return None


def gd_upload(local_path: Path, parent_id: str) -> str | None:
    for attempt in range(4):
        try:
            res = gd_run(["mutate", "upload", str(local_path), "--parent", parent_id], timeout=120)
            if res.returncode == 0:
                fid = parse_gdrive_id(res.stdout)
                if fid:
                    return fid
        except Exception:
            pass
        time.sleep(1.0 * (attempt + 1))
    return None


def gd_download(file_id: str, out_path: Path) -> bool:
    for attempt in range(3):
        try:
            res = gd_run(["readonly", "download", file_id, "--out", str(out_path)], timeout=180)
            if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return True
        except Exception:
            pass
        time.sleep(1.0 * (attempt + 1))
    return False


def extract_archive(arc_path: Path, out_dir: Path) -> bool:
    ext = arc_path.suffix.lower()
    if ext == ".rar" and UNRAR_EXE.exists():
        res = subprocess.run(
            [str(UNRAR_EXE), "x", "-y", "-idq", str(arc_path), str(out_dir) + "\\"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        return res.returncode == 0
    if ext == ".zip":
        try:
            with zipfile.ZipFile(arc_path, "r") as zf:
                zf.extractall(out_dir)
            return True
        except Exception:
            return False
    return False


def gd_cp(src_id: str, name: str, parent_id: str) -> str | None:
    for attempt in range(3):
        try:
            res = gd_run(["mutate", "cp", src_id, name, "--parent", parent_id])
            if res.returncode == 0:
                fid = parse_gdrive_id(res.stdout)
                if fid:
                    return fid
            err = (res.stderr or "") + (res.stdout or "")
            if any(x in err.lower() for x in ["not found", "404", "permission", "cannot copy"]):
                return None
        except Exception:
            pass
        time.sleep(1.0 * (attempt + 1))
    return None


def parse_kb_book_page(book_url: str) -> dict | None:
    body = fetch_text(book_url)
    if not body:
        return None
    title_m = re.search(r"<title>(.*?)</title>", body, re.S)
    raw_title = html_lib.unescape(title_m.group(1).strip()) if title_m else ""
    og_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', body)
    if not og_m:
        og_m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', body)
    cover_url = og_m.group(1) if og_m else ""

    writer_m = re.search(r'href=["\']/writer/[^"\']*["\'][^>]*>(.*?)</a>', body, re.S)
    writer = html_lib.unescape(re.sub(r"<[^>]+>", "", writer_m.group(1)).strip()) if writer_m else ""

    cats = [
        html_lib.unescape(re.sub(r"<[^>]+>", "", c).strip())
        for c in re.findall(r'href=["\']/category/[^"\']+["\'][^>]*>(.*?)</a>', body, re.S)
    ]

    dl_m = re.search(r'href=["\'](/download/[^"\']+)["\']', body)
    dl_path = html_lib.unescape(dl_m.group(1)) if dl_m else ""
    drive_url = resolve_redirect(f"https://www.kindlebangla.com{dl_path}") if dl_path else ""

    # Fallback: check if drive.google.com appears directly in body
    if not drive_url:
        dm = re.search(r"https://drive\.google\.com/[^\s\"'<>]+", body)
        if dm:
            drive_url = html_lib.unescape(dm.group(0))

    # Build a clean title from raw_title stripping " - Author" if repeated
    book_name = raw_title
    if " - " in raw_title and not writer:
        parts = raw_title.rsplit(" - ", 1)
        book_name, writer = parts[0].strip(), parts[1].strip()
    elif writer and raw_title.endswith(f"- {writer}"):
        book_name = raw_title[: -(len(writer) + 2)].strip()

    # Cloudinary thumbnail variant (300px wide) + full cover URL
    thumb_url = cover_url
    if "res.cloudinary.com" in cover_url and "/image/upload/" in cover_url:
        thumb_url = cover_url.replace("/image/upload/", "/image/upload/w_300,q_auto,f_auto/")

    drive_folder_id = ""
    drive_file_id = ""
    fm = re.search(r"/folders/([A-Za-z0-9_-]+)", drive_url)
    if fm:
        drive_folder_id = fm.group(1)
    else:
        fim = re.search(r"(?:/file/d/|id=)([A-Za-z0-9_-]+)", drive_url)
        if fim:
            drive_file_id = fim.group(1)

    return {
        "url": book_url,
        "title": book_name or raw_title,
        "raw_title": raw_title,
        "author": writer,
        "categories": [c for c in cats if c],
        "cover_url": cover_url,
        "thumbnail_url": thumb_url,
        "dl_url": drive_url,
        "drive_folder_id": drive_folder_id,
        "drive_file_id": drive_file_id,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(REPO_DIR / "scripts"))
    import clean_classifier as cc  # noqa: E402

    clean_folders = json.loads((DATA_DIR / "clean_folders.json").read_text(encoding="utf-8"))
    covers_kb_folder_id = clean_folders["covers/KindleBangla"]

    meta_cache_file = DATA_DIR / "kindlebangla_catalog.json"
    if meta_cache_file.exists():
        kb_catalog = json.loads(meta_cache_file.read_text(encoding="utf-8"))
        print(f"Loaded {len(kb_catalog)} cached KindleBangla book records.", flush=True)
    else:
        print("Step 1: Fetching KindleBangla sitemap.xml...", flush=True)
        sm = fetch_text("https://www.kindlebangla.com/sitemap.xml")
        book_urls = [u for u in re.findall(r"<loc>(.*?)</loc>", sm) if "/book/" in u]
        print(f"Found {len(book_urls)} book URLs in KindleBangla sitemap.", flush=True)

        kb_catalog = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=28) as ex:
            futs = {ex.submit(parse_kb_book_page, u): u for u in book_urls}
            done = 0
            for f in concurrent.futures.as_completed(futs):
                rec = f.result()
                if rec:
                    kb_catalog.append(rec)
                done += 1
                if done % 150 == 0:
                    print(f"  Scraped {done}/{len(book_urls)} KindleBangla pages", flush=True)
        meta_cache_file.write_text(json.dumps(kb_catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(kb_catalog)} records to kindlebangla_catalog.json", flush=True)

    # Track already ingested source IDs and existing filenames to avoid duplicates
    extra_file = DATA_DIR / "extra_books.json"
    extra_books = json.loads(extra_file.read_text(encoding="utf-8")) if extra_file.exists() else []
    done_src_keys = {b.get("source_id") for b in extra_books if b.get("source_id")}
    known_titles_norm = {
        re.sub(r"[^a-z0-9\u0980-\u09ff]+", "", Path(b["name"]).stem.lower())
        for b in extra_books
    }

    covers_file = DATA_DIR / "book_covers.json"
    book_covers = json.loads(covers_file.read_text(encoding="utf-8")) if covers_file.exists() else {}

    kb_state_file = DATA_DIR / "kb_ingest_state.json"
    kb_state = (
        json.loads(kb_state_file.read_text(encoding="utf-8"))
        if kb_state_file.exists()
        else {"processed_urls": {}, "copied_covers": {}}
    )

    def save_state() -> None:
        kb_state_file.write_text(json.dumps(kb_state, ensure_ascii=False, indent=2), encoding="utf-8")
        extra_file.write_text(json.dumps(extra_books, ensure_ascii=False, indent=2), encoding="utf-8")
        covers_file.write_text(json.dumps(book_covers, ensure_ascii=False, indent=2), encoding="utf-8")

    todo = [r for r in kb_catalog if r["url"] not in kb_state["processed_urls"]]
    folder_ids_to_list = sorted({r["drive_folder_id"] for r in todo if r.get("drive_folder_id")})
    print(f"Step 2a: Batch streaming ls of {len(folder_ids_to_list)} KindleBangla Drive folders...", flush=True)
    streamed_folders = gd_stream_ls(folder_ids_to_list)
    print(f"  Streamed {len(streamed_folders)} folder contents!", flush=True)

    def process_one(rec: dict) -> dict | None:
        url = rec["url"]
        if url in kb_state["processed_urls"]:
            return None

        ebook_item = None
        cover_item = None
        local_ebook_path = None
        local_cover_path = None

        with tempfile.TemporaryDirectory() as work_tmp:
            work_dir = Path(work_tmp)
            src_key_id = ""

            if rec.get("drive_folder_id"):
                children = streamed_folders.get(rec["drive_folder_id"])
                if children is None:
                    children = gd_ls(rec["drive_folder_id"])
                ebooks = [c for c in children if Path(c["name"]).suffix.lower() in EBOOK_EXTS]
                ebooks.sort(key=lambda c: {".pdf": 0, ".epub": 1, ".mobi": 2, ".azw3": 3}.get(Path(c["name"]).suffix.lower(), 9))
                covers = [c for c in children if Path(c["name"]).suffix.lower() in IMAGE_EXTS]
                if ebooks:
                    ebook_item = ebooks[0]
                    src_key_id = ebook_item["id"]
                if covers:
                    cover_item = covers[0]
            elif rec.get("drive_file_id"):
                info = gd_info(rec["drive_file_id"])
                if info and info.get("id"):
                    fname = info.get("name") or f"{rec['title']}.pdf"
                    fext = Path(fname).suffix.lower()
                    src_key_id = info["id"]
                    if fext in (".rar", ".zip"):
                        arc_path = work_dir / f"arc{fext}"
                        ext_dir = work_dir / "ext"
                        ext_dir.mkdir(parents=True, exist_ok=True)
                        if gd_download(info["id"], arc_path) and extract_archive(arc_path, ext_dir):
                            all_files = [p for p in ext_dir.rglob("*") if p.is_file()]
                            eb_files = [p for p in all_files if p.suffix.lower() in EBOOK_EXTS]
                            eb_files.sort(key=lambda p: {".pdf": 0, ".epub": 1, ".mobi": 2, ".azw3": 3}.get(p.suffix.lower(), 9))
                            cov_files = [p for p in all_files if p.suffix.lower() in IMAGE_EXTS]
                            if eb_files:
                                local_ebook_path = eb_files[0]
                                ebook_item = {
                                    "id": info["id"],
                                    "name": local_ebook_path.name,
                                    "size": local_ebook_path.stat().st_size,
                                    "mimeType": "application/pdf" if local_ebook_path.suffix.lower() == ".pdf" else "application/epub+zip",
                                }
                            if cov_files:
                                local_cover_path = cov_files[0]
                        if not ebook_item:
                            # Archive extraction unavailable or contained no standard ebook ext; keep archive itself
                            ebook_item = {
                                "id": info["id"],
                                "name": fname,
                                "size": info.get("size", 0),
                                "mimeType": info.get("mimeType", "application/x-rar"),
                            }
                    else:
                        ebook_item = {
                            "id": info["id"],
                            "name": fname,
                            "size": info.get("size", 0),
                            "mimeType": info.get("mimeType", "application/epub+zip"),
                        }

            norm_title = unicodedata.normalize("NFC", (rec.get("title") or "").strip())
            norm_auth = unicodedata.normalize("NFC", (rec.get("author") or "").strip())
            if norm_auth and norm_auth.lower() not in norm_title.lower():
                raw_label = f"{norm_title} - {norm_auth}"
            else:
                raw_label = norm_title
            clean_base = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", raw_label).strip(" .")[:120]

            cover_drive_id = None
            if local_cover_path and rec["url"] not in kb_state["copied_covers"]:
                cov_ext = local_cover_path.suffix.lower() if local_cover_path.suffix.lower() in IMAGE_EXTS else ".jpg"
                target_cov = work_dir / f"{clean_base or local_cover_path.stem}{cov_ext}"
                if target_cov != local_cover_path:
                    shutil.copy2(local_cover_path, target_cov)
                cover_drive_id = gd_upload(target_cov, covers_kb_folder_id)
                if cover_drive_id:
                    kb_state["copied_covers"][rec["url"]] = cover_drive_id
            elif cover_item and rec["url"] not in kb_state["copied_covers"]:
                cov_ext = Path(cover_item["name"]).suffix.lower() or ".jpg"
                cov_name = f"{clean_base}{cov_ext}" if clean_base else cover_item["name"]
                cover_drive_id = gd_cp(cover_item["id"], cov_name, covers_kb_folder_id)
                if cover_drive_id:
                    kb_state["copied_covers"][rec["url"]] = cover_drive_id
            elif rec.get("cover_url") and rec["url"] not in kb_state["copied_covers"]:
                try:
                    cu = rec["cover_url"]
                    ext = Path(urllib.parse.urlparse(cu).path).suffix.lower()
                    if ext not in IMAGE_EXTS:
                        ext = ".jpg"
                    cname = (clean_base or "cover") + ext
                    cp = work_dir / cname
                    creq = urllib.request.Request(cu, headers=REQ_HDR)
                    with urllib.request.urlopen(creq, timeout=15) as cr:
                        data = cr.read()
                    if len(data) >= 512:
                        cp.write_bytes(data)
                        cfid = gd_upload(cp, covers_kb_folder_id)
                        if cfid:
                            cover_drive_id = cfid
                            kb_state["copied_covers"][rec["url"]] = cfid
                except Exception:
                    pass

            res_record = None
            if ebook_item and src_key_id:
                src_id = f"kb:{src_key_id}"
                if src_id not in done_src_keys:
                    clean_lp = cc.classify_clean_leaf(
                        title=rec.get("title") or ebook_item["name"],
                        author=rec.get("author", ""),
                        genres=rec.get("categories", []),
                        publication="Kindle Bangla (kindlebangla.com)",
                    )
                    clean_top = clean_lp.split("/")[0]
                    clean_leaf = clean_lp.split("/")[-1]
                    dest_folder_id = clean_folders.get(f"pdf/{clean_lp}") or clean_folders["pdf/Literature/Novels"]
                    eb_ext = Path(ebook_item["name"]).suffix.lower() or ".epub"
                    eb_target_name = f"{clean_base}{eb_ext}" if clean_base else ebook_item["name"]
                    if local_ebook_path:
                        target_eb = work_dir / eb_target_name
                        if target_eb != local_ebook_path:
                            shutil.copy2(local_ebook_path, target_eb)
                        new_fid = gd_upload(target_eb, dest_folder_id)
                    else:
                        new_fid = gd_cp(ebook_item["id"], eb_target_name, dest_folder_id)
                    if new_fid:
                        res_record = {
                            "source_id": src_id,
                            "file_id": new_fid,
                            "name": eb_target_name,
                            "size": int(ebook_item.get("size") or 0),
                            "mimeType": ebook_item.get("mimeType", "application/epub+zip"),
                            "top_category": clean_top,
                            "leaf_path": clean_lp,
                            "leaf_category": clean_leaf,
                            "subfolder": None,
                            "author": norm_auth or "Various / Compiled (সংকলিত)",
                            "publication": "Kindle Bangla (kindlebangla.com)",
                            "link": f"https://drive.google.com/file/d/{new_fid}/view",
                            "cover_url": rec.get("cover_url", ""),
                            "thumbnail_url": rec.get("thumbnail_url", ""),
                            "cover_drive_id": cover_drive_id or kb_state["copied_covers"].get(rec["url"], ""),
                            "internal_title": norm_title,
                        }
        return {
            "url": url,
            "rec": rec,
            "book": res_record,
            "cover_drive_id": cover_drive_id or kb_state["copied_covers"].get(rec["url"], ""),
        }

    print(f"Step 2b: Copying KindleBangla books & covers into Drive ({len(todo)} pending)...", flush=True)
    added = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(process_one, r): r for r in todo}
        done = 0
        for f in concurrent.futures.as_completed(futs):
            out = f.result()
            done += 1
            if out:
                r = out["rec"]
                kb_state["processed_urls"][out["url"]] = out["book"]["file_id"] if out["book"] else "no_file"
                cov_key = out["book"]["file_id"] if out["book"] else f"kb_url:{out['url']}"
                book_covers[cov_key] = {
                    "title": r["title"],
                    "author": r.get("author", ""),
                    "source": "kindlebangla.com",
                    "book_url": out["url"],
                    "cover_url": r.get("cover_url", ""),
                    "thumbnail_url": r.get("thumbnail_url", ""),
                    "cover_drive_id": out["cover_drive_id"],
                    "cover_drive_link": f"https://drive.google.com/file/d/{out['cover_drive_id']}/view" if out["cover_drive_id"] else "",
                }
                if out["book"]:
                    extra_books.append(out["book"])
                    done_src_keys.add(out["book"]["source_id"])
                    added += 1
            if done % 50 == 0:
                print(f"  KindleBangla processed {done}/{len(todo)} (added {added} books)", flush=True)
                save_state()

    save_state()
    print(f"KindleBangla Done! Added {added} books and {len(book_covers)} total tracked covers.", flush=True)


if __name__ == "__main__":
    main()
