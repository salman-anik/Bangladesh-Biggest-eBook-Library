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
TEXT_DIR = REPO_DIR / "text"

REQ_HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def clean_tax_segment(raw: str) -> str:
    if not re.search(r"[A-Za-z]", raw):
        return raw
    s = re.sub(r"^\d+_", "", raw)
    s2 = re.sub(r"[\u0980-\u09FF]+", "", s)
    s2 = re.sub(r"_+", " ", s2).strip()
    return re.sub(r"\s+", " ", s2) or raw


def clean_tax_path(raw_path: str) -> str:
    return "/".join(clean_tax_segment(seg) for seg in raw_path.split("/"))


def sanitize_filename(name: str) -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", name)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > 120:
        s = s[:120].strip()
    return s or "Untitled_Book"


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


def download_bytes(url: str, timeout: int = 20) -> bytes:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=REQ_HDR)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception:
            if attempt == 2:
                return b""
            time.sleep(0.8 * (attempt + 1))
    return b""


def strip_html_text(fragment: str) -> str:
    txt = re.sub(r"<(br|p|/p|div|/div|h[1-6]|/h[1-6]|li|/li)[^>]*>", "\n", fragment, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html_lib.unescape(txt)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in txt.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def parse_eb_book_page(url: str) -> dict | None:
    body = fetch_text(url)
    if not body:
        return None

    # ID from post class postid-123 or learndash_post_123
    id_m = re.search(r"learndash_post_(\d+)|postid-(\d+)", body)
    post_id = (id_m.group(1) or id_m.group(2)) if id_m else ""

    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    if not title_m:
        title_m = re.search(r"<title>(.*?)</title>", body, re.S)
    title = strip_html_text(title_m.group(1)) if title_m else url.rstrip("/").split("/")[-1]
    title = title.replace(" – ", " - ").strip()

    og_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', body)
    if not og_m:
        og_m = re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', body)
    cover_url = og_m.group(1) if og_m else ""

    thumb_m = re.search(r"data-srcset=[\"']([^\"'\s]+-200x300\.[^\"'\s]+)", body)
    if not thumb_m:
        thumb_m = re.search(r"srcset=[\"']([^\"'\s]+-200x300\.[^\"'\s]+)", body)
    thumbnail_url = thumb_m.group(1) if thumb_m else cover_url

    art_m = re.search(r"<article[^>]*>(.*?)</article>", body, re.S)
    art = art_m.group(1) if art_m else body

    authors = [
        strip_html_text(a)
        for a in re.findall(r'href=["\']https://www\.ebanglalibrary\.com/authors/[^"\']+["\'][^>]*>(.*?)</a>', art, re.S)
    ]
    author = ", ".join(a for a in authors if a)

    genres = [
        strip_html_text(g)
        for g in re.findall(r'href=["\']https://www\.ebanglalibrary\.com/genres/[^"\']+["\'][^>]*>(.*?)</a>', art, re.S)
    ]
    genres = [g for g in genres if g and g.lower() != "editor's choice"]

    # Extract main content block before ld-item-list (lessons list)
    tab_idx = art.find('class="ld-tab-content')
    if tab_idx == -1:
        tab_idx = art.find('class="entry-content')
    lesson_list_idx = art.find('class="ld-item-list')
    content_html = ""
    if tab_idx != -1:
        end_idx = lesson_list_idx if (lesson_list_idx != -1 and lesson_list_idx > tab_idx) else len(art)
        content_html = art[tab_idx:end_idx]
    content_text = strip_html_text(content_html)

    # Extract lessons / chapters (URL + title)
    lesson_urls = []
    seen_u = set()
    for l_url, l_title_html in re.findall(
        r'<a[^>]+class="[^"]*ld-item-name[^"]*"[^>]+href=["\'](https://www\.ebanglalibrary\.com/lessons/[^"\']+)["\'][^>]*>(.*?)</a>',
        art,
        re.S,
    ):
        if l_url not in seen_u:
            seen_u.add(l_url)
            lesson_urls.append({"url": l_url, "title": strip_html_text(l_title_html)})
    if not lesson_urls:
        for l_url in re.findall(r'href=["\'](https://www\.ebanglalibrary\.com/lessons/[^"\']+)["\']', art):
            if l_url not in seen_u:
                seen_u.add(l_url)
                slug = urllib.parse.unquote(l_url.rstrip("/").split("/")[-1]).replace("-", " ")
                lesson_urls.append({"url": l_url, "title": slug})

    return {
        "source": "ebanglalibrary.com",
        "post_id": post_id,
        "url": url,
        "title": title,
        "author": author or "Various / Unknown",
        "genres": genres,
        "cover_url": cover_url,
        "thumbnail_url": thumbnail_url,
        "intro_content": content_text,
        "chapters": lesson_urls,
        "chapter_count": len(lesson_urls),
    }


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
        time.sleep(0.5 * (attempt + 1))
    return []


def gd_ensure_folder(name: str, parent_id: str, existing_children: dict[str, str] | None = None) -> str:
    if existing_children is None:
        children = gd_ls(parent_id)
        existing_children = {
            c["name"]: c["id"]
            for c in children
            if c.get("mimeType") == "application/vnd.google-apps.folder"
        }
    if name in existing_children:
        return existing_children[name]
    for attempt in range(4):
        try:
            res = gd_run(["mutate", "mkdir", name, "--parent", parent_id])
            if res.returncode == 0:
                fid = parse_gdrive_id(res.stdout)
                if fid:
                    return fid
        except Exception:
            pass
        time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"mkdir failed for {name} under {parent_id}")


def gd_upload(local_path: Path, parent_id: str) -> str | None:
    for attempt in range(4):
        try:
            res = gd_run(["mutate", "upload", str(local_path), "--parent", parent_id], timeout=60)
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
    text_root_id = clean_folders["text"]
    covers_eb_folder_id = clean_folders["covers/eBanglaLibrary"]

    # 1. Discover ALL sfwd-courses sitemaps from wp-sitemap.xml
    cache_file = DATA_DIR / "ebanglalibrary_raw.json"
    if cache_file.exists():
        eb_books = json.loads(cache_file.read_text(encoding="utf-8"))
        print(f"Loaded {len(eb_books)} cached eBanglaLibrary books.", flush=True)
    else:
        print("Step 1: Discovering all books from ebanglalibrary.com sitemaps...", flush=True)
        idx_xml = fetch_text("https://www.ebanglalibrary.com/wp-sitemap.xml")
        course_sms = re.findall(r"<loc>(https://www\.ebanglalibrary\.com/wp-sitemap-posts-sfwd-courses-[^<]+)</loc>", idx_xml)
        if not course_sms:
            course_sms = [
                f"https://www.ebanglalibrary.com/wp-sitemap-posts-sfwd-courses-{i}.xml"
                for i in (1, 2, 3)
            ]
        book_urls = []
        for sm_u in course_sms:
            sm_xml = fetch_text(sm_u)
            locs = re.findall(r"<loc>(.*?)</loc>", sm_xml)
            book_urls.extend(locs)
            print(f"  {sm_u} -> {len(locs)} URLs", flush=True)
        book_urls = list(dict.fromkeys(book_urls))
        print(f"Total unique eBanglaLibrary book URLs: {len(book_urls)}", flush=True)

        eb_books = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
            futs = {ex.submit(parse_eb_book_page, u): u for u in book_urls}
            done = 0
            for f in concurrent.futures.as_completed(futs):
                rec = f.result()
                if rec:
                    eb_books.append(rec)
                done += 1
                if done % 250 == 0:
                    print(f"  Scraped {done}/{len(book_urls)} eBanglaLibrary books", flush=True)
        cache_file.write_text(json.dumps(eb_books, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(eb_books)} eBanglaLibrary books to ebanglalibrary_raw.json", flush=True)

    # 2. Classify each book & ensure text/<Category>/<Leaf> hierarchy in Google Drive
    print("Step 2: Creating clean category hierarchy under Drive text/...", flush=True)
    if not clean_folders.get("text_ready"):
        top_existing = {c["name"]: c["id"] for c in gd_ls(text_root_id) if c.get("mimeType") == "application/vnd.google-apps.folder"}
        for tc, sub in b25.TAXONOMY.items():
            ctc = clean_tax_segment(tc)
            tpath = f"text/{ctc}"
            if tpath not in clean_folders:
                clean_folders[tpath] = gd_ensure_folder(ctc, text_root_id, top_existing)
        # Create mid & leaves concurrently per level
        todo_mid = []
        for tc, sub in b25.TAXONOMY.items():
            ctc = clean_tax_segment(tc)
            if isinstance(sub, dict):
                for mid in sub.keys():
                    cmid = clean_tax_segment(mid)
                    mpath = f"text/{ctc}/{cmid}"
                    if mpath not in clean_folders:
                        todo_mid.append((mpath, cmid, clean_folders[f"text/{ctc}"]))
        if todo_mid:
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
                futs = {ex.submit(gd_ensure_folder, name, pid): mpath for mpath, name, pid in todo_mid}
                for f in concurrent.futures.as_completed(futs):
                    clean_folders[futs[f]] = f.result()

        # Gather unique leaves needed by eb_books + full taxonomy leaves
        needed_leaves = []
        for tc, sub in b25.TAXONOMY.items():
            ctc = clean_tax_segment(tc)
            if isinstance(sub, dict):
                for mid, leaves in sub.items():
                    cmid = clean_tax_segment(mid)
                    for lf in leaves:
                        clf = clean_tax_segment(lf)
                        lpath = f"text/{ctc}/{cmid}/{clf}"
                        if lpath not in clean_folders:
                            needed_leaves.append((lpath, clf, clean_folders[f"text/{ctc}/{cmid}"]))
            else:
                for lf in sub:
                    clf = clean_tax_segment(lf)
                    lpath = f"text/{ctc}/{clf}"
                    if lpath not in clean_folders:
                        needed_leaves.append((lpath, clf, clean_folders[f"text/{ctc}"]))
        if needed_leaves:
            print(f"  Creating {len(needed_leaves)} leaf folders under text/...", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
                futs = {ex.submit(gd_ensure_folder, name, pid, {}): lpath for lpath, name, pid in needed_leaves}
                for f in concurrent.futures.as_completed(futs):
                    clean_folders[futs[f]] = f.result()
        clean_folders["text_ready"] = True
        (DATA_DIR / "clean_folders.json").write_text(json.dumps(clean_folders, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. Write per-book JSON locally under text/<Category>/<Leaf>/ AND upload to Drive
    eb_state_file = DATA_DIR / "eb_upload_state.json"
    eb_state = json.loads(eb_state_file.read_text(encoding="utf-8")) if eb_state_file.exists() else {"uploaded": {}, "covers": {}}

    covers_file = DATA_DIR / "book_covers.json"
    book_covers = json.loads(covers_file.read_text(encoding="utf-8")) if covers_file.exists() else {}

    extra_file = DATA_DIR / "extra_books.json"
    extra_books = json.loads(extra_file.read_text(encoding="utf-8")) if extra_file.exists() else []
    done_src_keys = {b.get("source_id") for b in extra_books if b.get("source_id")}

    classified = []
    seen_paths = set()
    for b in eb_books:
        raw_item = {
            "name": f"{b['title']} - {b['author']}.json",
            "category": " ".join(b.get("genres", [])),
            "subfolder": b.get("author", ""),
            "source_path": f"{' '.join(b.get('genres', []))} {b['title']}",
            "size": len(b.get("intro_content", "").encode("utf-8")),
        }
        top_path, leaf, _, _ = b25.classify_book_leaf(raw_item)
        clean_top = clean_tax_segment(top_path.split("/")[0])
        clean_lp = clean_tax_path(f"{top_path}/{leaf}")
        clean_leaf = clean_tax_segment(leaf)

        raw_title = (b.get("title") or "").strip()
        raw_auth = (b.get("author") or "").strip()
        # Strip trailing author from title if already present so real_title is pure book name
        real_title = raw_title
        if raw_auth and raw_auth != "Various / Unknown":
            for sep in (" - ", " – ", " — ", "-"):
                if real_title.endswith(f"{sep}{raw_auth}"):
                    real_title = real_title[: -len(f"{sep}{raw_auth}")].strip()
        b["real_title"] = real_title or raw_title
        if raw_auth and raw_auth != "Various / Unknown" and raw_auth not in real_title:
            fname_base = sanitize_filename(f"{real_title} - {raw_auth}")
        else:
            fname_base = sanitize_filename(real_title or raw_title)
        rel_json = f"{clean_lp}/{fname_base}.json"
        if rel_json in seen_paths:
            suffix = b.get("post_id") or str(len(seen_paths))
            rel_json = f"{clean_lp}/{fname_base} ({suffix}).json"
        seen_paths.add(rel_json)

        out_path = TEXT_DIR / rel_json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        book_payload = {
            **b,
            "top_category": clean_top,
            "leaf_path": clean_lp,
            "leaf_category": clean_leaf,
            "format": "json",
        }
        out_path.write_text(json.dumps(book_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        classified.append((b, clean_top, clean_lp, clean_leaf, out_path))

    # Track ALL covers & upload JSONs to Drive text/<leaf>
    todo_uploads = [(b, ct, clp, cl, p) for (b, ct, clp, cl, p) in classified if b["url"] not in eb_state["uploaded"]]
    print(f"Step 3: Uploading {len(todo_uploads)} eBanglaLibrary JSON books to Drive text/...", flush=True)

    if todo_uploads:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            futs = {}
            for b, ct, clp, cl, p in todo_uploads:
                dest_fid = clean_folders.get(f"text/{clp}") or clean_folders["text/Literature/Novels"]
                futs[ex.submit(gd_upload, p, dest_fid)] = (b, ct, clp, cl, p)
            done = 0
            for f in concurrent.futures.as_completed(futs):
                b, ct, clp, cl, p = futs[f]
                fid = f.result()
                done += 1
                if fid:
                    eb_state["uploaded"][b["url"]] = fid
                    src_id = f"eb:{b['post_id'] or fid}"
                    if src_id not in done_src_keys:
                        extra_books.append({
                            "source_id": src_id,
                            "file_id": fid,
                            "name": p.name,
                            "size": p.stat().st_size,
                            "mimeType": "application/json",
                            "top_category": ct,
                            "leaf_path": f"text/{clp}",
                            "leaf_category": cl,
                            "subfolder": None,
                            "section": "text",
                            "author": b.get("author") or "Various / Compiled (সংকলিত)",
                            "publication": "eBanglaLibrary (ebanglalibrary.com)",
                            "link": f"https://drive.google.com/file/d/{fid}/view",
                            "cover_url": b.get("cover_url", ""),
                            "thumbnail_url": b.get("thumbnail_url", ""),
                            "source_url": b["url"],
                        })
                        done_src_keys.add(src_id)
                if done % 100 == 0:
                    print(f"  Uploaded {done}/{len(todo_uploads)} JSON books to Drive text/", flush=True)
                    eb_state_file.write_text(json.dumps(eb_state, ensure_ascii=False), encoding="utf-8")
                    extra_file.write_text(json.dumps(extra_books, ensure_ascii=False, indent=2), encoding="utf-8")

        eb_state_file.write_text(json.dumps(eb_state, ensure_ascii=False), encoding="utf-8")
        extra_file.write_text(json.dumps(extra_books, ensure_ascii=False, indent=2), encoding="utf-8")

    # Download & upload unique cover images to covers/eBanglaLibrary
    unique_covers = {}
    for b, _, _, _, _ in classified:
        cu = b.get("cover_url") or ""
        if cu and cu not in eb_state["covers"] and cu not in unique_covers:
            unique_covers[cu] = b["title"]

    if unique_covers:
        print(f"Step 4: Downloading & uploading {len(unique_covers)} unique eBanglaLibrary covers to Drive covers/...", flush=True)
        with tempfile.TemporaryDirectory() as ctmp:
            ctmp_dir = Path(ctmp)
            downloaded_covs = []

            def dl_cov(idx_item):
                idx, (cu, title) = idx_item
                data = download_bytes(cu, timeout=15)
                if len(data) < 512:
                    return None
                ext = Path(urllib.parse.urlparse(cu).path).suffix.lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                    ext = ".jpg"
                cname = sanitize_filename(title) + ext
                sub = ctmp_dir / str(idx)
                sub.mkdir(parents=True, exist_ok=True)
                p = sub / cname
                p.write_bytes(data)
                return (cu, p, cname)

            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as dex:
                for res in dex.map(dl_cov, list(enumerate(unique_covers.items()))):
                    if res:
                        downloaded_covs.append(res)

            print(f"  Downloaded {len(downloaded_covs)} cover images; uploading to Drive...", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as uex:
                futs = {uex.submit(gd_upload, p, covers_eb_folder_id): cu for cu, p, _ in downloaded_covs}
                done_c = 0
                for f in concurrent.futures.as_completed(futs):
                    cu = futs[f]
                    cfid = f.result()
                    if cfid:
                        eb_state["covers"][cu] = cfid
                    done_c += 1
                    if done_c % 100 == 0:
                        print(f"  Uploaded {done_c}/{len(downloaded_covs)} eBanglaLibrary covers", flush=True)
                        eb_state_file.write_text(json.dumps(eb_state, ensure_ascii=False), encoding="utf-8")
            eb_state_file.write_text(json.dumps(eb_state, ensure_ascii=False), encoding="utf-8")

    # Save cover URLs for ALL eBanglaLibrary books into book_covers.json
    for b, ct, clp, cl, p in classified:
        fid = eb_state["uploaded"].get(b["url"], b.get("post_id") or b["url"])
        cfid = eb_state["covers"].get(b.get("cover_url") or "", "")
        book_covers[fid] = {
            "title": b["title"],
            "author": b.get("author", ""),
            "source": "ebanglalibrary.com",
            "book_url": b["url"],
            "cover_url": b.get("cover_url", ""),
            "thumbnail_url": b.get("thumbnail_url", ""),
            "cover_drive_id": cfid,
            "cover_drive_link": f"https://drive.google.com/file/d/{cfid}/view" if cfid else "",
        }
    covers_file.write_text(json.dumps(book_covers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"eBanglaLibrary Done! {len(eb_state['uploaded'])} JSON books in Drive text/ and {len(eb_state['covers'])} covers.", flush=True)


if __name__ == "__main__":
    main()
