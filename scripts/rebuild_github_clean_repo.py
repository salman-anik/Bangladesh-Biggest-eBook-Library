import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import quote

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
PDF_DIR = REPO_DIR / "pdf"
TEXT_DIR = REPO_DIR / "text"
VIS_PUBLIC = REPO_DIR / "visualize" / "public"

ROOT_DRIVE_ID = "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
PDF_DRIVE_ID = "1eAvkHOqOwF2lSri8Xe3X4NXtsKsGI2u-"
TEXT_DRIVE_ID = "1Kc2ENKN8z0nZpjbZAjqhTHrS6Ny3ii6X"
COVERS_DRIVE_ID = "1QLLOB1FSFrR36pb-7yb6O0gvNfWHJbTC"
REPO_WEB_BASE = "https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library"
GITHUB_BLOB_BASE = "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/blob/main"
GITHUB_TREE_BASE = "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/tree/main"

sys.path.insert(0, str(REPO_DIR / "scripts"))
import build_25cat_library as b25  # noqa: E402
import rename_books_by_internal_title as rbit  # noqa: E402

try:
    import reorganize_drive_and_clean as rdc  # noqa: E402
except Exception:
    rdc = None


def clean_tax_segment(raw: str) -> str:
    if not raw or not re.search(r"[A-Za-z]", raw):
        return raw
    s = re.sub(r"^\d+_", "", raw)
    s2 = re.sub(r"[\u0980-\u09FF]+", "", s)
    s2 = re.sub(r"_+", " ", s2).strip()
    return re.sub(r"\s+", " ", s2) or raw


def clean_tax_path(raw_path: str) -> str:
    return "/".join(clean_tax_segment(seg) for seg in raw_path.split("/") if seg)


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def fmt_size(b: int) -> str:
    if not b:
        return "-"
    u = ["B", "KB", "MB", "GB"]
    i = 0
    val = float(b)
    while val >= 1024 and i < len(u) - 1:
        val /= 1024
        i += 1
    return f"{int(val)} {u[i]}" if i == 0 else f"{val:.1f} {u[i]}"


def detect_nctb_classes(name: str) -> list[str]:
    if rdc:
        return rdc.detect_nctb_classes(name)
    low = name.lower()
    if "class-9-10" in low or "class 9-10" in low or "নবম দশম" in name or "নবম-দশম" in name:
        return ["Class 9", "Class 10"]
    for i in range(10, 0, -1):
        if f"class-{i}" in low or f"class {i}" in low:
            return [f"Class {i}"]
    if "pre-primary" in low or "প্রাক-প্রাথমিক" in name:
        return ["Pre-Primary"]
    return ["Academic Textbooks"]


def load_folder_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Return (clean_folders_all, flat_taxonomy_folders)."""
    cf_path = DATA_DIR / "clean_folders.json"
    if cf_path.exists():
        cf = json.loads(cf_path.read_text(encoding="utf-8"))
    else:
        ts = json.loads((DATA_DIR / "taxonomy_state.json").read_text(encoding="utf-8"))
        cf = {
            "__ROOT__": ROOT_DRIVE_ID,
            "pdf": PDF_DRIVE_ID,
            "text": TEXT_DRIVE_ID,
            "covers": COVERS_DRIVE_ID,
        }
        for raw_path, fid in ts.get("folders", {}).items():
            cf[f"pdf/{clean_tax_path(raw_path)}"] = fid

    flat: dict[str, str] = {}
    for k, v in cf.items():
        if k in ("__ROOT__", "text_ready") or not isinstance(v, str):
            continue
        flat[k] = v
        if k.startswith("pdf/"):
            flat[k[4:]] = v
    return cf, flat


def build_clean_tree() -> dict[str, list | dict]:
    tree: dict[str, list | dict] = {}
    class_list = ["Pre-Primary"] + [f"Class {i}" for i in range(1, 11)]
    for raw_tc, sub in b25.TAXONOMY.items():
        ctc = clean_tax_segment(raw_tc)
        if isinstance(sub, dict):
            sub_clean: dict[str, list[str]] = {}
            for mid, leaves in sub.items():
                cmid = clean_tax_segment(mid)
                sub_clean[cmid] = [clean_tax_segment(lf) for lf in leaves]
            tree[ctc] = sub_clean
        else:
            leaves_clean = [clean_tax_segment(lf) for lf in sub]
            if ctc == "Education and Academics":
                ordered = []
                for c in class_list + leaves_clean:
                    if c not in ordered:
                        ordered.append(c)
                leaves_clean = ordered
            tree[ctc] = leaves_clean
    return tree


def collect_all_books() -> list[dict]:
    trashed_file = DATA_DIR / "trashed_ids.json"
    trashed = set(json.loads(trashed_file.read_text(encoding="utf-8"))) if trashed_file.exists() else set()

    covers_file = DATA_DIR / "book_covers.json"
    book_covers = json.loads(covers_file.read_text(encoding="utf-8")) if covers_file.exists() else {}

    ia_overrides = rdc.IA_KEEP_OVERRIDES if rdc else {}

    plan_file = DATA_DIR / "copy_plan.json"
    prog_file = DATA_DIR / "catalog_progress.json"
    extra_file = DATA_DIR / "extra_books.json"

    plan = json.loads(plan_file.read_text(encoding="utf-8")) if plan_file.exists() else []
    progress = json.loads(prog_file.read_text(encoding="utf-8")) if prog_file.exists() else {}
    extra = json.loads(extra_file.read_text(encoding="utf-8")) if extra_file.exists() else []

    by_fid: dict[str, dict] = {}

    for it in plan:
        fid = progress.get(it["source_id"])
        if not fid or fid in trashed:
            continue
        orig_name = it.get("name") or ""
        if Path(orig_name).suffix.lower() in (".ini", ".apk", ".lnk"):
            continue

        raw_top_path, raw_leaf, sub, _ = b25.classify_book_leaf(it)
        clean_top = clean_tax_segment(raw_top_path.split("/")[0])
        clean_lp = clean_tax_path(f"{raw_top_path}/{raw_leaf}")
        clean_leaf = clean_tax_segment(raw_leaf)
        clean_sub = clean_tax_segment(sub) if sub else None

        author = b25.extract_author(it)
        pub = b25.extract_publication(it)

        if "nctb" in pub.lower() or "NCTB" in orig_name:
            classes = detect_nctb_classes(orig_name)
            clean_top = "Education and Academics"
            clean_leaf = classes[0]
            clean_lp = f"Education and Academics/{clean_leaf}"
            clean_sub = None

        rec = {
            "source_id": it["source_id"],
            "file_id": fid,
            "name": orig_name,
            "size": int(it.get("size") or 0),
            "mimeType": it.get("mimeType") or "application/pdf",
            "top_category": clean_top,
            "leaf_path": clean_lp,
            "leaf_category": clean_leaf,
            "subfolder": clean_sub,
            "section": "pdf",
            "author": author,
            "publication": pub,
            "link": f"https://drive.google.com/file/d/{fid}/view",
        }
        rec["name"] = rbit.clean_book_filename(rec)
        by_fid[fid] = rec

    for raw in extra:
        fid = raw.get("file_id")
        if not fid or fid in trashed:
            continue
        orig_name = raw.get("name") or ""
        if Path(orig_name).suffix.lower() in (".ini", ".apk", ".lnk"):
            continue

        rec = dict(raw)
        lp = rec.get("leaf_path") or ""
        if lp.startswith("text/"):
            lp = lp[5:]
            rec["section"] = "text"
        elif str(rec.get("source_id") or "").startswith("eb:"):
            rec["section"] = "text"
        else:
            rec["section"] = rec.get("section") or "pdf"

        if fid in ia_overrides:
            lp = ia_overrides[fid]
        elif "nctb" in (rec.get("publication") or "").lower() or "NCTB" in orig_name:
            classes = detect_nctb_classes(orig_name)
            if str(rec.get("source_id") or "").startswith("nctb10:"):
                lp = "Education and Academics/Class 10"
            else:
                lp = f"Education and Academics/{classes[0]}"
            rec["subfolder"] = None

        clean_lp = clean_tax_path(lp) if lp else clean_tax_segment(rec.get("top_category") or "Others and Unclassified")
        clean_top = clean_lp.split("/")[0]
        clean_leaf = clean_lp.split("/")[-1]

        rec["top_category"] = clean_top
        rec["leaf_path"] = clean_lp
        rec["leaf_category"] = clean_leaf
        if rec.get("subfolder"):
            rec["subfolder"] = clean_tax_segment(rec["subfolder"])
        rec["link"] = rec.get("link") or f"https://drive.google.com/file/d/{fid}/view"
        rec["name"] = rbit.clean_book_filename(rec)

        cov = book_covers.get(fid) or book_covers.get(rec.get("source_id") or "")
        if cov:
            if cov.get("cover_url") and not rec.get("cover_url"):
                rec["cover_url"] = cov["cover_url"]
            if cov.get("thumbnail_url") and not rec.get("thumbnail_url"):
                rec["thumbnail_url"] = cov["thumbnail_url"]
            if cov.get("cover_drive_id") and not rec.get("cover_drive_id"):
                rec["cover_drive_id"] = cov["cover_drive_id"]

        by_fid[fid] = rec

    books = sorted(by_fid.values(), key=lambda x: (x["section"], x["leaf_path"], x["name"]))
    return books


def write_category_readmes(
    base_dir: Path,
    section: str,
    sec_books: list[dict],
    tree: dict[str, list | dict],
    flat_folders: dict[str, str],
) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    by_lp: dict[str, list[dict]] = defaultdict(list)
    by_tc: dict[str, list[dict]] = defaultdict(list)
    for b in sec_books:
        by_lp[b["leaf_path"]].append(b)
        by_tc[b["top_category"]].append(b)

    def folder_drive_link(clean_path: str) -> str:
        did = flat_folders.get(f"{section}/{clean_path}") or flat_folders.get(clean_path)
        return f"https://drive.google.com/drive/folders/{did}" if did else ""

    # Section root README.md
    sec_title = "PDF / eBook Library (`pdf/`)" if section == "pdf" else "Structured JSON Text Library (`text/` — eBanglaLibrary & Digital Texts)"
    sec_drive = flat_folders.get(section) or PDF_DRIVE_ID
    lines = [
        f"# {sec_title}",
        "",
        f"> **Google Drive (`{section}/`)**: [Open in Google Drive](https://drive.google.com/drive/folders/{sec_drive}) | **Total Books**: **{len(sec_books):,}**",
        "",
        "| # | Category | Books | GitHub | Google Drive |",
        "|--:|---|--:|---|---|",
    ]
    for i, tc in enumerate(tree.keys(), 1):
        cnt = len(by_tc.get(tc, []))
        gh = f"[{tc}](./{quote(tc)}/)"
        gd_u = folder_drive_link(tc)
        gd = f"[Drive ↗]({gd_u})" if gd_u else "—"
        lines.append(f"| {i} | **{md_escape(tc)}** | {cnt:,} | {gh} | {gd} |")
    (base_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def render_book_table(items: list[dict]) -> list[str]:
        if not items:
            return ["*No books placed directly in this folder yet. Browse subfolders or see [Master Catalog](../../README.md).*"]
        out = [
            "| # | Book Title | Author | Publication | Format | Size | Cover | Google Drive |",
            "|--:|---|---|---|---|---:|---|---|",
        ]
        for idx, b in enumerate(items, 1):
            fmt = Path(b["name"]).suffix.lstrip(".").upper() or "FILE"
            cov_u = b.get("cover_drive_link") or (f"https://drive.google.com/file/d/{b['cover_drive_id']}/view" if b.get("cover_drive_id") else b.get("cover_url") or "")
            cov_col = f"[Cover]({cov_u})" if cov_u else "—"
            out.append(
                f"| {idx} | **{md_escape(b['name'])}** | {md_escape(b.get('author') or '-')} | "
                f"{md_escape(b.get('publication') or '-')} | `{fmt}` | {fmt_size(b.get('size', 0))} | "
                f"{cov_col} | [Open ↗]({b['link']}) |"
            )
        return out

    # Per top-category and leaf README.md
    for tc, sub in tree.items():
        tc_dir = base_dir / tc
        tc_dir.mkdir(parents=True, exist_ok=True)
        tc_items = by_tc.get(tc, [])
        tc_gd = folder_drive_link(tc)
        tc_lines = [
            f"# {tc}",
            "",
            f"> **Section**: `{section}/` | **Books**: **{len(tc_items):,}**"
            + (f" | [Google Drive Folder ↗]({tc_gd})" if tc_gd else ""),
            "",
        ]
        if isinstance(sub, dict):
            tc_lines.append("| Subcategory | Leaf Category | Books | GitHub | Google Drive |")
            tc_lines.append("|---|---|--:|---|---|")
            for mid, leaves in sub.items():
                mid_dir = tc_dir / mid
                mid_dir.mkdir(parents=True, exist_ok=True)
                mid_lines = [f"# {tc} / {mid}", "", "| Category | Books | GitHub | Google Drive |", "|---|--:|---|---|"]
                for lf in leaves:
                    lp = f"{tc}/{mid}/{lf}"
                    lf_items = by_lp.get(lp, [])
                    lf_gd = folder_drive_link(lp)
                    gd_md = f"[Drive ↗]({lf_gd})" if lf_gd else "—"
                    tc_lines.append(f"| {md_escape(mid)} | **{md_escape(lf)}** | {len(lf_items):,} | [Browse](./{quote(mid)}/{quote(lf)}/) | {gd_md} |")
                    mid_lines.append(f"| **{md_escape(lf)}** | {len(lf_items):,} | [Browse](./{quote(lf)}/) | {gd_md} |")

                    lf_dir = mid_dir / lf
                    lf_dir.mkdir(parents=True, exist_ok=True)
                    lf_head = [
                        f"# {lf}",
                        "",
                        f"> **Path**: `{section}/{lp}` | **Books**: **{len(lf_items):,}**"
                        + (f" | [Google Drive Folder ↗]({lf_gd})" if lf_gd else ""),
                        "",
                    ]
                    (lf_dir / "README.md").write_text("\n".join(lf_head + render_book_table(lf_items)) + "\n", encoding="utf-8")
                (mid_dir / "README.md").write_text("\n".join(mid_lines) + "\n", encoding="utf-8")
        else:
            tc_lines.append("| Subcategory / Class | Books | GitHub | Google Drive |")
            tc_lines.append("|---|--:|---|---|")
            for lf in sub:
                lp = f"{tc}/{lf}"
                lf_items = by_lp.get(lp, [])
                lf_gd = folder_drive_link(lp)
                gd_md = f"[Drive ↗]({lf_gd})" if lf_gd else "—"
                tc_lines.append(f"| **{md_escape(lf)}** | {len(lf_items):,} | [Browse](./{quote(lf)}/) | {gd_md} |")

                lf_dir = tc_dir / lf
                lf_dir.mkdir(parents=True, exist_ok=True)
                lf_head = [
                    f"# {lf}",
                    "",
                    f"> **Path**: `{section}/{lp}` | **Books**: **{len(lf_items):,}**"
                    + (f" | [Google Drive Folder ↗]({lf_gd})" if lf_gd else ""),
                    "",
                ]
                (lf_dir / "README.md").write_text("\n".join(lf_head + render_book_table(lf_items)) + "\n", encoding="utf-8")

        (tc_dir / "README.md").write_text("\n".join(tc_lines) + "\n", encoding="utf-8")


def write_root_docs(
    all_books: list[dict],
    tree: dict[str, list | dict],
    flat_folders: dict[str, str],
) -> None:
    pdf_books = [b for b in all_books if b["section"] == "pdf"]
    text_books = [b for b in all_books if b["section"] == "text"]
    total_size = sum(b.get("size", 0) for b in all_books)
    covers_file = DATA_DIR / "book_covers.json"
    cover_count = len(json.loads(covers_file.read_text(encoding="utf-8"))) if covers_file.exists() else 0

    authors = Counter(b["author"] for b in all_books if b.get("author"))
    pubs = Counter(b["publication"] for b in all_books if b.get("publication"))
    pdf_by_tc = Counter(b["top_category"] for b in pdf_books)
    text_by_tc = Counter(b["top_category"] for b in text_books)
    by_lp = Counter(b["leaf_path"] for b in all_books)

    nctb_rows = []
    for cls in ["Pre-Primary"] + [f"Class {i}" for i in range(1, 11)]:
        lp = f"Education and Academics/{cls}"
        cnt = by_lp.get(lp, 0)
        did = flat_folders.get(f"pdf/{lp}") or flat_folders.get(lp)
        gd = f"[Drive ↗](https://drive.google.com/drive/folders/{did})" if did else "—"
        gh = f"[Browse](./pdf/{quote('Education and Academics')}/{quote(cls)}/)"
        nctb_rows.append(f"| **{cls}** | {cnt:,} | {gh} | {gd} |")

    cat_rows = []
    for i, tc in enumerate(tree.keys(), 1):
        pcnt = pdf_by_tc.get(tc, 0)
        tcnt = text_by_tc.get(tc, 0)
        did_pdf = flat_folders.get(f"pdf/{tc}") or flat_folders.get(tc)
        did_txt = flat_folders.get(f"text/{tc}")
        gd_links = []
        if did_pdf:
            gd_links.append(f"[PDF ↗](https://drive.google.com/drive/folders/{did_pdf})")
        if did_txt:
            gd_links.append(f"[JSON ↗](https://drive.google.com/drive/folders/{did_txt})")
        cat_rows.append(
            f"| {i} | **{tc}** | {pcnt:,} | {tcnt:,} | "
            f"[pdf/{tc}/](./pdf/{quote(tc)}/) | [text/{tc}/](./text/{quote(tc)}/) | {' · '.join(gd_links) or '—'} |"
        )

    faq_md = """
## Frequently Asked Questions (FAQ) / সচরাচর জিজ্ঞাসিত প্রশ্ন

### 1. What is Bangladesh-Biggest-eBook-Library? / বাংলাদেশ-বিগেস্ট-ইবুক-লাইব্রেরি কী?
It is a clean, open-source bilingual (Bengali & English) digital archive indexing over {total:,} verified PDF/EPUB books and categorized JSON texts across 25 English-named subject folders, with direct Google Drive access and book cover metadata.

### 2. How are the folders organized (`pdf/`, `text/`, `covers/`)? / ফোল্ডারগুলো কীভাবে সাজানো হয়েছে?
- [`pdf/`](./pdf/) (`pdf/` on Google Drive): All PDF, EPUB, and MOBI eBooks across 25 clean categories (`Fiction`, `Literature`, `Religion`, `Education and Academics`, etc.).
- [`text/`](./text/) (`text/` on Google Drive): Categorized JSON eBooks (`1 .json` file per book) collected from eBanglaLibrary and structured Islamic JSON archives for fast NLP, search, and offline reading.
- [`covers/`](https://drive.google.com/drive/folders/{cov_id}): Book cover and thumbnail archive mapped in `data/book_covers.json` and referenced in `books.json`.

### 3. Where are the NCTB Class 1 to Class 10 textbooks? / প্রথম থেকে দশম শ্রেণির NCTB বই কোথায়?
Every NCTB textbook is organized individually in [`pdf/Education and Academics/`](./pdf/Education%20and%20Academics/) under `Pre-Primary` and `Class 1` through `Class 10`. Combined Class 9–10 books appear in both `Class 9` and `Class 10`.

### 4. Why were folder names changed to clean English like `Fiction` and `Literature`?
Numeric prefixes (`01_`..`25_`), trailing Bengali folder suffixes, and underscores were removed so URLs, CLI tools, GitHub paths, and Google Drive navigation remain clean and consistent (e.g., `Literature`, `Fiction`, `Bangladeshi Personalities`).

### 5. Which websites and archives are included? / কোন কোন সোর্স থেকে বই সংগ্রহ করা হয়েছে?
Curated books and covers come from our master Google Drive collections, NCTB textbooks, [`ebanglalibrary.com`](https://www.ebanglalibrary.com/) (`text/` JSONs + covers), [`kindlebangla.com`](https://www.kindlebangla.com/) (`pdf/` EPUBs/PDFs + covers), and [`bdebooks.com/bn/`](https://bdebooks.com/bn/) (`pdf/` + covers).

### 6. Are non-book files and unrelated foreign documents removed? / অপ্রয়োজনীয় ফাইল কি সরানো হয়েছে?
Yes. All non-book files (`desktop.ini`, `.apk` installers, link lists) and unrelated foreign/CIA Reading Room scans were purged from Google Drive and excluded from all catalogs and GitHub indexes.

### 7. How are books named inside Google Drive and GitHub? / বইয়ের ফাইলনেম কীভাবে ঠিক করা হয়েছে?
Website spam watermarks, domain tags, and leading index numbers are stripped, and internal PDF/EPUB metadata titles are used so books follow clean naming (`<Real Book Title> - <Author>.<ext>` or `<Book Title> - <Class> (NCTB <Year>).pdf`).

### 8. How do I download or read a book? / কীভাবে বই পড়বো বা ডাউনলোড করবো?
Browse any folder under `pdf/` or `text/`, click **Open ↗**, or open the interactive [Web Catalog Explorer]({web_base}/) or Next.js app in `visualize/` for instant search and inline Google Drive preview.

### 9. Are book covers and thumbnails available for reuse? / বইয়ের কভার ও থাম্বনেইল কীভাবে ব্যবহার করবো?
Yes! Tracked `cover_url`, `thumbnail_url`, `cover_drive_id`, and `cover_drive_link` fields live in `data/book_covers.json` and `books.json`, with image files archived under Google Drive `covers/`.

### 10. Can AI/LLM developers use the `text/` JSON corpus? / AI বা রিসার্চের জন্য কি `text/` JSON ফাইল ব্যবহার করা যাবে?
Yes. Every book in `text/<Category>/<Leaf>/` is stored as a UTF-8 JSON object containing title, author, genres, chapter URLs, cover links, and cleaned introductory text.

### 11. How do I sync or search books locally? / লোকালভাবে কীভাবে ক্যাটালগ খুঁজবো?
Filter [`books.json`](./books.json) directly with Python/jq, browse [`AUTHORS.md`](./AUTHORS.md) and [`PUBLICATIONS.md`](./PUBLICATIONS.md), or run the interactive explorer in [`visualize/`](./visualize/).

### 12. How can I report a broken link or request copyright removal?
Open an Issue on the [GitHub Repository](https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/issues) with the file ID or title for prompt verification and removal if required by rightsholders.
""".format(total=len(all_books), cov_id=COVERS_DRIVE_ID, web_base=REPO_WEB_BASE).strip()

    readme = f"""# Bangladesh-Biggest-eBook-Library — বাংলাদেশের বৃহত্তম ফ্রি বাংলা ই-বুক ও টেক্সট আর্কাইভ

[![Books](https://img.shields.io/badge/Total%20Items-{len(all_books):,}-10b981?style=for-the-badge)](./books.json)
[![PDF eBooks](https://img.shields.io/badge/PDF%20%26%20EPUBs-{len(pdf_books):,}-0ea5e9?style=for-the-badge)](./pdf/README.md)
[![JSON Texts](https://img.shields.io/badge/JSON%20Texts-{len(text_books):,}-f59e0b?style=for-the-badge)](./text/README.md)
[![Google Drive](https://img.shields.io/badge/Google%20Drive-Bangladesh--Biggest--eBook--Library-2563eb?style=for-the-badge)](https://drive.google.com/drive/folders/{ROOT_DRIVE_ID})

> **Interactive Web Explorer**: [Browse Online]({REPO_WEB_BASE}/) | **Google Drive Root**: [Open Archive ↗](https://drive.google.com/drive/folders/{ROOT_DRIVE_ID})
> **Top-Level Folders**: [`pdf/`](./pdf/README.md) ({len(pdf_books):,} eBooks) · [`text/`](./text/README.md) ({len(text_books):,} JSON Texts) · [`covers/`](https://drive.google.com/drive/folders/{COVERS_DRIVE_ID}) ({cover_count:,} Tracked Covers) · **Authors**: {len(authors):,} · **Publications**: {len(pubs):,} · **Archive Size**: {fmt_size(total_size)}

---

## NCTB Textbooks by Class (`Pre-Primary` & `Class 1` – `Class 10`)

| Class / Grade | Textbooks | GitHub Folder | Google Drive |
|---|--:|---|---|
{chr(10).join(nctb_rows)}

---

## 25 Clean Subject Categories (`pdf/` & `text/`)

| # | Category | PDF / EPUB | Text JSON | GitHub `pdf/` | GitHub `text/` | Google Drive |
|--:|---|--:|--:|---|---|---|
{chr(10).join(cat_rows)}

---

## Indexes & Visualizations

- [Author Directory (`AUTHORS.md`)](./AUTHORS.md) — {len(authors):,} authors & translators
- [Publications Directory (`PUBLICATIONS.md`)](./PUBLICATIONS.md) — {len(pubs):,} publishers & digital sources
- [Master JSON Catalog (`books.json`)](./books.json) — Complete machine-readable catalog with cover & Drive links
- [Interactive Next.js Explorer (`visualize/`)](./visualize/README.md) — Search, preview & folder browser

---

{faq_md}

<!-- Sitemap: {REPO_WEB_BASE}/sitemap.xml | Robots: {REPO_WEB_BASE}/robots.txt -->
"""
    (REPO_DIR / "README.md").write_text(readme, encoding="utf-8")

    # AUTHORS.md
    auth_lines = [
        "# Authors & Translators Directory",
        "",
        f"> **Unique Authors / Entities**: **{len(authors):,}** across **{len(all_books):,}** books.",
        "",
        "| # | Author / Translator | Books |",
        "|--:|---|--:|",
    ]
    for i, (name, cnt) in enumerate(authors.most_common(1000), 1):
        auth_lines.append(f"| {i} | {md_escape(name)} | {cnt:,} |")
    (REPO_DIR / "AUTHORS.md").write_text("\n".join(auth_lines) + "\n", encoding="utf-8")

    # PUBLICATIONS.md
    pub_lines = [
        "# Publications & Digital Sources Directory",
        "",
        f"> **Unique Publications / Archives**: **{len(pubs):,}**.",
        "",
        "| # | Publication / Source | Books |",
        "|--:|---|--:|",
    ]
    for i, (name, cnt) in enumerate(pubs.most_common(), 1):
        pub_lines.append(f"| {i} | {md_escape(name)} | {cnt:,} |")
    (REPO_DIR / "PUBLICATIONS.md").write_text("\n".join(pub_lines) + "\n", encoding="utf-8")

    # sitemap.xml with clean URLs
    today = date.today().isoformat()
    sm_urls = [
        (f"{REPO_WEB_BASE}/", "1.0", "daily"),
        (f"{REPO_WEB_BASE}/README.html", "0.9", "daily"),
        (f"{REPO_WEB_BASE}/AUTHORS.html", "0.8", "weekly"),
        (f"{REPO_WEB_BASE}/PUBLICATIONS.html", "0.8", "weekly"),
        (f"{REPO_WEB_BASE}/books.json", "0.7", "daily"),
        (f"{REPO_WEB_BASE}/pdf/", "0.9", "daily"),
        (f"{REPO_WEB_BASE}/text/", "0.9", "daily"),
    ]
    for tc in tree.keys():
        sm_urls.append((f"{REPO_WEB_BASE}/pdf/{quote(tc)}/", "0.8", "weekly"))
        sm_urls.append((f"{REPO_WEB_BASE}/text/{quote(tc)}/", "0.7", "weekly"))

    sm_xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, prio, freq in sm_urls:
        sm_xml.append(
            f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        )
    sm_xml.append("</urlset>\n")
    (REPO_DIR / "sitemap.xml").write_text("\n".join(sm_xml), encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print("Rebuilding clean GitHub repo structure (pdf/ & text/, clean English folder names)...", flush=True)

    # 1. Remove old numeric 01_..25_ folders from repo root
    removed = 0
    for entry in list(REPO_DIR.iterdir()):
        if entry.is_dir() and re.match(r"^\d{2}_", entry.name):
            shutil.rmtree(entry)
            removed += 1
    print(f"Removed {removed} legacy numeric category directories from repo root.", flush=True)

    clean_tree = build_clean_tree()
    _, flat_folders = load_folder_maps()
    all_books = collect_all_books()
    print(f"Total verified clean catalog records: {len(all_books)}", flush=True)

    # 2. Rebuild pdf/ markdown folders cleanly
    if PDF_DIR.exists():
        # remove stale leaf dirs inside pdf/ so only clean taxonomy remains
        shutil.rmtree(PDF_DIR)
    pdf_books = [b for b in all_books if b["section"] == "pdf"]
    write_category_readmes(PDF_DIR, "pdf", pdf_books, clean_tree, flat_folders)

    # 3. Rebuild text/ READMEs while preserving any collected .json book files!
    text_books = [b for b in all_books if b["section"] == "text"]
    write_category_readmes(TEXT_DIR, "text", text_books, clean_tree, flat_folders)

    # 4. Write books.json & visualize/public/books.json + taxonomy.json
    books_payload = json.dumps(all_books, ensure_ascii=False, separators=(",", ":"))
    (REPO_DIR / "books.json").write_text(books_payload, encoding="utf-8")
    VIS_PUBLIC.mkdir(parents=True, exist_ok=True)
    (VIS_PUBLIC / "books.json").write_text(books_payload, encoding="utf-8")

    tax_payload = {
        "root_drive_id": ROOT_DRIVE_ID,
        "root_drive_name": "Bangladesh-Biggest-eBook-Library",
        "pdf_drive_id": PDF_DRIVE_ID,
        "text_drive_id": TEXT_DRIVE_ID,
        "covers_drive_id": COVERS_DRIVE_ID,
        "folders": flat_folders,
        "tree": clean_tree,
    }
    (VIS_PUBLIC / "taxonomy.json").write_text(json.dumps(tax_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 5. Rebuild README.md, AUTHORS.md, PUBLICATIONS.md, sitemap.xml
    write_root_docs(all_books, clean_tree, flat_folders)
    print(f"Done! pdf_books={len(pdf_books)}, text_books={len(text_books)}, total={len(all_books)}", flush=True)


if __name__ == "__main__":
    main()
