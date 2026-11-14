"""Memory-safe streaming reader for huge top-level JSON arrays (e.g. 3.74 GB ebanglalibrary_raw.json)."""

from __future__ import annotations

import codecs
import json
from pathlib import Path
from typing import Any, Iterator


def iter_json_array(path: Path, chunk_bytes: int = 8 * 1024 * 1024) -> Iterator[Any]:
    """Yield items one by one from a JSON array file without loading the full text into RAM."""
    decoder = json.JSONDecoder()
    utf8_dec = codecs.getincrementaldecoder("utf-8")()
    buf = ""
    pos = 0
    started = False

    with open(path, "rb") as f:
        while True:
            raw = f.read(chunk_bytes)
            eof = not raw
            text_chunk = utf8_dec.decode(raw, final=eof)
            if text_chunk:
                if pos > 0:
                    buf = buf[pos:]
                    pos = 0
                buf += text_chunk

            n = len(buf)
            while True:
                while pos < n and buf[pos].isspace():
                    pos += 1
                if not started:
                    if pos >= n:
                        break
                    if buf[pos] != "[":
                        raise ValueError(f"Expected '[' at start of JSON array in {path}")
                    started = True
                    pos += 1
                    continue

                while pos < n and buf[pos].isspace():
                    pos += 1
                if pos >= n:
                    break
                if buf[pos] == "]":
                    return
                if buf[pos] == ",":
                    pos += 1
                    continue

                try:
                    obj, next_pos = decoder.raw_decode(buf, pos)
                except json.JSONDecodeError:
                    if eof:
                        raise
                    break
                yield obj
                pos = next_pos

            if eof:
                break


def build_meta_json(raw_path: Path, meta_path: Path) -> int:
    """Stream raw_path -> lightweight meta_path (~2 MB) keeping text length summaries."""
    meta = []
    for b in iter_json_array(raw_path):
        chs = b.get("chapters") or []
        intro = b.get("intro_content") or ""
        non_empty_chs = sum(1 for c in chs if (c.get("content") or "").strip())
        total_chars = len(intro) + sum(len(c.get("content") or "") for c in chs)
        meta.append({
            "url": b.get("url") or "",
            "title": b.get("title") or "",
            "real_title": b.get("real_title") or "",
            "author": b.get("author") or "",
            "genres": b.get("genres") or [],
            "cover_url": b.get("cover_url") or "",
            "thumbnail_url": b.get("thumbnail_url") or "",
            "full_text_complete": bool(b.get("full_text_complete")),
            "chapter_count": len(chs),
            "filled_chapter_count": non_empty_chs,
            "total_text_chars": total_chars,
        })
    tmp = meta_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    tmp.replace(meta_path)
    return len(meta)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent / "data"
    cnt = build_meta_json(root / "ebanglalibrary_raw.json", root / "ebanglalibrary_meta.json")
    print(f"Wrote data/ebanglalibrary_meta.json ({cnt:,} books)", flush=True)
