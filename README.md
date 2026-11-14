# 📚 Bangladesh's Biggest E-Book Library (বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি)

A curated, categorized open digital library of **6,364 e-books** (71.4 GB) spanning Quran & Tafsir, Hadith, Islamic Studies, Seerah & History, Arabic & Dictionaries, and Bengali/World Literature.

- **Total Books:** 6,364
- **Synced to Personal Drive:** 0 / 6,364
- **Interactive Searchable Web Library:** Enable GitHub Pages on `main` branch (`/` root) to browse & search all books in `index.html`.

## 🗂️ Categories

| Category | বাংলা | Books | Index |
|---|---|---:|---|
| **01 - Quran & Tafsir** | কুরআন ও তাফসির | 388 | [Browse 01 - Quran & Tafsir](categories/01-quran-and-tafsir.md) |
| **02 - Hadith & Sunnah** | হাদীস ও সুন্নাহ | 339 | [Browse 02 - Hadith & Sunnah](categories/02-hadith-and-sunnah.md) |
| **03 - Islamic Books & Aqeedah** | ইসলামী বই ও আকীদা | 2,102 | [Browse 03 - Islamic Books & Aqeedah](categories/03-islamic-books-and-aqeedah.md) |
| **04 - Seerah, History & Biography** | সীরাত, ইতিহাস ও জীবনী | 275 | [Browse 04 - Seerah, History & Biography](categories/04-seerah-history-and-biography.md) |
| **05 - Arabic Language & Dictionaries** | আরবি ভাষা ও অভিধান | 94 | [Browse 05 - Arabic Language & Dictionaries](categories/05-arabic-language-and-dictionaries.md) |
| **06 - Literature & Authors (Mrinal e-Library)** | সাহিত্য ও লেখক (মৃণালের ই-লাইব্রেরি) | 3,118 | [Browse 06 - Literature & Authors (Mrinal e-Library)](categories/06-literature-and-authors.md) |
| **07 - Other & Archives** | অন্যান্য ও আর্কাইভ | 48 | [Browse 07 - Other & Archives](categories/07-other-and-archives.md) |

## 🤖 Automated Cloud Sync (GitHub Actions)

This repository includes `.github/workflows/sync-books.yml` so you can copy and organize all books into your own Google Drive **even when your PC is turned off**:

1. Add a repository secret `GDRIVE_OAUTH_TOKEN_JSON` (a Google Drive OAuth2 credentials JSON with `https://www.googleapis.com/auth/drive` scope, e.g., from Google Cloud Console / OAuth Playground or `rclone`).
2. Go to **Actions → Sync Books to Google Drive → Run workflow**.
3. The workflow copies remaining books in batches into your organized Google Drive folders, updates `data/catalog_progress.json`, regenerates all Markdown tables and `books.json`, and commits the changes automatically.
