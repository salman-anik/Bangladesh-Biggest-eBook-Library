"""READ-ONLY full audit of the Google Drive eBook library.

Lists every item under the library root via the Drive API (one paginated
files.list over the whole Drive, then ancestry filtering), and writes:

  out/audit/inventory_full.csv        every file/folder under the root
  out/audit/backup_manifest.jsonl.gz  recovery manifest (id, name, parents, md5, size)
  out/audit/duplicates_md5.csv        byte-identical eBook groups (by md5Checksum)
  out/audit/empty_folders.csv         folders with no files anywhere below them
  out/audit/naming_issues.csv         eBook names that violate the naming standard
  out/audit/suspicious_files.csv      zero/tiny files, odd types, archives
  out/audit/folder_stats.csv          per-folder counts and sizes
  out/audit/audit_summary.json        headline numbers

Nothing is modified on Drive.
"""
from __future__ import annotations

import collections
import csv
import gzip
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_api as d  # noqa: E402

ROOT = os.environ.get("LIBRARY_ROOT_ID", "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq")
OUT = Path(os.environ.get("AUDIT_OUT", "out/audit"))

EBOOK_EXT = {"pdf", "epub", "mobi", "azw", "azw3", "djvu", "djv", "txt", "doc", "docx", "rtf",
             "fb2", "cbz", "cbr", "chm", "odt", "lit", "prc"}
ARCHIVE_EXT = {"zip", "rar", "7z", "tar", "gz"}
IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "tif", "tiff"}
BN = re.compile(r"[\u0980-\u09FF]")
LATIN = re.compile(r"[A-Za-z]")


def ext_of(name: str) -> str:
    m = re.search(r"\.([A-Za-z0-9]{1,5})$", name)
    return m.group(1).lower() if m else ""


def kind_of(item: dict) -> str:
    mt = item["mimeType"]
    if mt == d.FOLDER:
        return "folder"
    if mt == d.SHORTCUT:
        return "shortcut"
    if mt.startswith("application/vnd.google-apps"):
        return "google_doc"
    e = ext_of(item["name"])
    if e in EBOOK_EXT or mt in ("application/pdf", "application/epub+zip"):
        return "ebook"
    if e in ARCHIVE_EXT:
        return "archive"
    if e in IMAGE_EXT or mt.startswith("image/"):
        return "image"
    if e == "json":
        return "json"
    return "other"


def script_of(text: str) -> str:
    bn, la = len(BN.findall(text)), len(LATIN.findall(text))
    if bn and bn >= la:
        return "bn"
    if la:
        return "latin"
    return "none"


ISSUE_RULES = [
    ("copy_suffix", re.compile(r"\((?:Copy|কপি)(?: \d+)?\)|Copy of |\(\d+\)\.\w+$", re.I)),
    ("unknown_author", re.compile(r"Unknown Author|লেখক অজানা|\(Unknown\)", re.I)),
    ("underscores", re.compile(r"_")),
    ("random_id", re.compile(r"[A-Za-z0-9_-]{18,}")),
    ("site_tag", re.compile(r"www\.|\.com|\.net|boierhut|pdfbd|banglapdf|amarboi|murchona|boighor", re.I)),
    ("double_space_or_trim", re.compile(r"\s{2,}|^\s|\s\.\w+$")),
    ("no_author_separator", None),  # filled in below
]


def naming_issues(name: str) -> list[str]:
    issues = []
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", name)
    for key, rx in ISSUE_RULES:
        if rx is not None and rx.search(name):
            issues.append(key)
    if " — " not in stem:
        issues.append("no_author_separator")
    if script_of(stem) == "latin" and re.search(r"\b(?:Shrenir|Prathomik|Madhyamik|Somogro|Uponnas|Golpo|Kobita|Khondo|Bangla Bi)\b", stem):
        issues.append("romanized_bangla")
    return issues


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    items: dict[str, dict] = {}
    for i, f in enumerate(d.list_all("trashed = false")):
        items[f["id"]] = f
        if i % 20000 == 0:
            print(f"listed {i} items ({time.time()-t0:.0f}s)", flush=True)
    print(f"total drive items visible: {len(items)}", flush=True)

    root = d.get(ROOT)
    items[ROOT] = root
    children: dict[str, list[str]] = collections.defaultdict(list)
    for f in items.values():
        for p in f.get("parents", []) or []:
            children[p].append(f["id"])

    # BFS from root to get paths (first parent wins; multi-parent noted)
    path: dict[str, str] = {ROOT: ""}
    depth: dict[str, int] = {ROOT: 0}
    order = [ROOT]
    q = collections.deque([ROOT])
    while q:
        cur = q.popleft()
        for c in sorted(children.get(cur, []), key=lambda x: items[x]["name"]):
            if c in path:
                continue
            nm = items[c]["name"].replace("/", "∕")
            path[c] = f"{path[cur]}/{nm}" if path[cur] else nm
            depth[c] = depth[cur] + 1
            order.append(c)
            if items[c]["mimeType"] == d.FOLDER:
                q.append(c)
    lib = [i for i in order if i != ROOT]
    print(f"items under library root: {len(lib)}", flush=True)

    # ---------- inventory ----------
    rows = []
    for i in lib:
        f = items[i]
        k = kind_of(f)
        parent = (f.get("parents") or [""])[0]
        rows.append({
            "id": i, "name": f["name"], "kind": k, "mimeType": f["mimeType"], "ext": ext_of(f["name"]),
            "size": int(f.get("size", 0) or 0), "md5": f.get("md5Checksum", ""),
            "parent_id": parent, "n_parents": len(f.get("parents") or []), "depth": depth[i],
            "path": path[i], "top": path[i].split("/")[0], "script": script_of(f["name"]),
            "created": f.get("createdTime", ""), "modified": f.get("modifiedTime", ""),
            "shortcut_target": (f.get("shortcutDetails") or {}).get("targetId", ""),
            "description": (f.get("description") or "")[:300].replace("\n", " "),
            "app_properties": json.dumps(f.get("appProperties") or {}, ensure_ascii=False),
        })
    fields = list(rows[0].keys()) if rows else []
    with open(OUT / "inventory_full.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with gzip.open(OUT / "backup_manifest.jsonl.gz", "wt", encoding="utf-8") as fh:
        for i in [ROOT] + lib:
            f = items[i]
            fh.write(json.dumps({"id": i, "name": f["name"], "mimeType": f["mimeType"],
                                 "parents": f.get("parents"), "size": f.get("size"),
                                 "md5": f.get("md5Checksum"), "path": path[i],
                                 "modified": f.get("modifiedTime")}, ensure_ascii=False) + "\n")

    by_id = {r["id"]: r for r in rows}
    ebooks = [r for r in rows if r["kind"] == "ebook"]

    # ---------- duplicates ----------
    groups = collections.defaultdict(list)
    for r in ebooks:
        if r["md5"]:
            groups[r["md5"]].append(r)
    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    with open(OUT / "duplicates_md5.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["group", "md5", "size", "keep_candidate", "id", "name", "path"])
        for gi, (md5, v) in enumerate(sorted(dup_groups.items(), key=lambda kv: -kv[1][0]["size"])):
            # keep candidate = shallowest path outside review/duplicate areas, oldest created
            def score(r):
                bad = any(s in r["path"] for s in ("UNSORTED", "DUPLICATE", "LEGACY", "Review"))
                return (bad, "(Copy" in r["name"], r["created"])
            keep = min(v, key=score)["id"]
            for r in v:
                w.writerow([gi, md5, r["size"], "KEEP" if r["id"] == keep else "dup", r["id"], r["name"], r["path"]])

    # ---------- empty folders ----------
    file_count_below = collections.Counter()
    for r in rows:
        if r["kind"] != "folder":
            p = r["parent_id"]
            while p and p in by_id:
                file_count_below[p] += 1
                p = by_id[p]["parent_id"]
            if p == ROOT:
                file_count_below[ROOT] += 1
    folders = [r for r in rows if r["kind"] == "folder"]
    empty = [r for r in folders if file_count_below[r["id"]] == 0]
    with open(OUT / "empty_folders.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "path"])
        for r in empty:
            w.writerow([r["id"], r["name"], r["path"]])

    # ---------- folder stats ----------
    direct = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        direct[r["parent_id"]][r["kind"]] += 1
        direct[r["parent_id"]]["bytes"] += r["size"]
    with open(OUT / "folder_stats.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "path", "depth", "subfolders", "ebooks", "json", "images", "other", "direct_bytes", "files_below"])
        for r in folders:
            c = direct[r["id"]]
            w.writerow([r["id"], r["path"], r["depth"], c["folder"], c["ebook"], c["json"], c["image"],
                        c["other"] + c["archive"] + c["google_doc"], c["bytes"], file_count_below[r["id"]]])

    # ---------- naming / suspicious ----------
    issue_counter = collections.Counter()
    with open(OUT / "naming_issues.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "issues", "path"])
        for r in ebooks:
            iss = naming_issues(r["name"])
            issue_counter.update(iss)
            if iss:
                w.writerow([r["id"], r["name"], ";".join(iss), r["path"]])
    with open(OUT / "suspicious_files.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "reason", "size", "path"])
        for r in rows:
            reason = None
            if r["kind"] == "ebook" and r["size"] == 0:
                reason = "zero_bytes"
            elif r["kind"] == "ebook" and r["ext"] == "pdf" and r["size"] < 20_000:
                reason = "tiny_pdf_<20KB"
            elif r["kind"] in ("archive", "other"):
                reason = f"non_ebook_{r['kind']}"
            elif r["n_parents"] > 1:
                reason = "multiple_parents"
            if reason:
                w.writerow([r["id"], r["name"], reason, r["size"], r["path"]])

    # ---------- per-book-folder pattern ----------
    ebook_parent = collections.Counter(r["parent_id"] for r in ebooks)
    single_book_folders = sum(1 for p, n in ebook_parent.items() if n == 1)

    top_stats = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        top_stats[r["top"]][r["kind"]] += 1
        top_stats[r["top"]]["bytes"] += r["size"]
    l2 = collections.defaultdict(lambda: collections.Counter())
    for r in ebooks:
        parts = r["path"].split("/")
        l2["/".join(parts[:2])]["ebooks"] += 1
        l2["/".join(parts[:2])]["bytes"] += r["size"]

    dup_extra = sum(len(v) - 1 for v in dup_groups.values())
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root_id": ROOT, "root_name": root.get("name"),
        "total_items": len(rows),
        "kinds": dict(collections.Counter(r["kind"] for r in rows)),
        "ebook_ext": dict(collections.Counter(r["ext"] for r in ebooks).most_common()),
        "ebook_bytes": sum(r["size"] for r in ebooks),
        "all_bytes": sum(r["size"] for r in rows),
        "ebook_script": dict(collections.Counter(script_of(r["name"]) for r in ebooks)),
        "folders": len(folders), "empty_folders": len(empty),
        "max_depth": max((r["depth"] for r in rows), default=0),
        "ebook_folders_with_single_ebook": single_book_folders,
        "duplicate_md5_groups": len(dup_groups), "duplicate_extra_copies": dup_extra,
        "duplicate_extra_bytes": sum(v[0]["size"] * (len(v) - 1) for v in dup_groups.values()),
        "ebooks_without_md5": sum(1 for r in ebooks if not r["md5"]),
        "naming_issue_counts": dict(issue_counter.most_common()),
        "ebooks_clean_named": sum(1 for r in ebooks if not naming_issues(r["name"])),
        "zero_byte_ebooks": sum(1 for r in ebooks if r["size"] == 0),
        "multi_parent_items": sum(1 for r in rows if r["n_parents"] > 1),
        "shortcuts": sum(1 for r in rows if r["kind"] == "shortcut"),
        "top_level": {k: dict(v) for k, v in sorted(top_stats.items())},
        "level2_ebooks": {k: dict(v) for k, v in sorted(l2.items())},
        "elapsed_sec": round(time.time() - t0),
    }
    (OUT / "audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("level2_ebooks",)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
