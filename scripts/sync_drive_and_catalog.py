import concurrent.futures
import json
import os
import sys
import threading
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PROGRESS_FILE = DATA_DIR / "catalog_progress.json"


def load_credentials() -> Credentials:
    raw = os.environ.get("GDRIVE_OAUTH_TOKEN_JSON", "").strip()
    if not raw:
        raise RuntimeError(
            "Missing GDRIVE_OAUTH_TOKEN_JSON secret. "
            "Add an OAuth2 authorized_user JSON (with client_id, client_secret, refresh_token) "
            "to GitHub Repository Secrets."
        )
    info = json.loads(raw)
    creds = Credentials.from_authorized_user_info(
        info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return creds


def copy_one(creds: Credentials, item: dict, parent_id: str) -> tuple[str, str]:
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    body = {"name": item["name"], "parents": [parent_id]}
    for attempt in range(5):
        try:
            res = (
                service.files()
                .copy(fileId=item["source_id"], body=body, fields="id", supportsAllDrives=True)
                .execute()
            )
            return item["source_id"], res["id"]
        except HttpError as e:
            status = getattr(e.resp, "status", None)
            if status in (403, 429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise


def main():
    max_items = int(os.environ.get("MAX_ITEMS_PER_RUN", "1500"))
    plan = json.loads((DATA_DIR / "copy_plan.json").read_text(encoding="utf-8"))
    fmap = json.loads((DATA_DIR / "folder_map.json").read_text(encoding="utf-8"))
    progress = (
        json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        if PROGRESS_FILE.exists()
        else {}
    )

    todo = [it for it in plan if it["source_id"] not in progress]
    print(f"Total books: {len(plan)}, Already copied: {len(progress)}, Remaining: {len(todo)}")
    if not todo:
        print("All books are already copied!")
        return

    batch = todo[:max_items]
    print(f"Processing {len(batch)} books in this run...")
    creds = load_credentials()
    lock = threading.Lock()
    done = 0
    errors = 0

    def task(it):
        key = f"{it['category']}||{it['subfolder']}"
        parent_id = fmap["subfolders"][key]
        return copy_one(creds, it, parent_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(task, it): it for it in batch}
        for f in concurrent.futures.as_completed(futs):
            it = futs[f]
            try:
                src_id, new_id = f.result()
                with lock:
                    progress[src_id] = new_id
                    done += 1
                    if done % 100 == 0:
                        PROGRESS_FILE.write_text(
                            json.dumps(progress, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                        print(f"Copied {done}/{len(batch)} (total {len(progress)}/{len(plan)})")
            except Exception as e:
                with lock:
                    errors += 1
                print(f"ERROR copying {it['name']} ({it['source_id']}): {e}", file=sys.stderr)

    PROGRESS_FILE.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Run complete: {done} copied, {errors} errors, total {len(progress)}/{len(plan)}")


if __name__ == "__main__":
    main()
