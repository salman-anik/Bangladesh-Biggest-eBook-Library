# 🌐 Bangladesh Biggest eBook Library — Search Explorer Website

A lightweight, high-performance web interface for searching, filtering, and discovering 21,000+ books from the Bangladesh Biggest eBook Library.

## Features

- **Multilingual Search**: Instant search across Bangla, English, and Arabic titles, authors, and keywords.
- **Facet Browsing**: Browse by 23 canonical subjects and 110+ subcategories.
- **Language Filtering**: Filter by Bangla, English, Arabic, or view all.
- **Publication Year Range**: Filter historical, modern, and contemporary publications.
- **Direct Google Drive Integration**: Every book links directly to its verified Google Drive preview and download URL.
- **Mobile Responsive**: Built with Next.js 15, TypeScript, and Tailwind CSS.
- **Privacy & Safety**: Client-side / static index querying without exposing private documents.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Data Source**: JSON Search Index (`data/search_index.json` / `books.json`)

## Local Development

```bash
cd visualize
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

## Production Build

```bash
cd visualize
npm run build
npm run start
```
