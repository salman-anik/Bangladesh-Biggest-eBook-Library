import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CAT_DIR = ROOT / "categories"
CAT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_META = {
    "01 - Quran & Tafsir": {
        "slug": "01-quran-and-tafsir",
        "bn": "কুরআন ও তাফসির",
        "desc": "Al-Quran translations, Tafsir Ibn Kathir, Tafsir Fi Zilalil Quran, Ahkamul Quran, Qasasul Quran, and Quranic studies.",
    },
    "02 - Hadith & Sunnah": {
        "slug": "02-hadith-and-sunnah",
        "bn": "হাদীস ও সুন্নাহ",
        "desc": "Sihah Sittah, Riyadus Salehin, Mishkat, and authentic Hadith & Sunnah collections.",
    },
    "03 - Islamic Books & Aqeedah": {
        "slug": "03-islamic-books-and-aqeedah",
        "bn": "ইসলামী বই ও আকীদা",
        "desc": "Aqeedah, Fiqh, Ibadah, Dawah, Islamic Economics, Comparative Religion, and works by renowned Islamic scholars.",
    },
    "04 - Seerah, History & Biography": {
        "slug": "04-seerah-history-and-biography",
        "bn": "সীরাত, ইতিহাস ও জীবনী",
        "desc": "Seerah of Prophet Muhammad (SAW), biographies of Sahabah & Imams, Al-Bidaya wan-Nihaya, and Islamic history.",
    },
    "05 - Arabic Language & Dictionaries": {
        "slug": "05-arabic-language-and-dictionaries",
        "bn": "আরবি ভাষা ও অভিধান",
        "desc": "Arabic grammar, Madinah Arabic, and Bangla/Arabic/English dictionaries.",
    },
    "06 - Literature & Authors (Mrinal e-Library)": {
        "slug": "06-literature-and-authors",
        "bn": "সাহিত্য ও লেখক (মৃণালের ই-লাইব্রেরি)",
        "desc": "Bengali & World Literature, classics, novels, poetry, translations, and motivational books organized by author.",
    },
    "07 - Other & Archives": {
        "slug": "07-other-and-archives",
        "bn": "অন্যান্য ও আর্কাইভ",
        "desc": "Archives, companion media, and miscellaneous files.",
    },
}

def fmt_size(b: int) -> str:
    if not b:
        return "-"
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}" if unit != "B" else f"{b} B"
        b /= 1024
    return f"{b:.2f} TB"

def md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]").replace("\n", " ").strip()

def main():
    plan = json.loads((DATA_DIR / "copy_plan.json").read_text(encoding="utf-8"))
    prog_file = DATA_DIR / "catalog_progress.json"
    copied_map = json.loads(prog_file.read_text(encoding="utf-8")) if prog_file.exists() else {}

    by_cat = defaultdict(list)
    books_json = []

    for item in plan:
        src_id = item["source_id"]
        new_id = copied_map.get(src_id)
        drive_id = new_id or src_id
        link = f"https://drive.google.com/file/d/{drive_id}/view"
        status = "copied" if new_id else "source"
        rec = {
            "name": item["name"],
            "category": item["category"],
            "subfolder": item["subfolder"],
            "size": item["size"],
            "mimeType": item["mimeType"],
            "link": link,
            "status": status,
        }
        by_cat[item["category"]].append(rec)
        books_json.append(rec)

    # Write compact books.json for web UI
    (ROOT / "books.json").write_text(json.dumps(books_json, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Write category Markdown files
    total_books = len(books_json)
    total_copied = sum(1 for b in books_json if b["status"] == "copied")
    total_size = sum(b["size"] for b in books_json)

    readme_lines = [
        "# 📚 Bangladesh's Biggest E-Book Library (বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি)",
        "",
        f"A curated, categorized open digital library of **{total_books:,} e-books** ({fmt_size(total_size)}) spanning Quran & Tafsir, Hadith, Islamic Studies, Seerah & History, Arabic & Dictionaries, and Bengali/World Literature.",
        "",
        f"- **Total Books:** {total_books:,}",
        f"- **Synced to Personal Drive:** {total_copied:,} / {total_books:,}",
        "- **Interactive Searchable Web Library:** Enable GitHub Pages on `main` branch (`/` root) to browse & search all books in `index.html`.",
        "",
        "## 🗂️ Categories",
        "",
        "| Category | বাংলা | Books | Index |",
        "|---|---|---:|---|",
    ]

    for cat, meta in CATEGORY_META.items():
        items = sorted(by_cat.get(cat, []), key=lambda x: (x["subfolder"], x["name"]))
        slug = meta["slug"]
        readme_lines.append(
            f"| **{cat}** | {meta['bn']} | {len(items):,} | [Browse {cat}](categories/{slug}.md) |"
        )

        # Group by subfolder inside category markdown
        sub_groups = defaultdict(list)
        for it in items:
            sub_groups[it["subfolder"]].append(it)

        cat_lines = [
            f"# {cat} ({meta['bn']})",
            "",
            f"> {meta['desc']}",
            "",
            f"**Total Books:** {len(items):,} | [⬅️ Back to Library Home](../README.md)",
            "",
        ]
        if len(sub_groups) > 1:
            cat_lines.append("## Subcategories / Authors")
            cat_lines.append("")
            for sub in sorted(sub_groups.keys()):
                cat_lines.append(f"- **{md_escape(sub)}** ({len(sub_groups[sub])})")
            cat_lines.append("")

        cat_lines.append("## Books")
        cat_lines.append("")
        cat_lines.append("| # | Book Name | Subcategory / Author | Size | Drive Link |")
        cat_lines.append("|---:|---|---|---:|---|")
        for idx, it in enumerate(items, 1):
            cat_lines.append(
                f"| {idx} | {md_escape(it['name'])} | {md_escape(it['subfolder'])} | {fmt_size(it['size'])} | [Open in Drive]({it['link']}) |"
            )

        (CAT_DIR / f"{slug}.md").write_text("\n".join(cat_lines) + "\n", encoding="utf-8")

    readme_lines.extend([
        "",
        "## 🤖 Automated Cloud Sync (GitHub Actions)",
        "",
        "This repository includes `.github/workflows/sync-books.yml` so you can copy and organize all books into your own Google Drive **even when your PC is turned off**:",
        "",
        "1. Add a repository secret `GDRIVE_OAUTH_TOKEN_JSON` (a Google Drive OAuth2 credentials JSON with `https://www.googleapis.com/auth/drive` scope, e.g., from Google Cloud Console / OAuth Playground or `rclone`).",
        "2. Go to **Actions → Sync Books to Google Drive → Run workflow**.",
        "3. The workflow copies remaining books in batches into your organized Google Drive folders, updates `data/catalog_progress.json`, regenerates all Markdown tables and `books.json`, and commits the changes automatically.",
        "",
    ])

    (ROOT / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    print(f"Generated README.md, {len(CATEGORY_META)} category markdown files, and books.json ({total_books} books)")

if __name__ == "__main__":
    main()
