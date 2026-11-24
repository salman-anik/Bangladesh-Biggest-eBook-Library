#!/usr/bin/env python3
"""Collect author biographies and portraits for Authors & Scholars from Wikipedia.

Uses MediaWiki batch `action=query` lookups (25 titles per call) with polite
HTTP 429 retry/backoff to avoid rate-limiting, then falls back to MediaWiki
search for remaining authors. Writes rich metadata to
`Library Management/Author Details/`, compact bundled assets to
`App/assets/author_details.json` and `visualize/public/author_details.json`, and
merges newly discovered portraits into `App/assets/author_photos.json` without
overwriting existing Google Drive photo IDs.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = (
    "AnaBookLibraryBot/1.0 "
    "(https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library; "
    "salmananik.bd@gmail.com)"
)
REQUEST_TIMEOUT_SEC = 10
BATCH_SIZE = 25

HONORIFIC_RE = re.compile(
    r"^(?:ড\.?|অধ্যাপক|মাওলানা|আল্লামা|মুফতি|শায়খ|শায়খ|ইমাম|হযরত|স্বামী|"
    r"Dr\.?|Prof\.?|Professor|Md\.?|Mr\.?|Mrs\.?|Ms\.?|Sir|Sheikh|Imam|Maulana)\s+",
    re.IGNORECASE,
)
PAREN_RE = re.compile(r"\s*\([^)]*\)")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[।.!?])\s+")

AUTHOR_HINT_KEYWORDS = (
    "writer",
    "author",
    "novelist",
    "poet",
    "essayist",
    "dramatist",
    "playwright",
    "historian",
    "philosopher",
    "scholar",
    "journalist",
    "translator",
    "scientist",
    "polymath",
    "thinker",
    "physicist",
    "lyricist",
    "composer",
    "literature",
    "bengali",
    "bangladeshi",
    "লেখক",
    "লেখিকা",
    "ঔপন্যাসিক",
    "কবি",
    "সাহিত্যিক",
    "প্রাবন্ধিক",
    "নাট্যকার",
    "গল্পকার",
    "কথাসাহিত্যিক",
    "ছড়াকার",
    "গবেষক",
    "অধ্যাপক",
    "শিক্ষাবিদ",
    "অনুবাদক",
    "চিন্তাবিদ",
    "সাংবাদিক",
    "ইসলামী",
    "ইসলামি",
    "পণ্ডিত",
    "দাঈ",
    "মুফতি",
    "আলেম",
    "দার্শনিক",
    "বৈজ্ঞানিক",
    "বিজ্ঞানী",
    "ইতিহাসবিদ",
    "উপন্যাস",
    "কাব্যগ্রন্থ",
    "সাহিত্য",
    "রচনা",
    "শিশুসাহিত্যিক",
)

WRONG_PERSON_KEYWORDS = (
    "মুঘল সম্রাট",
    "রাজনীতিবিদ",
    "cricketer",
    "footballer",
    "politician",
    "মুক্তিযোদ্ধা",
    "parliament",
    "উপজেলা",
    "চলচ্চিত্র অভিনেত",
    "ক্রিকেটার",
    "ফুটবলার",
)


def http_get_json(url: str) -> dict[str, Any] | None:
    delay = 1.0
    for attempt in range(4):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                return data if isinstance(data, dict) else None
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 502, 503, 504) and attempt < 3:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
                time.sleep(min(wait, 12.0))
                delay *= 2
                continue
            return None
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            if attempt < 2:
                time.sleep(delay)
                delay *= 2
                continue
            return None
    return None


def strip_noise(name: str) -> str:
    s = unicodedata.normalize("NFC", name or "")
    s = PAREN_RE.sub("", s).strip()
    return re.sub(r"\s+", " ", s)


def build_query_variants(raw_name: str) -> list[str]:
    nfc_raw = unicodedata.normalize("NFC", raw_name or "").strip()
    base = strip_noise(nfc_raw)
    variants: list[str] = []

    no_honorific = base
    for _ in range(3):
        next_val = HONORIFIC_RE.sub("", no_honorific).strip()
        if next_val == no_honorific:
            break
        no_honorific = next_val

    for candidate in (nfc_raw, base, no_honorific):
        if candidate and candidate not in variants:
            variants.append(candidate)

    # Also add Bengali precomposed vs decomposed `য়` variant just in case
    for v in list(variants):
        alt = v.replace("\u09df", "\u09af\u09bc")
        if alt not in variants:
            variants.append(alt)

    return variants


def is_latin_heavy(text: str) -> bool:
    latin = sum(1 for ch in text if "A" <= ch <= "Z" or "a" <= ch <= "z")
    bengali = sum(1 for ch in text if "\u0980" <= ch <= "\u09ff")
    return latin > bengali


def trim_bio(extract: str, max_chars: int = 460) -> str:
    text = re.sub(r"\s+", " ", (extract or "").strip())
    if not text:
        return ""
    sentences = SENTENCE_SPLIT_RE.split(text)
    selected: list[str] = []
    total = 0
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(selected) >= 4:
            break
        if selected and total + len(sent) + 1 > max_chars:
            break
        selected.append(sent)
        total += len(sent) + 1
    out = " ".join(selected).strip() if selected else text[:max_chars].rstrip()
    if len(out) > max_chars:
        cut = out[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:-")
        out = cut + "…"
    return out


def normalize_match_tokens(text: str) -> list[str]:
    cleaned = strip_noise(text).lower()
    cleaned = HONORIFIC_RE.sub("", cleaned).strip()
    cleaned = re.sub(r"[.\-_'\"’“”,|/&()]", " ", cleaned)
    return [t for t in cleaned.split() if len(t) >= 2]


def batch_fetch_pages(lang: str, titles: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch Wikipedia page metadata for up to BATCH_SIZE titles at once."""
    results: dict[str, dict[str, Any]] = {}
    unique_titles = list(dict.fromkeys(t.strip() for t in titles if t.strip()))
    for start in range(0, len(unique_titles), BATCH_SIZE):
        chunk = unique_titles[start : start + BATCH_SIZE]
        params = urllib.parse.urlencode(
            {
                "action": "query",
                "prop": "extracts|pageimages|description|info|pageprops",
                "exintro": "1",
                "explaintext": "1",
                "exsentences": "4",
                "piprop": "thumbnail",
                "pithumbsize": "240",
                "inprop": "url",
                "ppprop": "disambiguation",
                "redirects": "1",
                "titles": "|".join(chunk),
                "format": "json",
            }
        )
        url = f"https://{lang}.wikipedia.org/w/api.php?{params}"
        data = http_get_json(url)
        time.sleep(0.18)
        if not data:
            continue

        query_blk = data.get("query", {}) or {}
        norm_map = {n["from"]: n["to"] for n in query_blk.get("normalized", [])}
        redir_map = {r["from"]: r["to"] for r in query_blk.get("redirects", [])}

        pages_by_title: dict[str, dict[str, Any]] = {}
        for page in (query_blk.get("pages") or {}).values():
            if not isinstance(page, dict) or "missing" in page:
                continue
            if "disambiguation" in (page.get("pageprops") or {}):
                continue
            pages_by_title[page.get("title", "")] = page

        for orig in chunk:
            cur = norm_map.get(orig, orig)
            cur = redir_map.get(cur, cur)
            # handle two-hop redirects if any
            cur = redir_map.get(cur, cur)
            if cur in pages_by_title:
                results[orig] = pages_by_title[cur]
    return results


def search_wiki_titles(lang: str, query: str) -> list[str]:
    q = urllib.parse.quote(query)
    url = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={q}&srlimit=5&utf8=1&format=json"
    )
    data = http_get_json(url)
    time.sleep(0.15)
    if not data:
        return []
    hits = data.get("query", {}).get("search", []) or []
    return [h["title"] for h in hits if isinstance(h, dict) and h.get("title")]


def looks_like_author_page(query_name: str, page: dict[str, Any], exact: bool) -> bool:
    title = (page.get("title") or "").strip()
    desc = (page.get("description") or "").lower()
    extract = (page.get("extract") or "").strip()
    if not extract:
        return False

    combined = f"{title.lower()} {desc} {extract[:400].lower()}"
    strict_lit_keywords = (
        "writer",
        "author",
        "novelist",
        "poet",
        "essayist",
        "dramatist",
        "playwright",
        "scholar",
        "translator",
        "লেখক",
        "লেখিকা",
        "ঔপন্যাসিক",
        "কবি",
        "সাহিত্যিক",
        "প্রাবন্ধিক",
        "নাট্যকার",
        "গল্পকার",
        "কথাসাহিত্যিক",
        "অনুবাদক",
        "ছড়াকার",
        "শিশুসাহিত্যিক",
        "ইসলামী",
        "ইসলামি",
        "আলেম",
        "মুফতি",
    )
    has_strict_lit = any(k in combined for k in strict_lit_keywords)
    has_wrong_person = any(k in combined for k in WRONG_PERSON_KEYWORDS)
    if has_wrong_person and not has_strict_lit:
        return False

    has_hint = any(k in combined for k in AUTHOR_HINT_KEYWORDS)
    q_tokens = normalize_match_tokens(query_name)
    t_tokens = set(normalize_match_tokens(title))
    overlap = sum(1 for t in q_tokens if t in t_tokens or any(t in tt for tt in t_tokens))

    if exact and (overlap >= 1 or has_hint):
        return True
    if len(q_tokens) >= 2:
        # Never match on just a shared surname (e.g. "গৌতম রায়" -> "সত্যজিৎ রায়")
        required = 2 if len(q_tokens) == 2 else max(2, len(q_tokens) - 1)
        tokens_in_text = sum(1 for t in q_tokens if t in combined)
        if has_strict_lit and overlap >= required and tokens_in_text >= required:
            return True
        if has_hint and overlap >= len(q_tokens):
            return True
        return False
    if has_strict_lit and overlap >= 1:
        return True
    if has_hint and overlap >= 1:
        return True
    return False


def parse_page_payload(lang: str, page: dict[str, Any]) -> dict[str, Any]:
    short_desc = (page.get("description") or "").strip()
    bio = trim_bio(page.get("extract") or "")
    wiki_url = (page.get("fullurl") or "").strip()
    thumb = page.get("thumbnail", {}) or {}
    photo_url = (thumb.get("source") or "").strip()
    return {
        "shortDesc": short_desc,
        "bio": bio,
        "wikiUrl": wiki_url,
        "photoUrl": photo_url,
        "source": f"{lang}wiki",
    }


def extract_authors_from_catalog(books_path: Path) -> list[dict[str, Any]]:
    data = json.loads(books_path.read_text(encoding="utf-8"))
    cats: list[str] = data.get("cats", [])
    subs: list[str] = data.get("subs", [])
    if "Authors & Scholars" not in cats:
        raise ValueError("'Authors & Scholars' category not found in books.json")
    auth_cat_idx = cats.index("Authors & Scholars")

    acc_map: dict[tuple[str, str], dict[str, Any]] = {}
    for row in data.get("books", []):
        if row[3] != auth_cat_idx:
            continue
        sub_str = subs[row[4]] if row[4] < len(subs) else ""
        if not sub_str:
            continue
        parts = [p for p in sub_str.split("/") if p]
        if len(parts) < 2:
            continue

        top_group = parts[0]
        subfolder = ""
        if top_group in ("Bangladeshi Authors", "International Authors"):
            group = top_group
            author_name = parts[1]
            if len(parts) >= 3:
                subfolder = parts[2]
        elif top_group == "Islamic Scholars":
            group = "Islamic Scholars"
            if len(parts) >= 3:
                author_name = parts[2]
                if len(parts) >= 4:
                    subfolder = parts[3]
            else:
                author_name = parts[1]
        else:
            continue

        key = (group, author_name)
        if key not in acc_map:
            acc_map[key] = {
                "name": author_name,
                "group": group,
                "bookCount": 0,
                "subfolders": set(),
            }
        acc_map[key]["bookCount"] += 1
        if subfolder:
            acc_map[key]["subfolders"].add(subfolder)

    authors: list[dict[str, Any]] = []
    for item in acc_map.values():
        authors.append(
            {
                "name": item["name"],
                "group": item["group"],
                "bookCount": item["bookCount"],
                "subfolders": sorted(item["subfolders"]),
            }
        )
    authors.sort(key=lambda x: x["name"].lower())
    return authors


def build_markdown_index(records: list[dict[str, Any]], generated_at: str) -> str:
    wiki_count = sum(1 for r in records if r["source"] != "catalog")
    photo_count = sum(1 for r in records if r["photoUrl"])
    lines = [
        "# Author Profiles & Details Directory",
        "",
        "[🏠 Library Home](../../README.md) / [Library Management](../README.md) / **Author Details**",
        "",
        f"- **Generated (UTC):** `{generated_at}`",
        f"- **Total Authors Indexed:** `{len(records)}`",
        f"- **Wikipedia Biographies Matched:** `{wiki_count}`",
        f"- **Wikipedia Portraits Found:** `{photo_count}`",
        "- **Machine-Readable Data:** [author_details.json](author_details.json)",
        "",
        "| Author | Group | Books | Source | Short Description | Reference |",
        "|---|---|---:|---|---|---|",
    ]
    for r in records:
        desc = (r["shortDesc"] or "-").replace("|", "\\|")
        ref = f"[Wikipedia]({r['wikiUrl']})" if r["wikiUrl"] else "Catalog Archive"
        lines.append(
            f"| {r['name'].replace('|', '\\|')} | {r['group']} | {r['bookCount']} | `{r['source']}` | {desc} | {ref} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    repo_dir = Path(__file__).resolve().parent.parent
    books_path = repo_dir / "books.json"
    if not books_path.exists():
        print(f"ERROR: books.json not found at {books_path}", file=sys.stderr)
        return 1

    raw_authors = extract_authors_from_catalog(books_path)
    print(f"Extracted {len(raw_authors)} unique authors from books.json")

    variants_by_name = {a["name"]: build_query_variants(a["name"]) for a in raw_authors}
    bn_titles: list[str] = []
    en_titles: list[str] = []
    for a in raw_authors:
        vs = variants_by_name[a["name"]]
        bn_titles.extend(vs)
        if is_latin_heavy(a["name"]):
            en_titles.extend(vs)

    print(f"Pass 1: Batch querying bn.wikipedia ({len(bn_titles)} title variants)...")
    bn_pages = batch_fetch_pages("bn", bn_titles)
    print(f"Pass 1: Batch querying en.wikipedia ({len(en_titles)} title variants)...")
    en_pages = batch_fetch_pages("en", en_titles) if en_titles else {}

    matched_by_idx: dict[int, dict[str, Any]] = {}
    unmatched_indices: list[int] = []

    for idx, entry in enumerate(raw_authors):
        name = entry["name"]
        langs = ["en", "bn"] if is_latin_heavy(name) else ["bn", "en"]
        found: dict[str, Any] | None = None
        for lang in langs:
            pool = bn_pages if lang == "bn" else en_pages
            for v in variants_by_name[name]:
                page = pool.get(v)
                if page and looks_like_author_page(name, page, exact=True):
                    found = parse_page_payload(lang, page)
                    break
            if found:
                break
        if found:
            matched_by_idx[idx] = found
        else:
            unmatched_indices.append(idx)

    print(
        f"Pass 1 complete: matched {len(matched_by_idx)}/{len(raw_authors)}. "
        f"Pass 2: Search fallback for {len(unmatched_indices)} remaining authors..."
    )

    # Pass 2: Search Wikipedia for unmatched authors (including "(সাহিত্যিক)" / "(লেখক)" qualifiers)
    candidate_hits_bn: dict[int, list[str]] = {}
    candidate_hits_en: dict[int, list[str]] = {}
    all_search_titles_bn: list[str] = []
    all_search_titles_en: list[str] = []

    for idx in unmatched_indices:
        name = raw_authors[idx]["name"]
        v0 = variants_by_name[name][0]
        if is_latin_heavy(name):
            hits_en = search_wiki_titles("en", v0)
            if hits_en:
                candidate_hits_en[idx] = hits_en
                all_search_titles_en.extend(hits_en)
            hits_bn = search_wiki_titles("bn", v0)
            if hits_bn:
                candidate_hits_bn[idx] = hits_bn
                all_search_titles_bn.extend(hits_bn)
        else:
            hits_bn = search_wiki_titles("bn", f"{v0} সাহিত্যিক")
            hits_bn_plain = search_wiki_titles("bn", v0)
            merged_bn = list(dict.fromkeys(hits_bn + hits_bn_plain))[:5]
            if merged_bn:
                candidate_hits_bn[idx] = merged_bn
                all_search_titles_bn.extend(merged_bn)

    search_pages_bn = batch_fetch_pages("bn", all_search_titles_bn) if all_search_titles_bn else {}
    search_pages_en = batch_fetch_pages("en", all_search_titles_en) if all_search_titles_en else {}

    for idx in unmatched_indices:
        name = raw_authors[idx]["name"]
        langs = ["en", "bn"] if is_latin_heavy(name) else ["bn", "en"]
        for lang in langs:
            titles = candidate_hits_bn.get(idx, []) if lang == "bn" else candidate_hits_en.get(idx, [])
            pool = search_pages_bn if lang == "bn" else search_pages_en
            for t in titles:
                page = pool.get(t)
                if page and looks_like_author_page(name, page, exact=False):
                    matched_by_idx[idx] = parse_page_payload(lang, page)
                    break
            if idx in matched_by_idx:
                break

    enriched: list[dict[str, Any]] = []
    for idx, entry in enumerate(raw_authors):
        name = entry["name"]
        group = entry["group"]
        book_count = entry["bookCount"]
        subfolders = entry["subfolders"]
        wiki = matched_by_idx.get(idx)

        if wiki:
            short_desc = wiki["shortDesc"] or group
            bio = wiki["bio"]
            wiki_url = wiki["wikiUrl"]
            photo_url = wiki["photoUrl"]
            source = wiki["source"]
        else:
            short_desc = f"{group} · {book_count} {('book' if book_count == 1 else 'books')}"
            bio = (
                f"Works by {name} preserved in the Bangladesh's Biggest eBook Library "
                f"under {group}. Browse all {book_count} digitized "
                f"{'book' if book_count == 1 else 'books'}"
                + (f" across {len(subfolders)} sections." if subfolders else " in this archive.")
            )
            wiki_url = ""
            photo_url = ""
            source = "catalog"

        enriched.append(
            {
                "name": name,
                "group": group,
                "bookCount": book_count,
                "subfolders": subfolders,
                "shortDesc": short_desc,
                "bio": bio,
                "wikiUrl": wiki_url,
                "photoUrl": photo_url,
                "source": source,
            }
        )

    enriched.sort(key=lambda x: x["name"].lower())
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    wiki_count = sum(1 for r in enriched if r["source"] != "catalog")
    photo_count = sum(1 for r in enriched if r["photoUrl"])

    # 1. Library Management/Author Details outputs
    details_dir = repo_dir / "Library Management" / "Author Details"
    details_dir.mkdir(parents=True, exist_ok=True)
    rich_payload = {
        "generated_at": generated_at,
        "total_authors": len(enriched),
        "wiki_matched": wiki_count,
        "photo_matched": photo_count,
        "authors": enriched,
    }
    (details_dir / "author_details.json").write_text(
        json.dumps(rich_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (details_dir / "AUTHOR_DETAILS_INDEX.md").write_text(
        build_markdown_index(enriched, generated_at),
        encoding="utf-8",
    )

    # 2. Compact map for App/assets/author_details.json & visualize/public/author_details.json
    compact_map: dict[str, dict[str, str]] = {}
    for r in enriched:
        norm_key = r["name"].strip().lower()
        if not norm_key:
            continue
        compact_map[norm_key] = {
            "name": r["name"],
            "group": r["group"],
            "shortDesc": r["shortDesc"],
            "bio": r["bio"],
            "wikiUrl": r["wikiUrl"],
        }

    compact_json = json.dumps(compact_map, ensure_ascii=False, indent=2) + "\n"
    (repo_dir / "App" / "assets" / "author_details.json").write_text(
        compact_json, encoding="utf-8"
    )
    vis_details_path = repo_dir / "visualize" / "public" / "author_details.json"
    if vis_details_path.parent.exists():
        vis_details_path.write_text(compact_json, encoding="utf-8")

    # 3. Merge newly discovered Wikipedia photo URLs into App/assets/author_photos.json
    # without overwriting any existing Drive photo IDs.
    photos_path = repo_dir / "App" / "assets" / "author_photos.json"
    existing_photos: dict[str, str] = {}
    if photos_path.exists():
        existing_photos = json.loads(photos_path.read_text(encoding="utf-8"))

    added_photos = 0
    for r in enriched:
        photo_url = r["photoUrl"]
        if not photo_url:
            continue
        norm_key = r["name"].strip().lower()
        if norm_key not in existing_photos:
            existing_photos[norm_key] = photo_url
            added_photos += 1

    sorted_photos = dict(sorted(existing_photos.items(), key=lambda kv: kv[0]))
    photos_path.write_text(
        json.dumps(sorted_photos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Done! Total={len(enriched)}, WikiMatched={wiki_count}, "
        f"WikiPhotos={photo_count}, NewPhotosAdded={added_photos}, "
        f"TotalPhotos={len(sorted_photos)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
