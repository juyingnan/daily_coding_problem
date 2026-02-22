import time
import re
import traceback
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set
import requests

# ============================
# Configuration (edit here)
# ============================

CONFIG = {
    "poll_interval_sec": 10,

    # Tag torrents once processed to avoid re-processing
    "processed_tag": "auto_mainfile_done",

    # Only handle torrents added within this many seconds; 0 = no limit
    "only_handle_added_within_sec": 0,

    # Thresholds (default 95% as requested)
    "single_dominant_ratio": 0.95,          # largest_file / total >= 0.95 -> keep only largest
    "group_dominant_sum_ratio": 0.95,       # sum(group) / total >= 0.95 -> keep group
    "group_size_similarity_tol": 0.12,      # group similarity: (max-min)/max <= 0.12
    "group_min_files": 2,                   # group must have at least N files

    # Do not auto-handle torrents with fewer than this number of files
    "min_files_to_consider": 2,

    # Episode protection: if enough files look like episodes, disable group rule
    "episode_protection_enabled": True,
    "episode_min_matches": 3,               # if >= this many files match episode patterns...
    "episode_match_ratio": 0.35,            # ...and matches/total_files >= this ratio, treat as episodic set

    # Archive volume preference: detect common multi-part archive naming and prefer group selection
    "archive_preference_enabled": True,
    "archive_min_matches": 2,               # if >= this many files match archive volume patterns, consider it multi-part

    # Extensions you'd generally like to never download unless they are explicitly kept by rules
    "prefer_deselect_ext": [
        ".url", ".txt", ".nfo", ".jpg", ".jpeg", ".png", ".gif",
        ".html", ".htm", ".lnk", ".exe"
    ],

    # qBittorrent instances (local + NAS)
    "instances": [
        {
            "name": "local",
            "base_url": "http://127.0.0.1:8080",
            "username": "admin",
            "password": "your_password_here",
            "verify_tls": True,
        },
        {
            "name": "nas",
            "base_url": "http://NAS_IP:8080",
            "username": "admin",
            "password": "your_password_here",
            "verify_tls": True,
        }
    ]
}


# ============================
# Data models
# ============================

@dataclass
class QBFile:
    fid: int
    name: str
    size: int
    priority: int  # 0 = Do not download, 1 = Normal (varies across versions but 0/1 are stable)


# ============================
# qBittorrent Web API client
# ============================

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
            out.append(QBFile(
                fid=int(f.get("id")),
                name=str(f.get("name", "")),
                size=int(f.get("size", 0)),
                priority=int(f.get("priority", 1)),
            ))
        return out

    def set_file_priority(self, h: str, file_ids: List[int], priority: int) -> None:
        # Most compatible approach: set priority per file id
        for fid in file_ids:
            r = self.sess.post(
                self._url("/api/v2/torrents/filePrio"),
                data={"hashes": h, "id": fid, "priority": priority},
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


# ============================
# Helpers: detection & selection
# ============================

def normalize_name(name: str) -> str:
    return name.lower().replace("\\", "/").strip()

def file_ext(name: str) -> str:
    n = normalize_name(name)
    dot = n.rfind(".")
    return "" if dot == -1 else n[dot:]

# Episode patterns:
# - S01E02, s1e2, S01.E02, S01-E02
# - 1x02
# - E03, EP03 (common but riskier; still useful with ratio-based protection)
EPISODE_PATTERNS = [
    re.compile(r"\bs\d{1,2}\s*[.\- _]?\s*e\d{1,3}\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s*x\s*\d{1,3}\b", re.IGNORECASE),
    re.compile(r"\bep?\s*\d{1,3}\b", re.IGNORECASE),
]

def looks_like_episode(name: str) -> bool:
    n = normalize_name(name)
    # Avoid matching episode-like tokens inside obvious archive parts
    if looks_like_archive_volume(n):
        return False
    return any(p.search(n) for p in EPISODE_PATTERNS)

# Archive volume patterns:
# - .part01.rar / .part1.rar
# - .r00 .r01 ... (with .rar)
# - .z01 .z02 ... (with .zip)
# - .001 .002 ... (often with .7z.001, .zip.001, etc.)
ARCHIVE_VOLUME_PATTERNS = [
    re.compile(r"\.part\d{1,3}\.rar$", re.IGNORECASE),
    re.compile(r"\.r\d{2,3}$", re.IGNORECASE),        # r00, r01...
    re.compile(r"\.z\d{2,3}$", re.IGNORECASE),        # z01, z02...
    re.compile(r"\.(7z|zip|rar)\.\d{3}$", re.IGNORECASE),  # 7z.001, zip.001, rar.001
    re.compile(r"\.\d{3}$", re.IGNORECASE),           # .001 .002 (generic, last resort)
]

def looks_like_archive_volume(name: str) -> bool:
    n = normalize_name(name)
    return any(p.search(n) for p in ARCHIVE_VOLUME_PATTERNS)

def find_archive_volume_ids(files: List[QBFile], cfg: Dict) -> Set[int]:
    if not cfg.get("archive_preference_enabled", True):
        return set()
    ids = set()
    for f in files:
        if looks_like_archive_volume(f.name):
            ids.add(f.fid)
    if len(ids) >= int(cfg.get("archive_min_matches", 2)):
        return ids
    return set()

def is_episodic_set(files: List[QBFile], cfg: Dict) -> bool:
    if not cfg.get("episode_protection_enabled", True):
        return False
    total = len(files)
    if total <= 0:
        return False

    matches = sum(1 for f in files if looks_like_episode(f.name))
    if matches < int(cfg.get("episode_min_matches", 3)):
        return False

    ratio = matches / total
    return ratio >= float(cfg.get("episode_match_ratio", 0.35))

def choose_files(files: List[QBFile], cfg: Dict) -> Optional[Tuple[str, List[int], List[int]]]:
    """
    Returns:
      ("single", keep_ids, drop_ids) or ("group", keep_ids, drop_ids)
    Returns None if no rule matches.
    """

    if len(files) < cfg["min_files_to_consider"]:
        return None

    total = sum(f.size for f in files)
    if total <= 0:
        return None

    # Sort descending by size
    fs = sorted(files, key=lambda x: x.size, reverse=True)
    largest = fs[0]
    largest_ratio = largest.size / total

    episodic = is_episodic_set(files, cfg)

    # Detect archive volumes (if present, we prefer grouping those parts)
    archive_ids = find_archive_volume_ids(files, cfg)

    # ----------------------------
    # Group rule (multi-part / similarly sized major files)
    # ----------------------------
    # Disable group rule for episodic torrents to reduce false positives.
    if not episodic:
        tol = float(cfg["group_size_similarity_tol"])
        group_min = int(cfg["group_min_files"])
        target_sum_ratio = float(cfg["group_dominant_sum_ratio"])

        # If archive volumes are detected, try to build a keep-set primarily from them.
        if archive_ids:
            # Keep the archive parts that collectively cover enough of total size.
            # Strategy: choose archive files sorted by size until sum ratio >= target.
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
            # If archive parts exist but don't reach ratio, fall through to generic group/single rules.

        # Generic "top-k similar size" grouping
        best_group = None  # (k, ratio, ids)
        for k in range(group_min, len(fs) + 1):
            group = fs[:k]
            max_size = group[0].size
            min_size = group[-1].size
            if max_size <= 0:
                break

            # Similar size check
            if (max_size - min_size) / max_size > tol:
                break  # further k will only get smaller, so stop

            group_sum = sum(x.size for x in group)
            group_ratio = group_sum / total
            if group_ratio >= target_sum_ratio:
                best_group = (k, group_ratio, [x.fid for x in group])

        if best_group is not None:
            keep_set = set(best_group[2])
            drop_ids = [f.fid for f in files if f.fid not in keep_set]
            return ("group", sorted(list(keep_set)), drop_ids)

    # ----------------------------
    # Single dominant file rule
    # ----------------------------
    if largest_ratio >= float(cfg["single_dominant_ratio"]):
        keep_set = {largest.fid}
        drop_ids = [f.fid for f in files if f.fid not in keep_set]
        return ("single", [largest.fid], drop_ids)

    return None


def should_handle(t: Dict, cfg: Dict) -> bool:
    tags = t.get("tags") or ""
    tag_list = [x.strip() for x in tags.split(",") if x.strip()]
    if cfg["processed_tag"] in tag_list:
        return False

    sec = int(cfg.get("only_handle_added_within_sec", 0))
    if sec > 0:
        added_on = t.get("added_on")
        if isinstance(added_on, int):
            now = int(time.time())
            if now - added_on > sec:
                return False

    return True


# ============================
# Main loop
# ============================

def main() -> None:
    cfg = CONFIG
    poll = int(cfg["poll_interval_sec"])
    processed_tag = cfg["processed_tag"]

    clients: List[QBClient] = []
    for inst in cfg["instances"]:
        clients.append(QBClient(
            base_url=inst["base_url"],
            username=inst["username"],
            password=inst["password"],
            verify_tls=bool(inst.get("verify_tls", True)),
            name=inst.get("name") or inst["base_url"],
        ))

    # Login once at start
    for c in clients:
        c.login()
        print(f"[{c.name}] logged in.")

    print("Running... Press Ctrl+C to stop.")
    while True:
        for c in clients:
            try:
                torrents = c.torrents_info()
                for t in torrents:
                    if not should_handle(t, cfg):
                        continue

                    h = t.get("hash")
                    name = t.get("name", "")
                    if not h:
                        continue

                    files = c.torrent_files(h)
                    decision = choose_files(files, cfg)
                    if decision is None:
                        continue

                    mode, keep_ids, drop_ids = decision

                    # Apply priorities: drop -> 0 (do not download), keep -> 1 (normal)
                    if drop_ids:
                        c.set_file_priority(h, drop_ids, 0)
                    if keep_ids:
                        c.set_file_priority(h, keep_ids, 1)

                    # Enforce deselect on preferred ad/metadata extensions unless explicitly kept
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

                    # Mark processed
                    c.add_tag(h, processed_tag)

                    total = sum(f.size for f in files) or 1
                    kept = sum(f.size for f in files if f.fid in set(keep_ids))
                    episodic_flag = is_episodic_set(files, cfg)
                    print(f"[{c.name}] {mode}: {name} | keep {len(keep_ids)} files ({kept/total:.1%}) "
                          f"drop {len(drop_ids)} | episodic={episodic_flag}")

            except Exception as e:
                print(f"[{c.name}] error: {e}")
                traceback.print_exc()

        time.sleep(poll)


if __name__ == "__main__":
    main()