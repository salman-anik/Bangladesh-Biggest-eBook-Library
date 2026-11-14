import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

LANGUAGE_SERVER = r"C:\Users\USER\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"
GDRIVE_BASE = (
    [LANGUAGE_SERVER, "plugin-cli", "gdrive"]
    if Path(LANGUAGE_SERVER).exists()
    else [shutil.which("gdrive") or "gdrive"]
)
REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
ROOT_DRIVE_ID = "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
ROOT_DRIVE_NAME = "Bangladesh-Biggest-eBook-Library"

TRASH_EXTS = {".ini", ".apk"}

# Genuine Bengali IA indices in IA[0..38] re-homed out of Quran
IA_KEEP_OVERRIDES = {
    "17lV2E9NDNzclk2kWBZikGAGR-NKrs2f3": "Language and Linguistics/Arabic Language",
    "1628eVw9GT6uh9uj1pv10kGQfmQu17VlP": "Religion/Islam/Islamic Lifestyle",
    "18rWm31n6YfPxJ2rQ0LynNRYva8mNrU0Y": "History/Ancient History",
    "1DLOLLgRQlcvLdeHJd2DGeSPeqcFPCSEG": "Religion/Hinduism",
    "1ESpZ1YEgfxjKh2uFuuZu8KghIKzcTW71": "Literature/Collected Works",
    "1dn05x9QaWPyXjXbYO8J7AEDeP7ap0j1r": "Fiction/Social Fiction",
    "1FiT-SrwTUazFGlmwUpTDpv2G-zdAhGpz": "Religion/Islam/Fiqh",
    "1Icbhnbq-suHTyg5siHARpYCBFFO4Njs5": "Religion/Islam/Islamic Lifestyle",
    "1OcR_wX3UxKo_wx9IDP3tucfoSgnswNwe": "Literature/Novels",
    "1UC7ZeMGkxzyUgse6emOiuKi7yWniAmI5": "Literature/Poetry",
    "15NYVNS-xfdK16Oep80zqpk6wRzcUymBT": "Medicine and Health/Alternative Medicine",
    "1GPHh5-yW3TFR7eyDqY4Dnulj6qUtMgWL": "Literature/Children's Literature",
    "1iAcdp62yBwnre91qTRU6eomtjfG5y2HF": "Literature/Poetry",
    "11tVmsslla7iIzWhp9ZJya35QFnD4O7rZ": "Religion/Islam/Hadith",
    "16yECJVKawICfuC68MRtD-FpsQS0cylpn": "Law and Legal/Bangladesh Law",
    "1ytmYHsmahyiWs2ZNRs_5TgJbyS1bNg3J": "Literature/Children's Literature",
    "1C0eNBBpS2vyHtjmLMYvUDnPVfLJfybcx": "Literature/Children's Literature",
    "14dlZvlESptD1kDBuNRxpbfxC_GFGtAiH": "Religion/Islam/Islamic Lifestyle",
    "1Scjo2vVwI7cP2t1aQy3SHShS-KSiy9iD": "Religion/Islam/Hadith",
    "1tpy9jKtx4XtuBxW51yh-LHoCBlFVuKWU": "Religion/Islam/Fiqh",
    "1cLMp9KdJnmVXr-wJP4-aXJlNu2cnw0cT": "Religion/Islam/Islamic Lifestyle",
    "1AE2Wn7c8QXja7Pzbv0islxxTuxWMBQVv": "Religion/Islam/Islamic Literature",
    "1A37KXgytSftBVVNQ3Vvu90xxgXxn1XCl": "Religion/Islam/Islamic Literature",
    "1NDk5SKSi7xc9VwR54CAJpErPFOXLKaBk": "Religion/Islam/Islamic Politics",
    "1-RJey1J6R_8vZiQUE6izkjRdmFO9w0C1": "Religion/Hinduism",
    "1wX4AcXtzaJiM5eH0mzL4Gn7L_uuoqOIg": "Religion/Islam/Islamic Philosophy",
    "1srdYEU1KlDmcr9lWoLBU31XOcsZzciSS": "Religion/Islam/Aqeedah",
    "1vXF_tLDRdqzfSGecV9xNbuxgy-VCooit": "Religion/Hinduism",
    "1n-jsuP4Lyb3Klz_N9wxReDkP0uW-QNgj": "Religion/Islam/Fiqh",
    "1hUh6GumezCHRuf124iHWCsN0qqD-9zir": "Religion/Islam/Sahaba",
}


def clean_tax_segment(raw: str) -> str:
    if not re.search(r"[A-Za-z]", raw):
        return raw
    s = re.sub(r"^\d+_", "", raw)
    s2 = re.sub(r"[\u0980-\u09FF]+", "", s)
    s2 = re.sub(r"_+", " ", s2).strip()
    s2 = re.sub(r"\s+", " ", s2)
    return s2 or raw


def clean_tax_path(raw_path: str) -> str:
    return "/".join(clean_tax_segment(seg) for seg in raw_path.split("/"))


def detect_nctb_classes(name: str) -> list[str]:
    n = name.lower()
    if "প্রাক-প্রাথমিক" in name or "প্রাক প্রাথমিক" in name or "pre-primary" in n or "pre primary" in n:
        return ["Pre-Primary"]
    if "একাদশ" in name or "দ্বাদশ" in name or "hsc" in n or "উচ্চ মাধ্যমিক" in name:
        return ["Higher Secondary"]
    if any(k in name for k in ["নবম দশম", "নবম ও দশম", "নবম-দশম", "নবম - দশম", "এসএসসি"]) or "9-10" in n or "ix-x" in n:
        return ["Class 9", "Class 10"]
    for kw, cls in [
        (("প্রথম শ্রেণি", "১ম শ্রেণি", "class 1", "class-1"), "Class 1"),
        (("দ্বিতীয় শ্রেণি", "দ্বিতীয় শ্রেণি", "২য় শ্রেণি", "২য় শ্রেণি", "class 2"), "Class 2"),
        (("তৃতীয় শ্রেণি", "তৃতীয় শ্রেণি", "৩য় শ্রেণি", "৩য় শ্রেণি", "class 3"), "Class 3"),
        (("চতুর্থ শ্রেণি", "৪র্থ শ্রেণি", "class 4"), "Class 4"),
        (("পঞ্চম শ্রেণি", "৫ম শ্রেণি", "class 5"), "Class 5"),
        (("ষষ্ঠ শ্রেণি", "৬ষ্ঠ শ্রেণি", "class 6"), "Class 6"),
        (("সপ্তম শ্রেণি", "৭ম শ্রেণি", "class 7"), "Class 7"),
        (("অষ্টম শ্রেণি", "৮ম শ্রেণি", "class 8"), "Class 8"),
        (("নবম শ্রেণি", "৯ম শ্রেণি", "class 9"), "Class 9"),
        (("দশম শ্রেণি", "১০ম শ্রেণি", "class 10"), "Class 10"),
    ]:
        if any(k in n for k in kw):
            return [cls]
    return ["Primary Education"]


def run_gd(args: list[str], retries: int = 4, timeout: int = 120) -> str:
    last_err = ""
    for attempt in range(retries):
        try:
            res = subprocess.run(
                GDRIVE_BASE + args,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            if res.returncode == 0:
                return res.stdout
            last_err = res.stderr or res.stdout
            if "not found" in last_err.lower() or "404" in last_err:
                return ""
        except subprocess.TimeoutExpired as e:
            last_err = f"timeout: {e}"
        time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"gdrive {args} failed: {last_err}")


def parse_gdrive_id(out: str) -> str:
    txt = out.strip()
    if txt.startswith("{"):
        try:
            obj = json.loads(txt)
            if obj.get("id"):
                return obj["id"]
        except Exception:
            pass
    m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", txt)
    if m:
        return m.group(1)
    raise RuntimeError(f"Could not parse Drive ID from output: {txt[:300]}")


def gd_ls(parent_id: str) -> list[dict]:
    out = run_gd(["readonly", "ls", parent_id, "--max", "0", "--json"])
    if not out.strip():
        return []
    return json.loads(out)


def gd_ensure_folder(name: str, parent_id: str, existing_children: dict[str, str] | None = None) -> str:
    if existing_children is None:
        children = gd_ls(parent_id)
        existing_children = {
            c["name"]: c["id"]
            for c in children
            if c.get("mimeType") == "application/vnd.google-apps.folder"
        }
    if name in existing_children:
        return existing_children[name]
    out = run_gd(["mutate", "mkdir", name, "--parent", parent_id])
    return parse_gdrive_id(out)


def gd_rename(file_id: str, new_name: str) -> None:
    run_gd(["mutate", "rename", file_id, new_name])


def gd_mv(file_id: str, new_parent: str) -> None:
    run_gd(["mutate", "mv", file_id, new_parent])


def gd_cp(file_id: str, name: str, parent_id: str) -> str:
    out = run_gd(["mutate", "cp", file_id, name, "--parent", parent_id])
    return parse_gdrive_id(out)


def gd_trash(file_id: str) -> None:
    run_gd(["mutate", "trash", file_id])


def gd_batch(ops: list[dict], chunk_size: int = 60) -> bool:
    import tempfile
    for i in range(0, len(ops), chunk_size):
        chunk = ops[i : i + chunk_size]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(chunk, tf, ensure_ascii=False)
            tmp = tf.name
        try:
            run_gd(["mutate", "batch", "-f", tmp], retries=3)
        finally:
            Path(tmp).unlink(missing_ok=True)
    return True


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    sys.path.insert(0, str(REPO_DIR / "scripts"))
    import build_25cat_library as b25  # noqa: E402

    taxonomy_keys = set()
    for tc, sub in b25.TAXONOMY.items():
        taxonomy_keys.add(tc)
        if isinstance(sub, dict):
            for mid, leaves in sub.items():
                taxonomy_keys.add(f"{tc}/{mid}")
                for lf in leaves:
                    taxonomy_keys.add(f"{tc}/{mid}/{lf}")
        else:
            for lf in sub:
                taxonomy_keys.add(f"{tc}/{lf}")

    state_file = DATA_DIR / "taxonomy_state.json"
    tstate = json.loads(state_file.read_text(encoding="utf-8"))
    reorg_file = DATA_DIR / "reorg_state.json"
    rstate = (
        json.loads(reorg_file.read_text(encoding="utf-8"))
        if reorg_file.exists()
        else {
            "root_renamed": False,
            "top_created": {},
            "moved_cats_to_pdf": [],
            "renamed_folders": {},
            "trashed_ids": [],
            "rehomed_ia": [],
            "nctb_moved": [],
            "nctb_copied_10": {},
        }
    )

    def save_rstate() -> None:
        reorg_file.write_text(json.dumps(rstate, ensure_ascii=False, indent=2), encoding="utf-8")

    # 1. Rename Google Drive root folder & create pdf / text / covers
    print("Step 1: Renaming Google Drive root and ensuring pdf/, text/, covers/...", flush=True)
    if not rstate["root_renamed"]:
        gd_rename(ROOT_DRIVE_ID, ROOT_DRIVE_NAME)
        rstate["root_renamed"] = True
        save_rstate()

    root_children = {
        c["name"]: c["id"]
        for c in gd_ls(ROOT_DRIVE_ID)
        if c.get("mimeType") == "application/vnd.google-apps.folder"
    }
    for folder_name in ("pdf", "text", "covers"):
        if folder_name not in rstate["top_created"]:
            rstate["top_created"][folder_name] = gd_ensure_folder(folder_name, ROOT_DRIVE_ID, root_children)
            save_rstate()

    pdf_root_id = rstate["top_created"]["pdf"]
    text_root_id = rstate["top_created"]["text"]
    covers_root_id = rstate["top_created"]["covers"]
    print(f"  Root folders -> pdf={pdf_root_id}, text={text_root_id}, covers={covers_root_id}", flush=True)

    # Create cover source subfolders inside covers/
    cover_children = {
        c["name"]: c["id"]
        for c in gd_ls(covers_root_id)
        if c.get("mimeType") == "application/vnd.google-apps.folder"
    }
    for src_sub in ("KindleBangla", "BDeBooks", "eBanglaLibrary"):
        key = f"covers_{src_sub}"
        if key not in rstate["top_created"]:
            rstate["top_created"][key] = gd_ensure_folder(src_sub, covers_root_id, cover_children)
            save_rstate()

    # 2. Move the 25 top-level category folders into pdf/
    print("Step 2: Moving 25 category folders under pdf/...", flush=True)
    existing_in_pdf = {c["id"] for c in gd_ls(pdf_root_id)}
    moved_cats = set(rstate["moved_cats_to_pdf"])
    todo_cat_moves = []
    for tc in b25.TAXONOMY.keys():
        fid = tstate["folders"].get(tc)
        if not fid:
            continue
        if fid in existing_in_pdf:
            if tc not in moved_cats:
                rstate["moved_cats_to_pdf"].append(tc)
            continue
        if tc not in moved_cats:
            todo_cat_moves.append((tc, fid))
    save_rstate()
    if todo_cat_moves:
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(gd_mv, fid, pdf_root_id): tc for tc, fid in todo_cat_moves}
            for f in concurrent.futures.as_completed(futs):
                f.result()
                rstate["moved_cats_to_pdf"].append(futs[f])
        save_rstate()
    print(f"  All {len(rstate['moved_cats_to_pdf'])} top-level category folders inside pdf/", flush=True)

    # 3. Rename all taxonomy folders (25 top + Islam + ~240 leaves) to clean English via batch
    print("Step 3: Renaming category and leaf folders to clean English names (batch)...", flush=True)
    renamed_map = rstate["renamed_folders"]
    todo_renames = []
    for raw_path in sorted(taxonomy_keys):
        fid = tstate["folders"].get(raw_path)
        if not fid or fid in renamed_map:
            continue
        clean_seg = clean_tax_segment(raw_path.split("/")[-1])
        todo_renames.append((raw_path, fid, clean_seg))
    print(f"  Folders to rename: {len(todo_renames)}", flush=True)
    if todo_renames:
        for i in range(0, len(todo_renames), 25):
            chunk = todo_renames[i : i + 25]
            ops = [{"op": "rename", "fileId": fid, "name": clean_seg} for _, fid, clean_seg in chunk]
            gd_batch(ops, chunk_size=25)
            for _, fid, clean_seg in chunk:
                renamed_map[fid] = clean_seg
            save_rstate()
            print(f"    Renamed {min(i + 25, len(todo_renames))}/{len(todo_renames)}", flush=True)

    # Build clean folder ID mapping from tstate["folders"]
    clean_folders: dict[str, str] = {}
    clean_folders["__ROOT__"] = ROOT_DRIVE_ID
    clean_folders["pdf"] = pdf_root_id
    clean_folders["text"] = text_root_id
    clean_folders["covers"] = covers_root_id
    for k, v in rstate["top_created"].items():
        if k.startswith("covers_"):
            clean_folders[f"covers/{k[7:]}"] = v
    for raw_path, fid in tstate["folders"].items():
        clean_folders[f"pdf/{clean_tax_path(raw_path)}"] = fid

    # 4. Create Pre-Primary and Class 1..Class 10 under pdf/Education and Academics
    print("Step 4: Creating Pre-Primary & Class 1..Class 10 under pdf/Education and Academics...", flush=True)
    edu_id = clean_folders["pdf/Education and Academics"]
    edu_children = {
        c["name"]: c["id"]
        for c in gd_ls(edu_id)
        if c.get("mimeType") == "application/vnd.google-apps.folder"
    }
    class_folders = ["Pre-Primary"] + [f"Class {i}" for i in range(1, 11)]
    for cls_name in class_folders:
        cpath = f"pdf/Education and Academics/{cls_name}"
        if cpath not in clean_folders:
            clean_folders[cpath] = gd_ensure_folder(cls_name, edu_id, edu_children)

    # 5. Trash non-book / foreign / CIA Archive.org files and .ini/.apk junk
    print("Step 5: Purging non-book / foreign / CIA junk files...", flush=True)
    extra_file = DATA_DIR / "extra_books.json"
    extra = json.loads(extra_file.read_text(encoding="utf-8"))
    books_json_path = REPO_DIR / "books.json"
    curr_books = json.loads(books_json_path.read_text(encoding="utf-8")) if books_json_path.exists() else []

    ia_list = [b for b in extra if (b.get("source_id") or "").startswith("ia:")]
    trash_ids = set()
    for i, b in enumerate(ia_list):
        if i >= 39 or b["file_id"] not in IA_KEEP_OVERRIDES:
            # Wait: check IA[02] (Democracy) & IA[10] (Islamic Philosophy) & IA[14,15,17] (Surah) & IA[16] (Nazrul) & IA[19] (Stranger) & IA[38] (Quran)
            nm = b["name"]
            if i < 39 and b["file_id"] not in (
                "1T8WKNp0ZbgWF2dafQE8IymgUm68yyppA",  # The Primordiverse Theory Of Multiverse.pdf
                "1K4BM_it1KbVFd7TRyq2WbI2ZDg3Q11fN",  # The Stranger ( Lutful).pdf
            ):
                continue
            trash_ids.add(b["file_id"])

    # Also trash .ini (desktop.ini) and .apk files from base/extra
    for b in curr_books + extra:
        suf = Path(b["name"]).suffix.lower()
        if suf in TRASH_EXTS:
            trash_ids.add(b["file_id"])

    already_trashed = set(rstate["trashed_ids"])
    todo_trash = sorted(trash_ids - already_trashed)
    print(f"  Total junk to trash: {len(trash_ids)} (pending: {len(todo_trash)})", flush=True)
    if todo_trash:
        for i in range(0, len(todo_trash), 25):
            chunk = todo_trash[i : i + 25]
            ops = [{"op": "trash", "fileId": fid} for fid in chunk]
            gd_batch(ops, chunk_size=25)
            rstate["trashed_ids"].extend(chunk)
            save_rstate()
            print(f"    Trashed {min(i + 25, len(todo_trash))}/{len(todo_trash)}", flush=True)

    trashed_all = set(rstate["trashed_ids"])
    trashed_file = DATA_DIR / "trashed_ids.json"
    trashed_file.write_text(json.dumps(sorted(trashed_all), indent=2), encoding="utf-8")

    # Remove trashed items from extra_books.json & normalize paths in extra_books.json
    cleaned_extra = []
    for b in extra:
        if b["file_id"] in trashed_all:
            continue
        b["top_category"] = clean_tax_segment(b["top_category"])
        b["leaf_path"] = clean_tax_path(b["leaf_path"])
        b["leaf_category"] = clean_tax_segment(b["leaf_category"])
        cleaned_extra.append(b)

    # 6. Re-home kept IA books into their proper leaf folders
    print("Step 6: Re-homing genuine Bengali IA books into true leaf folders...", flush=True)
    rehomed_set = set(rstate["rehomed_ia"])
    ia_moves = []
    for b in cleaned_extra:
        fid = b["file_id"]
        if fid in IA_KEEP_OVERRIDES:
            new_lp = IA_KEEP_OVERRIDES[fid]
            b["top_category"] = new_lp.split("/")[0]
            b["leaf_path"] = new_lp
            b["leaf_category"] = new_lp.split("/")[-1]
            if fid not in rehomed_set:
                dest_id = clean_folders[f"pdf/{new_lp}"]
                ia_moves.append((fid, dest_id))
    if ia_moves:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(gd_mv, fid, dest_id): fid for fid, dest_id in ia_moves}
            for f in concurrent.futures.as_completed(futs):
                f.result()
                rstate["rehomed_ia"].append(futs[f])
        save_rstate()

    # 7. Move all 1,248 NCTB books into Pre-Primary / Class 1..Class 10 / Higher Secondary / Primary Education
    print("Step 7: Organizing 1,248 NCTB textbooks into Pre-Primary & Class 1..Class 10...", flush=True)
    nctb_moved_set = set(rstate["nctb_moved"])
    nctb_copied_10 = rstate["nctb_copied_10"]
    todo_nctb_mv = []
    todo_nctb_cp10 = []
    new_class10_records = []
    existing_extra_ids = {b["file_id"] for b in cleaned_extra}

    for b in cleaned_extra:
        if "nctb" not in (b.get("publication") or "").lower() and "NCTB" not in b["name"]:
            continue
        classes = detect_nctb_classes(b["name"])
        primary_cls = classes[0]
        target_lp = f"Education and Academics/{primary_cls}"
        b["top_category"] = "Education and Academics"
        b["leaf_path"] = target_lp
        b["leaf_category"] = primary_cls
        b["subfolder"] = None

        if b["file_id"] not in nctb_moved_set:
            dest_id = clean_folders[f"pdf/{target_lp}"]
            todo_nctb_mv.append((b["file_id"], dest_id))

        if len(classes) == 2 and classes[1] == "Class 10":
            c10_folder_id = clean_folders["pdf/Education and Academics/Class 10"]
            if b["file_id"] in nctb_copied_10:
                c10_id = nctb_copied_10[b["file_id"]]
                if c10_id not in existing_extra_ids:
                    c10_rec = dict(b)
                    c10_rec["source_id"] = f"nctb10:{b['file_id']}"
                    c10_rec["file_id"] = c10_id
                    c10_rec["leaf_path"] = "Education and Academics/Class 10"
                    c10_rec["leaf_category"] = "Class 10"
                    c10_rec["link"] = f"https://drive.google.com/file/d/{c10_id}/view"
                    new_class10_records.append(c10_rec)
                    existing_extra_ids.add(c10_id)
            else:
                todo_nctb_cp10.append((b, c10_folder_id))

    print(f"  NCTB moves pending: {len(todo_nctb_mv)}, Class 9-10 copies to Class 10 pending: {len(todo_nctb_cp10)}", flush=True)
    if todo_nctb_mv:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(gd_mv, fid, dest): fid for fid, dest in todo_nctb_mv}
            done = 0
            for f in concurrent.futures.as_completed(futs):
                f.result()
                rstate["nctb_moved"].append(futs[f])
                done += 1
                if done % 50 == 0:
                    print(f"    NCTB moved {done}/{len(todo_nctb_mv)}", flush=True)
                    save_rstate()
        save_rstate()

    if todo_nctb_cp10:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(gd_cp, b["file_id"], b["name"], c10_fid): b for b, c10_fid in todo_nctb_cp10}
            done = 0
            for f in concurrent.futures.as_completed(futs):
                orig = futs[f]
                new_id = f.result()
                nctb_copied_10[orig["file_id"]] = new_id
                c10_rec = dict(orig)
                c10_rec["source_id"] = f"nctb10:{orig['file_id']}"
                c10_rec["file_id"] = new_id
                c10_rec["leaf_path"] = "Education and Academics/Class 10"
                c10_rec["leaf_category"] = "Class 10"
                c10_rec["link"] = f"https://drive.google.com/file/d/{new_id}/view"
                new_class10_records.append(c10_rec)
                done += 1
                if done % 25 == 0:
                    print(f"    NCTB Class 10 copied {done}/{len(todo_nctb_cp10)}", flush=True)
                    save_rstate()
        save_rstate()

    cleaned_extra.extend(new_class10_records)
    extra_file.write_text(json.dumps(cleaned_extra, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save updated clean_folders into taxonomy_state_clean.json
    (DATA_DIR / "clean_folders.json").write_text(json.dumps(clean_folders, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done Step 1! extra_books={len(cleaned_extra)}, trashed={len(trashed_all)}, clean_folders={len(clean_folders)}", flush=True)


if __name__ == "__main__":
    main()
