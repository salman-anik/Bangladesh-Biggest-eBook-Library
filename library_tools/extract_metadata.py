"""READ-ONLY validation + embedded-metadata extraction for every eBook in the audit.

Input : out/audit/inventory_full.csv (from audit_drive.py)
        repo data files with original source IDs (for name recovery)
Output: out/meta/file_meta.jsonl     one record per eBook: real type, validity, embedded title/author/...
        out/meta/source_lookup.jsonl original source files (name, md5) for name recovery
"""
from __future__ import annotations

import concurrent.futures as cf
import csv
import io
import json
import os
import re
import sys
import threading
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_api as d  # noqa: E402

AUDIT = Path(os.environ.get("AUDIT_OUT", "out/audit"))
OUT = Path(os.environ.get("META_OUT", "out/meta"))
DATA = Path(os.environ.get("REPO_DATA", "data"))
WORKERS = int(os.environ.get("WORKERS", "16"))
FULL_DL_LIMIT = 60 * 1024 * 1024  # download whole EPUB/DOCX/MOBI up to this size

_wlock = threading.Lock()


def pdf_string(raw: bytes) -> str:
    raw = raw.strip()
    try:
        if raw.startswith(b"<"):
            b = bytes.fromhex(re.sub(rb"[^0-9A-Fa-f]", b"", raw[1:-1]).decode())
        else:
            s = raw[1:-1]
            out, i = bytearray(), 0
            esc = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f", b"(": b"(", b")": b")", b"\\": b"\\"}
            while i < len(s):
                c = s[i:i + 1]
                if c == b"\\" and i + 1 < len(s):
                    n = s[i + 1:i + 2]
                    if n in esc:
                        out += esc[n]; i += 2; continue
                    m = re.match(rb"[0-7]{1,3}", s[i + 1:i + 4])
                    if m:
                        out.append(int(m.group(), 8) & 0xFF); i += 1 + len(m.group()); continue
                    i += 1; continue
                out += c; i += 1
            b = bytes(out)
        if b.startswith(b"\xfe\xff"):
            return b[2:].decode("utf-16-be", "replace").strip("\x00 ")
        if b.startswith(b"\xef\xbb\xbf"):
            return b[3:].decode("utf-8", "replace").strip()
        try:
            return b.decode("utf-8").strip()
        except UnicodeDecodeError:
            return b.decode("latin-1").strip()
    except Exception:
        return ""


PDF_KEYS = [b"Title", b"Author", b"Subject", b"Keywords", b"Creator", b"Producer", b"CreationDate"]
STR = rb"(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>)"


def pdf_meta(blob: bytes) -> dict:
    meta = {}
    for k in PDF_KEYS:
        for m in re.finditer(rb"/" + k + rb"\s*" + STR, blob):
            v = pdf_string(m.group(1))
            if v and not meta.get(k.decode().lower()):
                meta[k.decode().lower()] = v[:300]
    # XMP
    for tag, key in (
        (rb"dc:title", "xmp_title"),
        (rb"dc:creator", "xmp_creator"),
        (rb"dc:language", "xmp_language"),
        (rb"dc:publisher", "xmp_publisher"),
    ):
        m = re.search(tag + rb"\b[^>]*>.*?<rdf:li[^>]*>(.*?)</rdf:li>", blob, re.S)
        if not m:
            m = re.search(tag + rb"\b[^>]*>([^<]+)</" + tag + rb">", blob, re.S)
        if m:
            try:
                val = m.group(1).decode("utf-8", "replace").strip()[:300]
                if val:
                    meta[key] = val
            except Exception:
                pass
    m = re.findall(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", blob)
    if m:
        meta["pages"] = max(int(x) for x in m)
    if b"/Encrypt" in blob:
        meta["encrypted"] = True
    return meta


def epub_meta(data: bytes) -> dict:
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    opf = None
    if "META-INF/container.xml" in names:
        m = re.search(rb'full-path="([^"]+)"', z.read("META-INF/container.xml"))
        if m:
            opf = m.group(1).decode()
    if not opf:
        opf = next((n for n in names if n.endswith(".opf")), None)
    if not opf:
        return {"epub_error": "no_opf"}
    root = ET.fromstring(z.read(opf))
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    meta = {}
    for f in ("title", "creator", "language", "publisher", "date", "contributor", "subject", "description", "identifier"):
        vals = [(e.text or "").strip() for e in root.iter("{http://purl.org/dc/elements/1.1/}" + f) if (e.text or "").strip()]
        if vals:
            meta[f] = vals[0][:300] if f != "subject" else "; ".join(vals)[:300]
            if f == "creator" and len(vals) > 1:
                meta["creators"] = vals[:5]
    meta["spine_items"] = sum(1 for _ in root.iter("{http://www.idpf.org/2007/opf}itemref"))
    return meta


def docx_meta(data: bytes) -> dict:
    z = zipfile.ZipFile(io.BytesIO(data))
    if "docProps/core.xml" not in z.namelist():
        return {}
    x = z.read("docProps/core.xml").decode("utf-8", "replace")
    meta = {}
    for tag, key in (("dc:title", "title"), ("dc:creator", "creator"), ("dc:language", "language")):
        m = re.search(f"<{tag}[^>]*>(.*?)</{tag}>", x, re.S)
        if m and m.group(1).strip():
            meta[key] = m.group(1).strip()[:300]
    return meta


def mobi_meta(data: bytes) -> dict:
    meta = {}
    if data[60:68] not in (b"BOOKMOBI", b"TEXtREAd"):
        return {"mobi_error": "bad_magic"}
    rec0 = int.from_bytes(data[78:82], "big")
    r = data[rec0:]
    if r[16:20] != b"MOBI":
        return meta
    hlen = int.from_bytes(r[20:24], "big")
    enc = int.from_bytes(r[28:32], "big")
    codec = "utf-8" if enc == 65001 else "cp1252"
    off, ln = int.from_bytes(r[84:88], "big"), int.from_bytes(r[88:92], "big")
    meta["title"] = r[off:off + ln].decode(codec, "replace")[:300]
    if int.from_bytes(r[128:132], "big") & 0x40:
        e = r[16 + hlen:]
        if e[:4] == b"EXTH":
            cnt, p = int.from_bytes(e[8:12], "big"), 12
            for _ in range(cnt):
                t, l = int.from_bytes(e[p:p + 4], "big"), int.from_bytes(e[p + 4:p + 8], "big")
                v = e[p + 8:p + l].decode(codec, "replace")
                key = {100: "creator", 101: "publisher", 106: "date", 503: "title_full", 524: "language", 105: "subject"}.get(t)
                if key and key not in meta:
                    meta[key] = v[:300]
                p += l
    return meta


def sniff(head: bytes) -> str:
    if head.startswith(b"%PDF") or b"%PDF-" in head[:1024]:
        return "pdf"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head[60:68] in (b"BOOKMOBI", b"TEXtREAd"):
        return "mobi"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "ole_doc"
    if head.startswith(b"AT&TFORM"):
        return "djvu"
    if head.startswith(b"Rar!"):
        return "rar"
    if head.startswith(b"{\\rtf"):
        return "rtf"
    low = head[:600].lower()
    if b"<!doctype html" in low or b"<html" in low:
        return "html"
    try:
        head[:2048].decode("utf-8")
        return "text"
    except UnicodeDecodeError:
        return "unknown"


def process(r: dict) -> dict:
    fid, size, ext = r["id"], int(r["size"]), r["ext"]
    rec = {"id": fid, "ext": ext, "size": size}
    try:
        if size == 0:
            rec.update(real_type="empty", valid=False)
            return rec
        need_full = (ext in ("epub", "docx", "mobi", "azw3", "azw", "txt") and size <= FULL_DL_LIMIT) or size <= 65536
        if need_full:
            data = d.download_full(fid) if size > 0 else b""
            head = data[:65536]
        else:
            data = None
            head = d.download_range(fid, 0, 65535)
        t = sniff(head)
        rec["real_type"] = t
        if t == "html":
            txt = (data or head).decode("utf-8", "replace")
            ttl = re.search(r"<title>(.*?)</title>", txt, re.S | re.I)
            rec["html_title"] = ttl.group(1).strip()[:200] if ttl else ""
            urls = re.findall(r"""(?:content=["']\d+;\s*url=|href=["']|window\.location(?:\.href)?\s*=\s*["'])(https?://[^"'\s>]+)""", txt, re.I)
            urls += re.findall(r"https?://(?:www\.)?(?:mediafire\.com|drive\.google\.com|docs\.google\.com|archive\.org|islamicbook\.ws|dropbox\.com|mega\.nz)[^\s\"'<>]+", txt)
            seen = []
            for u in urls:
                if u not in seen and "justpaste.it/static" not in u:
                    seen.append(u)
            rec["redirect_urls"] = seen[:5]
            rec["valid"] = False
            return rec
        if t == "pdf":
            blob = head
            if data is None and size > 65536:
                blob += d.download_range(fid, max(0, size - 262144), size - 1)
            elif data is not None:
                blob = data
            m = pdf_meta(blob)
            rec.update(m)
            rec["valid"] = (b"%%EOF" in blob[-2048:]) if data is not None or size > 65536 else True
            if not rec["valid"]:
                rec["warn"] = "no_eof_marker"
                rec["valid"] = True  # tail-truncated reads can miss it; treat as soft warning
            return rec
        if t == "zip":
            if data is None:
                rec.update(valid=True, warn="zip_not_inspected_large")
                return rec
            try:
                if ext == "epub" or b"mimetypeapplication/epub+zip" in head[:100]:
                    rec.update(epub_meta(data))
                elif ext == "docx":
                    rec.update(docx_meta(data))
                rec["valid"] = zipfile.ZipFile(io.BytesIO(data)).testzip() is None
            except Exception as e:
                rec.update(valid=False, error=f"zip:{e.__class__.__name__}")
            return rec
        if t == "mobi":
            rec.update(mobi_meta(data or head))
            rec["valid"] = True
            return rec
        rec["valid"] = t in ("ole_doc", "djvu", "rtf", "text")
        return rec
    except Exception as e:  # noqa: BLE001
        rec.update(error=str(e)[:300], valid=None)
        return rec


def source_ids() -> dict[str, dict]:
    """Original-source Drive IDs recorded by earlier ingestion runs (for name recovery)."""
    ids: dict[str, dict] = {}
    def add(sid, info):
        if sid and re.fullmatch(r"[A-Za-z0-9_-]{25,}", sid):
            ids.setdefault(sid, info)
    for fn in ("copy_plan.json", "extra_books.json"):
        p = DATA / fn
        if p.exists():
            for x in json.load(open(p, encoding="utf-8")):
                add(x.get("source_id"), {"from": fn, "recorded_name": x.get("name"), "file_id": x.get("file_id", "")})
    return ids


def lookup_source(item) -> dict:
    sid, info = item
    try:
        f = d.get(sid, "id,name,md5Checksum,size,mimeType,parents")
        return {"source_id": sid, **info, "name": f.get("name"), "md5": f.get("md5Checksum"), "size": f.get("size"), "ok": True}
    except Exception as e:  # noqa: BLE001
        return {"source_id": sid, **info, "ok": False, "error": str(e)[:160]}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [r for r in csv.DictReader(open(AUDIT / "inventory_full.csv", encoding="utf-8-sig")) if r["kind"] == "ebook"]
    out_path = OUT / "file_meta.jsonl"
    done = set()
    if out_path.exists():
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(json.loads(line)["id"])
            except Exception:
                pass
    todo = [r for r in rows if r["id"] not in done]
    print(f"ebooks: {len(rows)}, to process: {len(todo)}", flush=True)
    t0 = time.time()
    counts = {"valid": 0, "html": 0, "error": 0, "other_invalid": 0}
    with open(out_path, "a", encoding="utf-8") as fh, cf.ThreadPoolExecutor(WORKERS) as ex:
        for i, rec in enumerate(ex.map(process, todo), 1):
            with _wlock:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec.get("error"):
                counts["error"] += 1
            elif rec.get("real_type") == "html":
                counts["html"] += 1
            elif rec.get("valid"):
                counts["valid"] += 1
            else:
                counts["other_invalid"] += 1
            if i % 500 == 0:
                fh.flush()
                print(
                    f"  {i}/{len(todo)} ({time.time()-t0:.0f}s) "
                    f"valid={counts['valid']} html={counts['html']} "
                    f"other_invalid={counts['other_invalid']} err={counts['error']}",
                    flush=True,
                )
        fh.flush()
    print(
        f"metadata done {len(todo)} items in {time.time()-t0:.0f}s: "
        f"valid={counts['valid']} html={counts['html']} "
        f"other_invalid={counts['other_invalid']} err={counts['error']}",
        flush=True,
    )

    src = source_ids()
    print(f"source ids to look up: {len(src)}", flush=True)
    t1 = time.time()
    src_ok = 0
    with open(OUT / "source_lookup.jsonl", "w", encoding="utf-8") as fh, cf.ThreadPoolExecutor(WORKERS) as ex:
        for i, rec in enumerate(ex.map(lookup_source, src.items()), 1):
            if rec.get("ok"):
                src_ok += 1
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 1000 == 0:
                fh.flush()
                print(f"  source {i}/{len(src)} ok={src_ok} ({time.time()-t1:.0f}s)", flush=True)
    print(f"done in {time.time()-t0:.0f}s (source_ok={src_ok}/{len(src)})", flush=True)


if __name__ == "__main__":
    main()
