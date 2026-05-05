r"""
README
======

Purpose:
- Connect to the local qBittorrent Web UI instance.
- Find completed torrents.
- Physically move their downloaded files/folders into `E:\Downloads\TEMP`.

Important:
- This script does not call qBittorrent's built-in move-location API.
- It performs a literal filesystem move via `shutil.move`.
- After a successful real move, it adds the tag `moved_to_temp` so the same torrent is skipped next time.
- In `--dry-run` mode, nothing is moved and no tag is added.

Examples:
- Preview all completed moves:
    python utils/qbittorrent_move_completed_to_temp.py --dry-run
- Only process completed torrents with a specific tag:
    python utils/qbittorrent_move_completed_to_temp.py --dry-run --has-tag mytag
- Only process a category:
    python utils/qbittorrent_move_completed_to_temp.py --category movies

Filters:
- `--dry-run`     Show source and destination without moving anything.
- `--has-tag`     Only process torrents already containing a given tag.
- `--category`    Only process torrents whose category exactly matches the given value.

Notes:
- If a destination name already exists, the script appends `__1`, `__2`, etc.
- The script reads connection settings from `qbittorrent_filter_config.json` and uses the `local` instance.
"""

import argparse
import json
import os
import shutil
import traceback
from pathlib import Path
from typing import Dict, List

import requests

CONFIG_TEMPLATE = {
    "instances": [
        {
            "name": "local",
            "base_url": "http://127.0.0.1:8080",
            "username": "admin",
            "password": "your_password_here",
            "verify_tls": True,
        }
    ]
}

TARGET_DIR = Path(r"E:\Downloads\TEMP")
PROCESSED_TAG = "moved_to_temp"
SKIP_EXTENSIONS = {".txt", ".nfo", ".html", ".htm", ".url", ".jpg", ".jpeg", ".png", ".gif"}
SKIP_NAME_PATTERNS = [
]


def format_size(num_bytes: int) -> str:
    mb = num_bytes / (1024 * 1024)
    gb = num_bytes / (1024 * 1024 * 1024)
    if gb >= 1:
        return f"{gb:.2f} GB"
    return f"{mb:.2f} MB"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move completed local qBittorrent content to E:/Downloads/TEMP."
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be moved without moving files")
    parser.add_argument(
        "--min-size-mb",
        type=float,
        default=50.0,
        help="Only move files whose size is at least this many MB (default: 50)",
    )
    parser.add_argument(
        "--has-tag",
        default="",
        help="Only process torrents that already have this tag",
    )
    parser.add_argument(
        "--category",
        default="",
        help="Only process torrents whose category exactly matches this value",
    )
    return parser.parse_args()


class QBClient:
    def __init__(self, base_url: str, username: str, password: str, verify_tls: bool = True, name: str = ""):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_tls = verify_tls
        self.sess = requests.Session()
        self.name = name or base_url

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def login(self) -> None:
        response = self.sess.post(
            self._url("/api/v2/auth/login"),
            data={"username": self.username, "password": self.password},
            timeout=15,
            verify=self.verify_tls,
        )
        if response.status_code != 200 or "Ok" not in response.text:
            raise RuntimeError(f"[{self.name}] login failed: status={response.status_code}, body={response.text!r}")

    def torrents_info(self) -> List[Dict]:
        response = self.sess.get(self._url("/api/v2/torrents/info"), timeout=20, verify=self.verify_tls)
        response.raise_for_status()
        return response.json()

    def add_tag(self, hashes: str, tag: str) -> None:
        response = self.sess.post(
            self._url("/api/v2/torrents/addTags"),
            data={"hashes": hashes, "tags": tag},
            timeout=20,
            verify=self.verify_tls,
        )
        response.raise_for_status()


def write_config_template(cfg_path: Path) -> None:
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with cfg_path.open("w", encoding="utf-8") as handle:
        json.dump(CONFIG_TEMPLATE, handle, indent=2)
        handle.write("\n")



def load_local_instance() -> Dict:
    cfg_path = Path(
        os.environ.get(
            "QBT_FILTER_CONFIG",
            Path(__file__).with_name("qbittorrent_filter_config.json"),
        )
    )
    if not cfg_path.is_file():
        write_config_template(cfg_path)
        raise RuntimeError("Config file not found. A template was created. Update it and re-run.")

    with cfg_path.open("r", encoding="utf-8") as handle:
        user_cfg = json.load(handle)

    instances = user_cfg.get("instances") if isinstance(user_cfg, dict) else None
    if not isinstance(instances, list) or not instances:
        raise RuntimeError("Config must include a non-empty 'instances' list.")

    for inst in instances:
        if (inst.get("name") or "").lower() == "local":
            return inst
    return instances[0]



def is_completed_torrent(torrent: Dict) -> bool:
    progress = torrent.get("progress")
    amount_left = torrent.get("amount_left")
    completion_on = torrent.get("completion_on")
    state = (torrent.get("state") or "").lower()

    if isinstance(progress, (int, float)) and progress >= 1:
        return True
    if isinstance(amount_left, (int, float)) and amount_left == 0:
        return True
    if isinstance(completion_on, int) and completion_on > 0:
        return True
    return state in {"uploading", "stalledup", "pausedup", "queuedup", "forcedup"}



def unique_destination(target_dir: Path, source_name: str) -> Path:
    candidate = target_dir / source_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        alt = target_dir / f"{stem}__{index}{suffix}"
        if not alt.exists():
            return alt
        index += 1


def resolve_source_path(torrent: Dict) -> Path | None:
    name = (torrent.get("name") or "").strip()
    content_path_raw = torrent.get("content_path")
    save_path_raw = torrent.get("save_path")

    candidates: List[Path] = []
    if content_path_raw:
        candidates.append(Path(content_path_raw))
    if save_path_raw and name:
        candidates.append(Path(save_path_raw) / name)

    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return None


def iter_files_to_move(source_path: Path) -> List[Path]:
    if source_path.is_file():
        return [source_path]
    if source_path.is_dir():
        return [path for path in source_path.rglob("*") if path.is_file()]
    return []


def should_skip_file(file_path: Path) -> bool:
    if file_path.suffix.lower() in SKIP_EXTENSIONS:
        return True

    lowered_name = file_path.name.lower()
    compact_name = "".join(lowered_name.split())
    return any("".join(pattern.lower().split()) in compact_name for pattern in SKIP_NAME_PATTERNS)


def move_torrent_content(torrent: Dict, target_dir: Path, dry_run: bool, min_size_bytes: int) -> tuple[bool, int, int]:
    name = torrent.get("name") or torrent.get("hash") or "unknown"
    source_path = resolve_source_path(torrent)
    if source_path is None:
        if not dry_run:
            print(
                f"[skip] source not found: {name} | content_path={torrent.get('content_path', '')!r} | save_path={torrent.get('save_path', '')!r}",
                flush=True,
            )
        return False, 0, 0

    target_dir.mkdir(parents=True, exist_ok=True)
    files_to_move = iter_files_to_move(source_path)
    if not files_to_move:
        if not dry_run:
            print(f"[skip] no files found to move: {source_path}", flush=True)
        return False, 0, 0

    moved_any = False
    moved_bytes = 0
    skipped_bytes = 0
    for file_path in files_to_move:
        file_size = file_path.stat().st_size
        if should_skip_file(file_path):
            skipped_bytes += file_size
            if not dry_run:
                print(f"[skip-file] {file_path}", flush=True)
            continue
        if file_size < min_size_bytes:
            skipped_bytes += file_size
            if not dry_run:
                print(f"[skip-file] {file_path} | below min size", flush=True)
            continue
        destination = unique_destination(target_dir, file_path.name)
        if dry_run:
            print(f"[dry-run] {file_path} -> {destination}", flush=True)
            moved_any = True
            moved_bytes += file_size
            continue
        shutil.move(str(file_path), str(destination))
        print(f"[moved] {file_path} -> {destination}", flush=True)
        moved_any = True
        moved_bytes += file_size

    if moved_any and not dry_run and source_path.is_dir():
        for folder in sorted((path for path in source_path.rglob("*") if path.is_dir()), reverse=True):
            try:
                folder.rmdir()
            except OSError:
                pass
        try:
            source_path.rmdir()
        except OSError:
            pass

    return moved_any, moved_bytes, skipped_bytes


def torrent_matches_filters(torrent: Dict, required_tag: str, required_category: str) -> bool:
    if required_tag:
        tags = torrent.get("tags") or ""
        tag_list = [x.strip() for x in tags.split(",") if x.strip()]
        if required_tag not in tag_list:
            return False

    if required_category:
        category = torrent.get("category") or ""
        if category != required_category:
            return False

    return True



def main() -> None:
    args = parse_args()
    min_size_bytes = int(args.min_size_mb * 1024 * 1024)
    inst = load_local_instance()
    client = QBClient(
        base_url=inst["base_url"],
        username=inst["username"],
        password=inst["password"],
        verify_tls=bool(inst.get("verify_tls", True)),
        name=inst.get("name") or inst["base_url"],
    )

    print(f"[{client.name}] connecting...", flush=True)
    client.login()
    print(f"[{client.name}] logged in.", flush=True)

    moved = 0
    skipped_incomplete = 0
    skipped_tagged = 0
    skipped_filter = 0
    skipped_failed = 0
    moved_total_bytes = 0
    skipped_total_bytes = 0

    torrents = client.torrents_info()
    print(f"[{client.name}] fetched {len(torrents)} torrents", flush=True)

    for torrent in torrents:
        tags = torrent.get("tags") or ""
        tag_list = [x.strip() for x in tags.split(",") if x.strip()]
        if PROCESSED_TAG in tag_list:
            skipped_tagged += 1
            continue

        if not torrent_matches_filters(torrent, args.has_tag, args.category):
            skipped_filter += 1
            continue

        if not is_completed_torrent(torrent):
            skipped_incomplete += 1
            continue

        try:
            moved_any, moved_bytes, skipped_bytes = move_torrent_content(
                torrent,
                TARGET_DIR,
                args.dry_run,
                min_size_bytes,
            )
            moved_total_bytes += moved_bytes
            skipped_total_bytes += skipped_bytes
            if moved_any:
                moved += 1
                torrent_hash = torrent.get("hash")
                if torrent_hash and not args.dry_run:
                    client.add_tag(torrent_hash, PROCESSED_TAG)
            else:
                skipped_failed += 1
        except Exception as exc:  # noqa: BLE001
            skipped_failed += 1
            print(f"[error] failed to move {torrent.get('name', '')}: {exc}", flush=True)
            traceback.print_exc()

    print(
        f"[{client.name}] DONE. moved={moved}, skipped_incomplete={skipped_incomplete}, "
        f"skipped_tagged={skipped_tagged}, skipped_filter={skipped_filter}, "
        f"skipped_failed={skipped_failed}, moved_size={format_size(moved_total_bytes)}, "
        f"skipped_size={format_size(skipped_total_bytes)}, dry_run={args.dry_run}, target={TARGET_DIR}",
        flush=True,
    )


if __name__ == "__main__":
    main()
