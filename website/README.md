# 🌐 Bangladesh's Biggest eBook Library — Web Search Explorer

A fast, zero-dependency bilingual web application served via GitHub Pages at [https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/](https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/) for discovering, previewing, and downloading **22,166+ free eBooks** (**316.87 GB**) mirrored directly from the 9-folder Google Drive architecture.

## Key Features

- **Mirrored 9-Folder Drive Tree Sidebar:** Navigate `Bangla Books`, `English Books`, `Education & Textbooks`, `Religion Books`, `Authors & Scholars`, `Series & Collections`, `Reference & Research`, `Review & Unclassified`, and `Library Management` with live recursive book counts and direct Google Drive folder links.
- **Book Cover Art Cards:** Displays **21,627+ curated cover thumbnails** directly from Google Drive (`Library Management / Cover Images`) with clean typographic fallback covers when an image is unavailable.
- **Instant In-Page Reader Modal (`Read`):** Preview books inside an embedded Google Drive viewer without leaving the page.
- **One-Click Direct Download (`Download`):** Download books directly from Google Drive with instant toast feedback.
- **Multilingual Search & Facets:** Instant client-side search across Bangla, English, and Arabic titles, authors, categories, subcategories, and series, plus filters for Format (`PDF`, `EPUB`, `MOBI`, `DOCX`, `DOC`, `TXT`), Language, Sort order, and Cover availability.
- **Reading List & Dark/Light Mode:** Bookmark favorite books locally (`localStorage`) and toggle between dark and light themes.

## Architecture

- [`../index.html`](../index.html) — Semantic explorer shell, SEO metadata, Drive tree sidebar, reader modal, and bookmarks drawer.
- [`../styles.css`](../styles.css) — Responsive dark/light theme styling and 2:3 cover card layout.
- [`../app.js`](../app.js) — Compact catalog loader (`books.json` v2), interactive tree builder, search/filter engine, Drive preview & download handlers.
- [`../books.json`](../books.json) — Compact columnar JSON index generated from `catalog/master_catalog.json` via [`../scripts/sync_github_architecture_and_web.py`](../scripts/sync_github_architecture_and_web.py).
