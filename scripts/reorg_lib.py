import subprocess
import json
import shutil
import os
import re
import time
import threading
from pathlib import Path
from datetime import datetime, timezone

def _resolve_gdrive_prefix():
    cmd_path = shutil.which('gdrive') or 'gdrive'
    if os.name == 'nt' and cmd_path.lower().endswith(('.cmd', '.bat')) and os.path.exists(cmd_path):
        try:
            txt = Path(cmd_path).read_text(encoding='utf-8', errors='replace').strip()
            m = re.match(r'^@"([^"]+)"\s+(.*?)\s+%\*\s*$', txt)
            if m:
                return [m.group(1), *m.group(2).split()], False
        except Exception:
            pass
        return [cmd_path], True
    return [cmd_path], False

GDRIVE_PREFIX, USE_SHELL = _resolve_gdrive_prefix()
LOG_FILE = r'C:\Users\USER\.gemini\antigravity\scratch\Bangladesh-Biggest-eBook-Library\data\library_reorganization_log.json'
_LOG_LOCK = threading.Lock()
_DEFERRED_OPS = []

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"operations": [], "created_folders": {}, "stats": {"renamed": 0, "moved": 0, "mkdir": 0, "shortcuts": 0, "updated": 0}}

def save_log(log_data):
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

def flush_log():
    with _LOG_LOCK:
        if not _DEFERRED_OPS:
            return
        log_data = load_log()
        for entry in _DEFERRED_OPS:
            log_data["operations"].append(entry)
            act = entry.get("action")
            if act in log_data["stats"]:
                log_data["stats"][act] += 1
        _DEFERRED_OPS.clear()
        save_log(log_data)

def run_gdrive(args, max_retries=4):
    cmd = [*GDRIVE_PREFIX, *args]
    for attempt in range(max_retries):
        res = subprocess.run(cmd, capture_output=True, text=True, shell=USE_SHELL, encoding='utf-8', errors='replace')
        if res.returncode == 0:
            return True, res.stdout.strip(), res.stderr.strip()
        err = res.stderr.strip() or res.stdout.strip()
        if any(tok in err.lower() for tok in ["429", "rate", "timeout", "500", "502", "503", "quota", "connection"]):
            time.sleep(2 ** (attempt + 1))
            continue
        return False, res.stdout.strip(), err
    return False, "", "Max retries exceeded"

def log_op(op_type, details, deferred=False):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": op_type,
        **details
    }
    with _LOG_LOCK:
        if deferred:
            _DEFERRED_OPS.append(entry)
            if len(_DEFERRED_OPS) >= 50:
                log_data = load_log()
                for e in _DEFERRED_OPS:
                    log_data["operations"].append(e)
                    a = e.get("action")
                    if a in log_data["stats"]:
                        log_data["stats"][a] += 1
                _DEFERRED_OPS.clear()
                save_log(log_data)
            return
        log_data = load_log()
        log_data["operations"].append(entry)
        if op_type in log_data["stats"]:
            log_data["stats"][op_type] += 1
        save_log(log_data)

def rename_item(file_id, new_name, old_name=None, deferred=False, quiet=False):
    ok, out, err = run_gdrive(['mutate', 'rename', file_id, new_name, '--json'])
    log_op("renamed", {"id": file_id, "old_name": old_name, "new_name": new_name, "ok": ok, "error": err if not ok else None}, deferred=deferred)
    if not ok:
        raise RuntimeError(f"Rename failed for {file_id} -> {new_name}: {err}")
    if not quiet:
        print(f"[RENAME] {old_name or file_id} -> {new_name}")
    return json.loads(out) if out.startswith('{') else out

def move_item(file_id, new_parent_id, old_parent_id=None, name=None, deferred=False, quiet=False):
    ok, out, err = run_gdrive(['mutate', 'mv', file_id, new_parent_id, '--json'])
    log_op("moved", {"id": file_id, "name": name, "old_parent": old_parent_id, "new_parent": new_parent_id, "ok": ok, "error": err if not ok else None}, deferred=deferred)
    if not ok:
        raise RuntimeError(f"Move failed for {file_id} -> {new_parent_id}: {err}")
    if not quiet:
        print(f"[MOVE] {name or file_id} -> parent {new_parent_id}")
    return json.loads(out) if out.startswith('{') else out

def mkdir_item(name, parent_id):
    ok_ls, out_ls, _ = run_gdrive(['readonly', 'ls', parent_id, '--max', '0', '--json'])
    if ok_ls and out_ls:
        try:
            items = json.loads(out_ls)
            for it in items:
                if it.get('name') == name and it.get('mimeType') == 'application/vnd.google-apps.folder':
                    print(f"[MKDIR-EXISTS] {name} ({it['id']}) under {parent_id}")
                    return it['id']
        except Exception:
            pass

    ok, out, err = run_gdrive(['mutate', 'mkdir', name, '--parent', parent_id, '--json'])
    if not ok:
        log_op("mkdir", {"name": name, "parent": parent_id, "ok": False, "error": err})
        raise RuntimeError(f"Mkdir failed for {name} under {parent_id}: {err}")
    data = json.loads(out) if out.startswith('{') else {}
    fid = data.get('id')
    if not fid:
        ok_ls2, out_ls2, _ = run_gdrive(['readonly', 'ls', parent_id, '--max', '0', '--json'])
        if ok_ls2:
            for it in json.loads(out_ls2):
                if it.get('name') == name and it.get('mimeType') == 'application/vnd.google-apps.folder':
                    fid = it['id']
                    break
    with _LOG_LOCK:
        log_data = load_log()
        log_data["created_folders"][f"{parent_id}/{name}"] = fid
        save_log(log_data)
    log_op("mkdir", {"id": fid, "name": name, "parent": parent_id, "ok": True})
    print(f"[MKDIR] {name} ({fid}) under {parent_id}")
    return fid

def create_shortcut(target_id, target_folder_id, name=None):
    ok, out, err = run_gdrive(['mutate', 'create-shortcut', target_id, target_folder_id, '--json'])
    log_op("shortcuts", {"target_id": target_id, "target_folder": target_folder_id, "name": name, "ok": ok, "error": err if not ok else None})
    if not ok:
        raise RuntimeError(f"Create shortcut failed for {target_id} in {target_folder_id}: {err}")
    print(f"[SHORTCUT] target {target_id} in {target_folder_id}")
    return json.loads(out) if out.startswith('{') else out

def gdrive_ls(folder_id):
    ok, out, err = run_gdrive(['readonly', 'ls', folder_id, '--max', '0', '--json'])
    if not ok:
        raise RuntimeError(f"LS failed for {folder_id}: {err}")
    return json.loads(out)
