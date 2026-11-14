import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

GDRIVE = shutil.which("gdrive") or "gdrive"
REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
SCRATCH_DIR = Path(
    r"C:\Users\USER\.gemini\antigravity\brain\257bbbd5-d40b-4ea8-a579-659f152212d3\scratch\batches"
)
PROGRESS_FILE = DATA_DIR / "catalog_progress.json"
LINE_RE = re.compile(r"\[\d+\]\s+Copied\s+([A-Za-z0-9_-]+)\s+->\s+([A-Za-z0-9_-]+)")


def run_batch(batch_idx: int, items: list[dict], fmap: dict) -> tuple[dict[str, str], str]:
    ops = []
    for it in items:
        key = f"{it['category']}||{it['subfolder']}"
        ops.append({
            "op": "copy",
            "fileId": it["source_id"],
            "name": it["name"],
            "parentId": fmap["subfolders"][key],
        })
    batch_file = SCRATCH_DIR / f"batch_{batch_idx}.json"
    batch_file.write_text(json.dumps(ops, ensure_ascii=False), encoding="utf-8")

    res = subprocess.run(
        [GDRIVE, "mutate", "batch", "-f", str(batch_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    out = (res.stdout or "") + "\n" + (res.stderr or "")
    copied = {}
    for m in LINE_RE.finditer(out):
        copied[m.group(1)] = m.group(2)
    err_msg = ""
    if res.returncode != 0 or len(copied) < len(items):
        err_lines = [ln for ln in out.splitlines() if ln.strip() and not LINE_RE.search(ln) and not ln.startswith("Executed ")]
        if err_lines:
            err_msg = " | ".join(err_lines[:3])
    return copied, err_msg


def sync_and_push(wave_label: str) -> None:
    subprocess.run(
        [sys.executable, str(REPO_DIR / "scripts" / "generate_library.py")],
        cwd=str(REPO_DIR),
        check=True,
    )
    subprocess.run(
        ["git", "add", "data/catalog_progress.json", "README.md", "categories/", "books.json"],
        cwd=str(REPO_DIR),
        check=True,
    )
    diff = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=str(REPO_DIR))
    if diff.returncode == 0:
        print(f"[{wave_label}] No git changes to commit.")
        return
    subprocess.run(
        ["git", "commit", "-m", "chore: sync batch of books to personal Google Drive"],
        cwd=str(REPO_DIR),
        check=True,
    )
    push = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=str(REPO_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if push.returncode != 0:
        print(f"[{wave_label}] Push failed, attempting pull --rebase: {push.stderr.strip()}")
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=str(REPO_DIR), check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_DIR), check=True)
    print(f"[{wave_label}] Pushed updated catalog to GitHub.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resumable batch copy of books to Google Drive")
    parser.add_argument("--workers", type=int, default=8, help="Parallel gdrive batch workers")
    parser.add_argument("--batch-size", type=int, default=50, help="Operations per batch JSON")
    parser.add_argument("--wave-size", type=int, default=800, help="Items per commit/push wave")
    args = parser.parse_args()

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    plan = json.loads((DATA_DIR / "copy_plan.json").read_text(encoding="utf-8"))
    fmap = json.loads((DATA_DIR / "folder_map.json").read_text(encoding="utf-8"))
    progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}

    todo = [it for it in plan if it["source_id"] not in progress]
    print(f"Starting copy: Total={len(plan)}, AlreadyCopied={len(progress)}, Remaining={len(todo)}", flush=True)
    if not todo:
        sync_and_push("final")
        return

    waves = [todo[i:i + args.wave_size] for i in range(0, len(todo), args.wave_size)]
    for w_idx, wave in enumerate(waves, 1):
        t0 = time.time()
        chunks = [wave[i:i + args.batch_size] for i in range(0, len(wave), args.batch_size)]
        wave_copied = 0
        wave_errors = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [
                ex.submit(run_batch, (w_idx - 1) * 100 + c_idx, ch, fmap)
                for c_idx, ch in enumerate(chunks)
            ]
            for f in concurrent.futures.as_completed(futs):
                copied, err_msg = f.result()
                progress.update(copied)
                wave_copied += len(copied)
                if err_msg:
                    wave_errors.append(err_msg)

        PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
        elapsed = time.time() - t0
        print(
            f"Wave {w_idx}/{len(waves)}: copied {wave_copied}/{len(wave)} in {elapsed:.1f}s "
            f"(Total: {len(progress)}/{len(plan)})",
            flush=True,
        )
        if wave_errors:
            print(f"Wave {w_idx} sample errors: {wave_errors[:3]}", file=sys.stderr, flush=True)

        sync_and_push(f"wave-{w_idx}")

    print(f"Finished all waves. Total copied: {len(progress)}/{len(plan)}", flush=True)


if __name__ == "__main__":
    main()
