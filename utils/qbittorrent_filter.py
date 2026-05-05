import json
import os
import re
import time
import traceback
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set
import requests

CONFIG_DEFAULT = {
    # Tag torrents once processed to avoid re-processing
    "processed_tag": "auto_mainfile_done",

    # Thresholds
    "single_dominant_ratio": 0.95,
    "group_dominant_sum_ratio": 0.95,
    "group_size_similarity_tol": 0.12,
    "group_min_files": 2,
    "min_files_to_consider": 2,

    # Filters (optional, strongly recommended)
    # If True: only process torrents that are paused (so you can review before start)
    "only_process_paused": False,
    # If True: only process torrents with 0 downloaded bytes (freshly added)
    "only_process_zero_downloaded": False,

    # Episode protection
    "episode_protection_enabled": True,
    "episode_min_matches": 3,
    "episode_match_ratio": 0.35,

    # Archive preference
    "archive_preference_enabled": True,
    "archive_min_matches": 2,

    "prefer_deselect_ext": [
        ".url", ".txt", ".nfo", ".jpg", ".jpeg", ".png", ".gif",
        ".html", ".htm", ".lnk", ".exe"
    ],

}

CONFIG_TEMPLATE = {
    "instances": [
        {
            "name": "local",
            "base_url": "http://127.0.0.1:8080",
            "username": "admin",
            "password": "your_password_here",
            "verify_tls": True
        },
        {
            "name": "nas",
            "base_url": "http://192.168.1.100:8085",
            "username": "your_username",
            "password": "your_password",
            "verify_tls": True
        }
    ]
}

def write_config_template(cfg_path: str) -> None:
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(CONFIG_TEMPLATE, f, indent=2)
        f.write("\n")

def load_config() -> Dict:
    cfg_path = os.environ.get(
        "QBT_FILTER_CONFIG",
        os.path.join(os.path.dirname(__file__), "qbittorrent_filter_config.json"),
    )
    if not os.path.isfile(cfg_path):
        write_config_template(cfg_path)
        raise RuntimeError(
            "Config file not found. A template was created. Update it and re-run."
        )
    with open(cfg_path, "r", encoding="utf-8") as f:
        user_cfg = json.load(f)

    cfg = dict(CONFIG_DEFAULT)
    instances = user_cfg.get("instances") if isinstance(user_cfg, dict) else None
    if isinstance(instances, list):
        cfg["instances"] = instances
    else:
        cfg["instances"] = None
    if user_cfg:
        for key in user_cfg:
            if key != "instances":
                cfg[key] = user_cfg[key]
    instances = cfg.get("instances")
    if not isinstance(instances, list) or not instances:
        raise RuntimeError("Config must include a non-empty 'instances' list.")
    return cfg

@dataclass
class QBFile:
    fid: int
    name: str
    size: int
    priority: int

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
        r = self.sess.post(
            self._url("/api/v2/auth/login"),
            data={"username": self.username, "password": self.password},
            timeout=15,
            verify=self.verify_tls,
        )
        if r.status_code != 200 or "Ok" not in r.text:
            raise RuntimeError(f"[{self.name}] login failed: status={r.status_code}, body={r.text!r}")

    def torrents_info(self) -> List[Dict]:
        r = self.sess.get(self._url("/api/v2/torrents/info"), timeout=20, verify=self.verify_tls)
        r.raise_for_status()
        return r.json()

    def torrent_files(self, h: str) -> List[QBFile]:
        r = self.sess.get(
            self._url("/api/v2/torrents/files"),
            params={"hash": h},
            timeout=30,
            verify=self.verify_tls,
        )
        r.raise_for_status()
        data = r.json()
        out: List[QBFile] = []
        for f in data:
            fid_raw = f.get("id", None)
            if fid_raw is None:
                fid_raw = f.get("index", None)   # <-- add this for qB 4.x compatibility
            if fid_raw is None:
                continue

            out.append(QBFile(
                fid=int(fid_raw),
                name=str(f.get("name", "")),
                size=int(f.get("size", 0)),
                priority=int(f.get("priority", 1)),
            ))
        return out

    def set_file_priority(self, h: str, file_ids: List[int], priority: int) -> None:
        for fid in file_ids:
            r = self.sess.post(
                self._url("/api/v2/torrents/filePrio"),
                data={"hash": h, "id": fid, "priority": priority},
                timeout=20,
                verify=self.verify_tls,
            )
            r.raise_for_status()

    def add_tag(self, hashes: str, tag: str) -> None:
        r = self.sess.post(
            self._url("/api/v2/torrents/addTags"),
            data={"hashes": hashes, "tags": tag},
            timeout=20,
            verify=self.verify_tls,
        )
        r.raise_for_status()

def normalize_name(name: str) -> str:
    return name.lower().replace("\\", "/").strip()

def file_ext(name: str) -> str:
    n = normalize_name(name)
    dot = n.rfind(".")
    return "" if dot == -1 else n[dot:]

EPISODE_PATTERNS = [
    re.compile(r"\bs\d{1,2}\s*[.\- _]?\s*e\d{1,3}\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s*x\s*\d{1,3}\b", re.IGNORECASE),
    re.compile(r"\bep?\s*\d{1,3}\b", re.IGNORECASE),
]

ARCHIVE_VOLUME_PATTERNS = [
    re.compile(r"\.part\d{1,3}\.rar$", re.IGNORECASE),
    re.compile(r"\.r\d{2,3}$", re.IGNORECASE),
    re.compile(r"\.z\d{2,3}$", re.IGNORECASE),
    re.compile(r"\.(7z|zip|rar)\.\d{3}$", re.IGNORECASE),
    re.compile(r"\.\d{3}$", re.IGNORECASE),
]

def looks_like_archive_volume(name: str) -> bool:
    n = normalize_name(name)
    return any(p.search(n) for p in ARCHIVE_VOLUME_PATTERNS)

def looks_like_episode(name: str) -> bool:
    n = normalize_name(name)
    if looks_like_archive_volume(n):
        return False
    return any(p.search(n) for p in EPISODE_PATTERNS)

def is_episodic_set(files: List[QBFile], cfg: Dict) -> bool:
    if not cfg.get("episode_protection_enabled", True):
        return False
    total = len(files)
    if total <= 0:
        return False
    matches = sum(1 for f in files if looks_like_episode(f.name))
    if matches < int(cfg.get("episode_min_matches", 3)):
        return False
    return (matches / total) >= float(cfg.get("episode_match_ratio", 0.35))

def find_archive_volume_ids(files: List[QBFile], cfg: Dict) -> Set[int]:
    if not cfg.get("archive_preference_enabled", True):
        return set()
    ids = {f.fid for f in files if looks_like_archive_volume(f.name)}
    if len(ids) >= int(cfg.get("archive_min_matches", 2)):
        return ids
    return set()

def choose_files(files: List[QBFile], cfg: Dict) -> Optional[Tuple[str, List[int], List[int]]]:
    if len(files) < cfg["min_files_to_consider"]:
        return None

    total = sum(f.size for f in files)
    if total <= 0:
        return None

    fs = sorted(files, key=lambda x: x.size, reverse=True)
    largest = fs[0]
    largest_ratio = largest.size / total

    episodic = is_episodic_set(files, cfg)
    archive_ids = find_archive_volume_ids(files, cfg)

    # Group rule first (unless episodic)
    if not episodic:
        target_sum_ratio = float(cfg["group_dominant_sum_ratio"])
        tol = float(cfg["group_size_similarity_tol"])
        group_min = int(cfg["group_min_files"])

        # Prefer archive volumes if detected
        if archive_ids:
            archive_files = sorted([f for f in fs if f.fid in archive_ids], key=lambda x: x.size, reverse=True)
            running = 0
            keep = []
            for f in archive_files:
                keep.append(f.fid)
                running += f.size
                if running / total >= target_sum_ratio:
                    keep_set = set(keep)
                    drop_ids = [f.fid for f in files if f.fid not in keep_set]
                    return ("group_archive", sorted(list(keep_set)), drop_ids)

        # Generic similar-size top-k
        best = None
        for k in range(group_min, len(fs) + 1):
            group = fs[:k]
            max_size = group[0].size
            min_size = group[-1].size
            if max_size <= 0:
                break
            if (max_size - min_size) / max_size > tol:
                break
            group_ratio = sum(x.size for x in group) / total
            if group_ratio >= target_sum_ratio:
                best = [x.fid for x in group]
        if best:
            keep_set = set(best)
            drop_ids = [f.fid for f in files if f.fid not in keep_set]
            return ("group", sorted(list(keep_set)), drop_ids)

    # Single dominant file rule
    if largest_ratio >= float(cfg["single_dominant_ratio"]):
        keep_set = {largest.fid}
        drop_ids = [f.fid for f in files if f.fid not in keep_set]
        return ("single", [largest.fid], drop_ids)

    return None

def torrent_passes_filters(t: Dict, cfg: Dict) -> bool:
    if cfg.get("only_process_paused"):
        # qB state examples: pausedDL, pausedUP, paused, etc.
        state = (t.get("state") or "").lower()
        if "paused" not in state:
            return False

    if cfg.get("only_process_zero_downloaded"):
        downloaded = t.get("downloaded")
        if isinstance(downloaded, (int, float)) and downloaded > 0:
            return False

    return True

def main() -> None:
    cfg = load_config()
    processed_tag = cfg["processed_tag"]

    for inst in cfg["instances"]:
        c = QBClient(
            base_url=inst["base_url"],
            username=inst["username"],
            password=inst["password"],
            verify_tls=bool(inst.get("verify_tls", True)),
            name=inst.get("name") or inst["base_url"],
        )

        print(f"[{c.name}] connecting...", flush=True)
        try:
            c.login()
            print(f"[{c.name}] logged in.", flush=True)
        except Exception as e:
            print(f"[{c.name}] login failed: {e}", flush=True)
            continue

        # Stats
        total = 0
        skipped_tagged = 0
        skipped_filtered = 0
        skipped_too_few_files = 0
        skipped_no_rule = 0
        applied = 0

        try:
            torrents = c.torrents_info()
            total = len(torrents)
            print(f"[{c.name}] fetched {total} torrents", flush=True)

            for t in torrents:
                tags = t.get("tags") or ""
                tag_list = [x.strip() for x in tags.split(",") if x.strip()]
                if processed_tag in tag_list:
                    skipped_tagged += 1
                    continue

                if not torrent_passes_filters(t, cfg):
                    skipped_filtered += 1
                    continue

                h = t.get("hash")
                name = t.get("name", "")
                if not h:
                    continue

                files = c.torrent_files(h)
                if len(files) < cfg["min_files_to_consider"]:
                    skipped_too_few_files += 1
                    continue

                decision = choose_files(files, cfg)
                if decision is None:
                    skipped_no_rule += 1
                    continue

                mode, keep_ids, drop_ids = decision

                if drop_ids:
                    c.set_file_priority(h, drop_ids, 0)
                if keep_ids:
                    c.set_file_priority(h, keep_ids, 1)

                # Optional: extra drop for "ad-like" extensions unless kept
                if cfg.get("prefer_deselect_ext"):
                    keep_set = set(keep_ids)
                    prefer_set = set(x.lower() for x in cfg["prefer_deselect_ext"])
                    extra_drop = []
                    for f in files:
                        if f.fid in keep_set:
                            continue
                        if file_ext(f.name) in prefer_set:
                            extra_drop.append(f.fid)
                    if extra_drop:
                        c.set_file_priority(h, extra_drop, 0)

                c.add_tag(h, processed_tag)
                applied += 1

                tot_size = sum(f.size for f in files) or 1
                kept_size = sum(f.size for f in files if f.fid in set(keep_ids))
                episodic_flag = is_episodic_set(files, cfg)
                print(f"[{c.name}] APPLIED {mode}: {name} | keep {len(keep_ids)} ({kept_size/tot_size:.1%}) "
                      f"drop {len(drop_ids)} | episodic={episodic_flag}", flush=True)

        except Exception as e:
            print(f"[{c.name}] error during processing: {e}", flush=True)
            traceback.print_exc()

        print(
            f"[{c.name}] DONE. total={total}, applied={applied}, "
            f"skipped_tagged={skipped_tagged}, skipped_filtered={skipped_filtered}, "
            f"skipped_too_few_files={skipped_too_few_files}, skipped_no_rule={skipped_no_rule}",
            flush=True
        )

if __name__ == "__main__":
    main()