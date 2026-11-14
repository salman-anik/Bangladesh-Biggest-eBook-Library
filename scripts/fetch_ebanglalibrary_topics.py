"""Fetch LearnDash /topics/ sub-pages for short/empty eBanglaLibrary lessons and update ebanglalibrary_raw.json."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sqlite3
from pathlib import Path

import bs4
import httpx

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "eb_chapters.sqlite"
RAW_PATH = DATA_DIR / "ebanglalibrary_raw.json"

NOISE_SELECTORS = (
    "script, style, noscript, iframe, form, "
    ".wpulike, .sharedaddy, .sd-sharing-enabled, .ld-content-actions, "
    ".ld-breadcrumbs, .ld-pagination, .jp-relatedposts, .post-views, "
    "button, .bookmark-btn"
)


def init_db(conn: sqlite3.Connection) -> None:
    """Create topic storage tables if missing."""
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS lesson_topics ("
        "lesson_url TEXT PRIMARY KEY, status INTEGER, topics_json TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS topics ("
        "url TEXT PRIMARY KEY, status INTEGER, content TEXT, char_len INTEGER)"
    )
    conn.commit()


def clean_prose(soup: bs4.BeautifulSoup) -> str:
    """Extract clean article/lesson/topic prose without UI noise."""
    container = soup.select_one(".ld-tab-content") or soup.select_one(".entry-content")
    if not container:
        return ""
    for el in container.select(NOISE_SELECTORS):
        el.decompose()
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in container.get_text("\n").splitlines()]
    text = "\n\n".join(ln for ln in lines if ln and ln.lower() != "bookmark")
    return text.strip()


def extract_topic_links(soup: bs4.BeautifulSoup) -> list[dict[str, str]]:
    """Return ordered deduplicated topic {url, title} dicts scoped to main lesson content (not sidebar)."""
    seen: set[str] = set()
    items: list[dict[str, str]] = []
    root = soup.select_one(".ld-focus-content") or soup.select_one("#learndash-page-content")
    if root is not None:
        anchors = root.select(".ld-topic-list a[href]")
    else:
        anchors = [
            a
            for a in soup.select(".ld-topic-list a[href]")
            if not a.find_parent(class_=re.compile(r"sidebar|navigation|widget"))
        ]
    for a in anchors:
        href = (a.get("href") or "").strip()
        if "/topics/" not in href or "ebanglalibrary.com" not in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        title_el = a.select_one(".ld-topic-title")
        title = re.sub(r"\s+", " ", (title_el or a).get_text(" ", strip=True)).strip()
        items.append({"url": href, "title": title})
    return items


async def fetch_with_retry(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str
) -> tuple[int, str]:
    """Fetch a URL with bounded concurrency and transient retry."""
    async with sem:
        for attempt in range(4):
            try:
                resp = await client.get(url, follow_redirects=True, timeout=25.0)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                return resp.status_code, resp.text
            except Exception:
                if attempt == 3:
                    return 0, ""
                await asyncio.sleep(1.5 * (attempt + 1))
        return 0, ""


async def scan_lessons(
    lesson_urls: list[str], conn: sqlite3.Connection, concurrency: int
) -> None:
    """Fetch lesson HTML and persist discovered .ld-topic-list URLs into SQLite."""
    done_urls = {r[0] for r in conn.execute("SELECT lesson_url FROM lesson_topics WHERE status=200")}
    todo = [u for u in lesson_urls if u not in done_urls]
    print(f"Short lessons to check: {len(lesson_urls):,} | Already checked: {len(done_urls):,} | Pending: {len(todo):,}", flush=True)
    if not todo:
        return
    sem = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers, limits=httpx.Limits(max_connections=concurrency + 10)) as client:
        for i in range(0, len(todo), 200):
            batch = todo[i : i + 200]
            results = await asyncio.gather(*(fetch_with_retry(client, sem, u) for u in batch))
            rows = []
            for url, (status, html) in zip(batch, results):
                topics = extract_topic_links(bs4.BeautifulSoup(html, "lxml")) if status == 200 and html else []
                rows.append((url, status, json.dumps(topics, ensure_ascii=False)))
            conn.executemany(
                "INSERT OR REPLACE INTO lesson_topics(lesson_url, status, topics_json) VALUES (?, ?, ?)",
                rows,
            )
            conn.commit()
            print(f"  Scanned {min(i + len(batch), len(todo)):,}/{len(todo):,} lessons for topic lists", flush=True)


async def fetch_topics(
    topic_urls: list[str], conn: sqlite3.Connection, concurrency: int
) -> None:
    """Fetch topic pages and persist cleaned prose into SQLite."""
    done = {r[0] for r in conn.execute("SELECT url FROM topics WHERE status=200")}
    todo = [u for u in topic_urls if u not in done]
    print(f"Total unique topic URLs: {len(topic_urls):,} | Already fetched: {len(done):,} | Pending: {len(todo):,}", flush=True)
    if not todo:
        return
    sem = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0 Safari/537.36"}
    fetched = 0
    ok = 0
    async with httpx.AsyncClient(headers=headers, limits=httpx.Limits(max_connections=concurrency + 10)) as client:
        for i in range(0, len(todo), 250):
            batch = todo[i : i + 250]
            results = await asyncio.gather(*(fetch_with_retry(client, sem, u) for u in batch))
            rows = []
            for url, (status, html) in zip(batch, results):
                txt = clean_prose(bs4.BeautifulSoup(html, "lxml")) if status == 200 and html else ""
                rows.append((url, status, txt, len(txt)))
                fetched += 1
                if status == 200:
                    ok += 1
            conn.executemany(
                "INSERT OR REPLACE INTO topics(url, status, content, char_len) VALUES (?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            print(f"  Fetched {fetched:,}/{len(todo):,} topics | ok={ok:,}", flush=True)


def materialize_raw_json(conn: sqlite3.Connection) -> None:
    """Merge fetched topic texts back into chapters & ebanglalibrary_raw.json."""
    lesson_topics: dict[str, list[dict[str, str]]] = {}
    for lurl, tjson in conn.execute("SELECT lesson_url, topics_json FROM lesson_topics"):
        tlist = json.loads(tjson or "[]")
        if tlist:
            lesson_topics[lurl] = tlist

    topic_texts: dict[str, str] = dict(conn.execute("SELECT url, content FROM topics WHERE content != ''"))
    print(
        f"Loaded {len(lesson_topics):,} topic-bearing lessons and {len(topic_texts):,} non-empty topics.",
        flush=True,
    )

    books = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    filled_chapters = 0
    complete_books = 0
    any_text_books = 0

    for b in books:
        chs = b.get("chapters") or []
        if chs:
            for c in chs:
                curl = c.get("url") or ""
                if curl in lesson_topics:
                    titems = []
                    parts = []
                    intro_ch = (c.get("content") or "").strip()
                    for t in lesson_topics[curl]:
                        tbody = topic_texts.get(t["url"], "").strip()
                        titems.append({"url": t["url"], "title": t["title"], "content": tbody})
                        if tbody:
                            hdr = t["title"]
                            parts.append(f"{hdr}\n\n{tbody}" if hdr and not tbody.startswith(hdr) else tbody)
                    c["topics"] = titems
                    if parts:
                        merged = "\n\n".join(([intro_ch] if intro_ch and len(intro_ch) > 150 else []) + parts)
                        c["content"] = merged
                        filled_chapters += 1
            is_complete = all(bool((c.get("content") or "").strip()) for c in chs)
            has_any = bool((b.get("intro_content") or "").strip() or any((c.get("content") or "").strip() for c in chs))
        else:
            is_complete = bool((b.get("intro_content") or "").strip())
            has_any = is_complete

        b["full_text_complete"] = is_complete
        if is_complete:
            complete_books += 1
        if has_any:
            any_text_books += 1

    tmp_path = RAW_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False)
    os.replace(tmp_path, RAW_PATH)
    print(
        f"Updated ebanglalibrary_raw.json: {complete_books:,}/{len(books):,} fully complete books "
        f"({any_text_books:,} with text, {filled_chapters:,} chapter slots expanded from /topics/).",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-char-len", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=40)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-materialize", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH), timeout=60)
    init_db(conn)

    lesson_urls = [
        r[0]
        for r in conn.execute(
            "SELECT url FROM chapters WHERE char_len < ? ORDER BY url",
            (args.max_char_len,),
        )
    ]
    if args.limit > 0:
        lesson_urls = lesson_urls[: args.limit]

    asyncio.run(scan_lessons(lesson_urls, conn, args.concurrency))

    needed_topics: list[str] = []
    seen_topics: set[str] = set()
    limit_set = set(lesson_urls)
    for lurl, tjson in conn.execute("SELECT lesson_url, topics_json FROM lesson_topics"):
        if args.limit > 0 and lurl not in limit_set:
            continue
        for item in json.loads(tjson or "[]"):
            u = item["url"]
            if u not in seen_topics:
                seen_topics.add(u)
                needed_topics.append(u)

    asyncio.run(fetch_topics(needed_topics, conn, args.concurrency))

    if not args.no_materialize and args.limit == 0:
        materialize_raw_json(conn)


if __name__ == "__main__":
    main()
