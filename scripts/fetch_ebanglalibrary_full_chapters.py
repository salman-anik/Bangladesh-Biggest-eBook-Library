#!/usr/bin/env python3
"""
Fetch full chapter text for all multi-chapter eBanglaLibrary books (3,575 books /
50,006 chapter URLs) into a resumable SQLite store (data/eb_chapters.sqlite),
then materialize complete full-book JSONs into data/ebanglalibrary_raw.json
and update Google Drive text JSON files in place (or stage local JSONs).

Checkpoints every batch into SQLite so runs resume safely with zero duplicates.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW_PATH = DATA / "ebanglalibrary_raw.json"
DB_PATH = DATA / "eb_chapters.sqlite"

REMOVE_SELECTORS = (
    "script", "style", "noscript", ".wpulike", ".sharedaddy",
    ".ld-content-actions", ".bookmark-button", ".upb-bookmark-button",
    ".ld-focus-comments", ".jp-relatedposts", "[class*='bookmark']",
)


def extract_clean_chapter_text(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "lxml")
    box = soup.select_one("div.ld-tab-content") or soup.select_one("div.entry-content") or soup.select_one("article")
    if box is None:
        return ""
    for sel in REMOVE_SELECTORS:
        for el in box.select(sel):
            el.decompose()
    raw_txt = box.get_text("\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw_txt.splitlines()]
    cleaned = [ln for ln in lines if ln and ln.lower() not in ("bookmark", "share this:", "like loading...")]
    return unicodedata.normalize("NFC", "\n".join(cleaned))


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chapters (
            url TEXT PRIMARY KEY,
            status INTEGER NOT NULL,
            content TEXT NOT NULL,
            char_len INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


async def fetch_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    url: str,
) -> tuple[str, int, str]:
    async with sem:
        for attempt in range(4):
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    text = extract_clean_chapter_text(resp.content)
                    return url, 200, text
                if resp.status_code in (404, 410):
                    return url, resp.status_code, ""
                if resp.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                return url, resp.status_code, ""
            except Exception:
                await asyncio.sleep(1.0 * (attempt + 1))
        return url, 0, ""


async def fetch_all_chapters(urls: list[str], concurrency: int, conn: sqlite3.Connection) -> None:
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency + 8, max_keepalive_connections=concurrency)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    done = 0
    ok_200 = 0
    failed = 0
    buf: list[tuple[str, int, str, int]] = []
    t0 = time.time()

    async with httpx.AsyncClient(headers=headers, timeout=30.0, limits=limits, http2=False) as client:
        CHUNK = 1000
        for start in range(0, len(urls), CHUNK):
            batch_urls = urls[start : start + CHUNK]
            tasks = [asyncio.create_task(fetch_one(client, sem, u)) for u in batch_urls]
            for coro in asyncio.as_completed(tasks):
                url, status, content = await coro
                done += 1
                if status == 200:
                    ok_200 += 1
                    buf.append((url, status, content, len(content)))
                else:
                    failed += 1
                    if status in (404, 410):
                        buf.append((url, status, "", 0))
                if len(buf) >= 200:
                    conn.executemany(
                        "INSERT OR REPLACE INTO chapters(url, status, content, char_len) VALUES (?, ?, ?, ?)",
                        buf,
                    )
                    conn.commit()
                    buf.clear()
            if buf:
                conn.executemany(
                    "INSERT OR REPLACE INTO chapters(url, status, content, char_len) VALUES (?, ?, ?, ?)",
                    buf,
                )
                conn.commit()
                buf.clear()
            elapsed = max(0.1, time.time() - t0)
            rate = done / elapsed
            print(
                f"  Fetched {done:,}/{len(urls):,} chapters | ok={ok_200:,} | fail={failed:,} | {rate:.1f}/s",
                flush=True,
            )


def materialize_raw_json(conn: sqlite3.Connection, books: list[dict[str, Any]]) -> None:
    print("Materializing fetched chapters into data/ebanglalibrary_raw.json...", flush=True)
    cur = conn.execute("SELECT url, content FROM chapters WHERE status = 200 AND char_len > 0")
    ch_map = {row[0]: row[1] for row in cur}
    populated_ch = 0
    populated_books = 0
    for b in books:
        chs = b.get("chapters") or []
        if not chs:
            if b.get("intro_content"):
                populated_books += 1
            continue
        book_has = False
        for c in chs:
            txt = ch_map.get(c.get("url") or "", "")
            if txt:
                c["content"] = txt
                populated_ch += 1
                book_has = True
        b["full_text_complete"] = all(bool(c.get("content")) for c in chs)
        if book_has:
            populated_books += 1

    tmp = RAW_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(books, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RAW_PATH)
    print(f"Updated {RAW_PATH.name}: {populated_books:,}/{len(books):,} books with full text ({populated_ch:,} chapters filled).", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch all full chapter contents for eBanglaLibrary JSON books")
    ap.add_argument("--concurrency", type=int, default=32, help="Concurrent HTTP connections")
    ap.add_argument("--limit", type=int, default=0, help="Only fetch first N pending chapters (for benchmarking)")
    ap.add_argument("--materialize-only", action="store_true", help="Only write SQLite chapters into ebanglalibrary_raw.json")
    args = ap.parse_args()

    books = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    conn = init_db(DB_PATH)

    if args.materialize_only:
        materialize_raw_json(conn, books)
        return

    all_urls: list[str] = []
    seen: set[str] = set()
    for b in books:
        for c in b.get("chapters") or []:
            u = c.get("url") or ""
            if u and u not in seen:
                seen.add(u)
                all_urls.append(u)

    already_ok = {row[0] for row in conn.execute("SELECT url FROM chapters WHERE status = 200 AND char_len > 0")}
    pending = [u for u in all_urls if u not in already_ok]
    if args.limit > 0:
        pending = pending[: args.limit]
    print(f"Total unique chapters: {len(all_urls):,} | Already fetched: {len(already_ok):,} | Pending: {len(pending):,}", flush=True)

    if pending:
        asyncio.run(fetch_all_chapters(pending, args.concurrency, conn))

    if args.limit == 0:
        materialize_raw_json(conn, books)


if __name__ == "__main__":
    main()
