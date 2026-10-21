from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import paramiko


ROOT = Path(__file__).resolve().parents[1]
REMOTE_ROOT = "/home/support/project/puj/respos/dragons_project_analitycs"
EXCLUDED = {".git", ".venv", "venv", ".vendor", "vendor_python", "__pycache__", ".idea", ".pytest_cache", ".mypy_cache", "node_modules", ".cache"}
TEXT_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".json", ".toml", ".txt", ".ps1", ".sh", ".csv", ".ipynb"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            result.update(chunk)
    return result.hexdigest()


def safe_path(base: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"..", ".git"} or ":" in part for part in parts):
        raise ValueError(f"Unsafe relative path: {relative}")
    result = base.joinpath(*parts).resolve()
    if not result.is_relative_to(base.resolve()):
        raise ValueError(f"Path escapes destination: {relative}")
    return result


def save_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def connect(password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.load_host_keys(str(Path.home() / ".ssh" / "known_hosts"))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect("192.168.194.86", port=722, username="support", password=password,
                   look_for_keys=False, allow_agent=False, timeout=30, auth_timeout=30,
                   banner_timeout=30, compress=True)
    client.get_transport().set_keepalive(20)
    return client


def remote_manifest(password: str) -> dict:
    code = '''import os,json,hashlib,subprocess
from pathlib import Path
from datetime import datetime,timezone
root=Path.cwd()
excluded=EXCLUDED_VALUE
files=[]
for directory,children,names in os.walk(root):
    children[:]=[name for name in children if name not in excluded and not (Path(directory)/name).is_symlink()]
    for name in names:
        path=Path(directory)/name
        if path.is_symlink() or name==".env" or name.startswith(".env."):
            continue
        before=path.stat()
        digest=hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda:handle.read(1048576),b""):
                digest.update(chunk)
        after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise RuntimeError("File changed during inventory: "+str(path))
        files.append({"path":path.relative_to(root).as_posix(),"size":after.st_size,"mtime":after.st_mtime,"sha256":digest.hexdigest()})
head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
print(json.dumps({"created_at_utc":datetime.now(timezone.utc).isoformat(),"remote_root":str(root),"git_head":head,"files":files}))
'''.replace("EXCLUDED_VALUE", repr(EXCLUDED))
    import shlex
    with connect(password) as client:
        command = "cd " + shlex.quote(REMOTE_ROOT) + " && python3 -c " + shlex.quote(code)
        stdin, stdout, stderr = client.exec_command(command, timeout=600)
        payload = stdout.read()
        status = stdout.channel.recv_exit_status()
        if status:
            raise RuntimeError("Remote inventory failed: " + stderr.read().decode()[-1000:])
        return json.loads(payload)


def is_project_text(relative: str) -> bool:
    source_file = relative.split("/")[0] not in {"data", "logs", "temp"} or relative.startswith("data/samples/")
    return source_file and Path(relative).suffix.lower() in TEXT_SUFFIXES


def refresh_entry(client: paramiko.SSHClient, relative: str) -> dict:
    import shlex
    code = 'import sys,json,hashlib; from pathlib import Path; path=Path(sys.argv[1]); before=path.stat(); digest=hashlib.sha256(); handle=path.open("rb"); [digest.update(chunk) for chunk in iter(lambda:handle.read(1048576),b"")]; handle.close(); after=path.stat(); assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns); print(json.dumps({"path":sys.argv[1],"size":after.st_size,"mtime":after.st_mtime,"sha256":digest.hexdigest()}))'
    command = "cd " + shlex.quote(REMOTE_ROOT) + " && python3 -c " + shlex.quote(code) + " " + shlex.quote(relative)
    stdin, stdout, stderr = client.exec_command(command, timeout=300)
    payload = stdout.read()
    if stdout.channel.recv_exit_status():
        raise RuntimeError("Could not refresh changing remote file")
    return json.loads(payload)


def install(entry: dict, temporary: Path, work: Path, common_head: bool) -> str:
    relative = entry["path"]
    target = safe_path(ROOT, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and digest(target) == entry["sha256"]:
        temporary.unlink()
        return "identical"
    if target.exists() and is_project_text(relative):
        local_bytes = target.read_bytes()
        remote_bytes = temporary.read_bytes()
        normalize = lambda value: value.decode("utf-8-sig").replace("\r\n", "\n")
        try:
            local_text = normalize(local_bytes)
            remote_text = normalize(remote_bytes)
            if local_text == remote_text:
                temporary.unlink()
                return "equivalent_text"
            if relative == "config/pipeline_config.yml":
                for key in ("etl_parquet_dir", "analytics_parquet", "nlp_repo"):
                    pattern = "^" + key + ":.*$"
                    match = re.search(pattern, local_text, re.MULTILINE)
                    if match:
                        remote_text = re.sub(pattern, lambda found: match.group(), remote_text, flags=re.MULTILINE)
            baseline = subprocess.run(["git", "show", "HEAD:" + relative], cwd=ROOT, capture_output=True)
            if common_head and baseline.returncode == 0:
                base_text = normalize(baseline.stdout)
                if remote_text == base_text or remote_text == local_text:
                    temporary.unlink()
                    return "local_changes_preserved"
                base_file = temporary.with_suffix(".base")
                local_file = temporary.with_suffix(".local")
                remote_file = temporary.with_suffix(".remote")
                base_file.write_text(base_text, encoding="utf-8")
                local_file.write_text(local_text, encoding="utf-8")
                remote_file.write_text(remote_text, encoding="utf-8")
                merged = subprocess.run(["git", "merge-file", "-p", str(local_file), str(base_file), str(remote_file)], capture_output=True)
                for scratch in (base_file, local_file, remote_file):
                    scratch.unlink()
                if merged.returncode == 0:
                    temporary.write_bytes(merged.stdout)
                    backup = safe_path(work / "backups", relative)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup)
                    temporary.replace(target)
                    return "merged_preserving_local_changes"
        except UnicodeError:
            pass
        incoming = safe_path(work / "conflicts", relative)
        incoming.parent.mkdir(parents=True, exist_ok=True)
        temporary.replace(incoming)
        return "conflict_remote_version_saved"
    if target.exists():
        backup = safe_path(work / "backups", relative)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(target, backup)
    temporary.replace(target)
    os.utime(target, (entry["mtime"], entry["mtime"]))
    return "updated" if (work / "backups" / relative).exists() else "downloaded"


def worker(work: Path, password: str, workers: int) -> str:
    manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
    state_path = work / "state.json"
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    results = previous.get("results", {})
    resolutions_path = work / "resolutions.json"
    if resolutions_path.exists():
        resolutions = json.loads(resolutions_path.read_text(encoding="utf-8"))
        for relative, resolution in resolutions.items():
            if not is_project_text(relative) or digest(safe_path(ROOT, relative)) != resolution["local_sha256"]:
                raise ValueError(f"Manual resolution no longer matches local file: {relative}")
            incoming = safe_path(work / "conflicts", relative)
            if digest(incoming) != resolution["remote_sha256"]:
                raise ValueError(f"Manual resolution no longer matches incoming file: {relative}")
            results[relative] = {"status": "local_platform_fix_preserved", **resolution}
    local_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    common_head = local_head == manifest["git_head"]
    lock = threading.Lock()
    started = previous.get("started_at_utc", utcnow())
    active = {}
    transferred = {}

    def checkpoint(phase: str) -> None:
        snapshot = {"started_at_utc": started, "updated_at_utc": utcnow(), "phase": phase,
                    "pid": os.getpid(), "manifest_files": len(manifest["files"]),
                    "manifest_bytes": sum(entry["size"] for entry in manifest["files"]),
                    "common_git_head": common_head, "completed_files": len(results),
                    "active": dict(active), "transferred_bytes_this_run": sum(transferred.values()),
                    "results": results}
        save_json(state_path, snapshot)

    pending = []
    for entry in manifest["files"]:
        relative = entry["path"]
        if relative in results and results[relative].get("status") != "error":
            continue
        target = safe_path(ROOT, relative)
        if target.is_file() and target.stat().st_size == entry["size"] and digest(target) == entry["sha256"]:
            results[relative] = {"status": "identical", "bytes": entry["size"]}
        else:
            pending.append(entry)
    pending.sort(key=lambda entry: (
        0 if is_project_text(entry["path"]) else 1 if entry["path"].startswith("data/processed/consolidated_predictions/") else 2,
        entry["size"],
    ))
    with lock:
        checkpoint("downloading")
    queue = iter(pending)

    def transfer_loop(index: int) -> None:
        client = None
        sftp = None
        while True:
            with lock:
                entry = next(queue, None)
            if entry is None:
                break
            relative = entry["path"]
            temporary = safe_path(work / "partials", relative + ".part")
            temporary.parent.mkdir(parents=True, exist_ok=True)
            for attempt in range(1, 9):
                try:
                    if client is None or not client.get_transport().is_active():
                        if client is not None:
                            client.close()
                        client = connect(password)
                        sftp = paramiko.SFTPClient.from_transport(client.get_transport(), window_size=16777216, max_packet_size=65536)
                        sftp.get_channel().settimeout(120)
                    remote = posixpath.join(REMOTE_ROOT, relative)
                    stat = sftp.stat(remote)
                    if stat.st_size != entry["size"] or abs(stat.st_mtime - entry["mtime"]) >= 1:
                        refreshed = refresh_entry(client, relative)
                        with lock:
                            entry.update(refreshed)
                            save_json(work / "manifest.json", manifest)
                        if temporary.exists():
                            temporary.replace(temporary.with_name(temporary.name + ".previous." + str(time.time_ns())))
                    offset = temporary.stat().st_size if temporary.exists() else 0
                    if offset > entry["size"]:
                        raise RuntimeError("Partial file exceeds expected size")
                    with lock:
                        active[str(index)] = {"path": relative, "bytes": offset, "total": entry["size"]}
                        checkpoint("downloading")
                    with sftp.open(remote, "rb") as source, temporary.open("ab") as destination:
                        source.seek(offset)
                        source.prefetch(entry["size"], max_concurrent_requests=16)
                        last_update = time.monotonic()
                        while True:
                            chunk = source.read(262144)
                            if not chunk:
                                break
                            destination.write(chunk)
                            offset += len(chunk)
                            with lock:
                                transferred[relative] = transferred.get(relative, 0) + len(chunk)
                                active[str(index)]["bytes"] = offset
                                if time.monotonic() - last_update > 5:
                                    checkpoint("downloading")
                                    last_update = time.monotonic()
                    if offset != entry["size"] or digest(temporary) != entry["sha256"]:
                        temporary.replace(temporary.with_name(temporary.name + ".invalid." + str(time.time_ns())))
                        raise RuntimeError("SHA256 or size mismatch")
                    status = install(entry, temporary, work, common_head)
                    with lock:
                        results[relative] = {"status": status, "bytes": entry["size"], "sha256": entry["sha256"]}
                        active.pop(str(index), None)
                        checkpoint("downloading")
                    print(utcnow(), status, relative, flush=True)
                    break
                except Exception as error:
                    print(utcnow(), "RETRY", relative, attempt, type(error).__name__, str(error)[:180], flush=True)
                    if client is not None:
                        client.close()
                    client = None
                    if attempt == 8:
                        with lock:
                            results[relative] = {"status": "error", "error": type(error).__name__, "message": str(error)[:180]}
                            active.pop(str(index), None)
                            checkpoint("downloading")
                    else:
                        time.sleep(min(attempt * 5, 30))
        if client is not None:
            client.close()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(transfer_loop, index) for index in range(workers)]
        for future in as_completed(futures):
            future.result()
    statuses = [item["status"] for item in results.values()]
    phase = "needs_retry" if "error" in statuses else "complete_with_code_conflicts" if "conflict_remote_version_saved" in statuses else "complete"
    with lock:
        checkpoint(phase)
    print(utcnow(), "FINISHED", phase, flush=True)
    return phase


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely pull the remote project with resumable, verified transfers.")
    parser.add_argument("--detach", action="store_true")
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("workers must be between 1 and 8")
    if args.worker:
        password = json.loads(sys.stdin.readline())["password"]
        while worker(args.worker.resolve(), password, args.workers) == "needs_retry":
            time.sleep(30)
        return 0
    password = getpass.getpass("SSH password: ")
    if args.resume:
        work = args.resume.resolve()
    else:
        work = ROOT / "logs" / "remote_sync" / datetime.now().strftime("%Y%m%d_%H%M%S")
        work.mkdir(parents=True, exist_ok=False)
        print("Building remote SHA256 inventory...", flush=True)
        manifest = remote_manifest(password)
        save_json(work / "manifest.json", manifest)
        print("Inventory:", len(manifest["files"]), "files,", sum(entry["size"] for entry in manifest["files"]), "bytes", flush=True)
    if args.detach:
        log = (work / "sync.log").open("ab")
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(work), "--workers", str(args.workers)]
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, **options)
        process.stdin.write((json.dumps({"password": password}) + "\n").encode())
        process.stdin.close()
        log.close()
        print(json.dumps({"worker_pid": process.pid, "work_dir": str(work), "state": str(work / "state.json")}), flush=True)
        return 0
    worker(work, password, args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
