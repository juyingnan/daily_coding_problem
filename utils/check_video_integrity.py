import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


PROGRESS_TIME_RE = re.compile(r"^out_time_us=(\d+)$")
SHOWINFO_TIME_RE = re.compile(r"\bpts_time:([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
GPU_SETUP_ERROR_MARKERS = (
    "cannot load nvcuda",
    "cuda_error_no_device",
    "device setup failed",
    "failed setup for format cuda",
    "hardware accelerator failed",
    "minimum required nvidia driver",
    "no device available for decoder",
)
ERROR_MARKERS = (
    "corrupt",
    "error",
    "invalid",
    "damaged",
    "missing picture",
    "concealing",
    "decode_slice_header",
    "reference picture missing",
    "co located pocs unavailable",
) + GPU_SETUP_ERROR_MARKERS


@dataclass(frozen=True)
class DecodeIssue:
    timestamp: Optional[float]
    message: str


@dataclass(frozen=True)
class ProblemRange:
    start: float
    end: float
    issue_count: int


def find_ffmpeg(explicit_path: Optional[str] = None) -> Optional[str]:
    candidates = [explicit_path, os.environ.get("FFMPEG_BINARY"), shutil.which("ffmpeg")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_packages.is_dir():
            winget_candidates = sorted(
                winget_packages.glob("Gyan.FFmpeg_*/**/bin/ffmpeg.exe"),
                reverse=True,
            )
            if winget_candidates:
                return str(winget_candidates[0])

    try:
        import imageio_ffmpeg

        candidate = imageio_ffmpeg.get_ffmpeg_exe()
        if candidate and Path(candidate).is_file():
            return candidate
    except (ImportError, RuntimeError):
        pass
    return None


def is_decode_error(line: str) -> bool:
    lowered = line.lower()
    if PROGRESS_TIME_RE.match(line.strip()):
        return False
    return any(marker in lowered for marker in ERROR_MARKERS)


def gpu_setup_failed(issues: Iterable[DecodeIssue]) -> bool:
    return any(
        marker in issue.message.lower()
        for issue in issues
        for marker in GPU_SETUP_ERROR_MARKERS
    )


def decode_issues(
    ffmpeg: str,
    video_path: Path,
    precise_timestamps: bool = False,
    start_time: float = 0.0,
    duration: Optional[float] = None,
    threads: int = 1,
    hardware_acceleration: Optional[str] = None,
) -> tuple[list[DecodeIssue], int]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "info" if precise_timestamps else "warning",
        "-threads",
        str(threads),
    ]
    if start_time > 0:
        command.extend(["-ss", str(start_time)])
    if hardware_acceleration:
        command.extend(["-hwaccel", hardware_acceleration])
    command.extend([
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
        "-an",
        "-sn",
        "-dn",
    ])
    if duration is not None:
        command.extend(["-t", str(duration)])
    if precise_timestamps:
        command.extend(["-vf", "showinfo"])
    else:
        command[3:3] = ["-nostats", "-stats_period", "0.25", "-progress", "pipe:2"]
    command.extend(["-f", "null", "-"])
    issues: list[DecodeIssue] = []
    current_time: Optional[float] = None

    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stderr is not None
    try:
        for line in process.stderr:
            time_match = PROGRESS_TIME_RE.match(line.strip())
            if time_match:
                current_time = start_time + int(time_match.group(1)) / 1_000_000
            elif precise_timestamps and (time_match := SHOWINFO_TIME_RE.search(line)):
                current_time = start_time + max(0.0, float(time_match.group(1)))
            elif is_decode_error(line):
                message = line.strip()
                if message and (not issues or issues[-1].message != message):
                    issues.append(DecodeIssue(current_time, message))
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        raise

    return_code = process.wait()
    if return_code != 0 and not issues:
        issues.append(DecodeIssue(current_time, f"FFmpeg exited with code {return_code}"))
    return issues, return_code


def probe_duration(ffmpeg: str, video_path: Path) -> Optional[float]:
    ffprobe = Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    if not ffprobe.is_file():
        ffprobe_path = shutil.which("ffprobe")
        if not ffprobe_path:
            return None
        ffprobe = Path(ffprobe_path)

    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None
    return duration if result.returncode == 0 and duration > 0 else None


def build_sample_starts(duration: float, interval: float, window: float) -> list[float]:
    if duration <= window:
        return [0.0]

    starts = []
    current = 0.0
    last_start = max(0.0, duration - window)
    while current < last_start:
        starts.append(current)
        current += interval
    if starts and last_start - starts[-1] < window:
        starts[-1] = last_start
    elif not starts or starts[-1] != last_start:
        starts.append(last_start)
    return starts


def sample_decode_issues(
    ffmpeg: str,
    video_path: Path,
    duration: float,
    interval: float,
    window: float,
    context: float,
    threads: int,
    use_gpu: bool = False,
) -> list[DecodeIssue]:
    issues: list[DecodeIssue] = []
    for start_time in build_sample_starts(duration, interval, window):
        window_duration = min(window, duration - start_time)
        quick_issues, _ = decode_issues(
            ffmpeg,
            video_path,
            start_time=start_time,
            duration=window_duration,
            threads=threads,
            hardware_acceleration="cuda" if use_gpu else None,
        )
        if use_gpu and gpu_setup_failed(quick_issues):
            raise RuntimeError(quick_issues[0].message)
        if not quick_issues:
            continue

        scanner = "GPU" if use_gpu else "CPU"
        print(
            f"  {scanner} 在 {format_timestamp(start_time)} 附近发现异常，"
            "正在使用 CPU 精确复检..."
        )
        precise_start = max(0.0, start_time - context)
        precise_end = min(duration, start_time + window_duration + context)
        precise_issues, _ = decode_issues(
            ffmpeg,
            video_path,
            precise_timestamps=True,
            start_time=precise_start,
            duration=precise_end - precise_start,
            threads=threads,
        )
        issues.extend(precise_issues or quick_issues)
    return issues


def merge_problem_ranges(
    issues: Iterable[DecodeIssue],
    merge_gap: float = 2.0,
    context: float = 1.0,
) -> list[ProblemRange]:
    timestamps = sorted(issue.timestamp for issue in issues if issue.timestamp is not None)
    if not timestamps:
        return []

    ranges: list[ProblemRange] = []
    start = timestamps[0]
    end = timestamps[0]
    count = 1
    for timestamp in timestamps[1:]:
        if timestamp - end <= merge_gap:
            end = timestamp
            count += 1
            continue
        ranges.append(ProblemRange(max(0.0, start - context), end + context, count))
        start = end = timestamp
        count = 1
    ranges.append(ProblemRange(max(0.0, start - context), end + context, count))
    return ranges


def format_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def collect_videos(target: Path, recursive: bool) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".mp4" else []
    if not target.is_dir():
        return []
    pattern = "**/*.mp4" if recursive else "*.mp4"
    return sorted(path for path in target.glob(pattern) if path.is_file())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="抽样解码 MP4 视频流，发现异常后精确检测并报告时间区间。"
    )
    parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        default=Path.home() / "Downloads",
        help="MP4 文件或目录，默认是当前用户的 Downloads 目录。",
    )
    parser.add_argument("--ffmpeg", help="FFmpeg 可执行文件路径。")
    parser.add_argument("--no-recursive", action="store_true", help="不扫描子目录。")
    parser.add_argument("--full", action="store_true", help="完整解码每个视频，不进行跳跃抽样。")
    accelerator_group = parser.add_mutually_exclusive_group()
    accelerator_group.add_argument(
        "--gpu",
        dest="gpu",
        action="store_true",
        default=True,
        help="第一遍使用 NVIDIA CUDA 解码（默认），异常区域仍由 CPU 精确复检。",
    )
    accelerator_group.add_argument(
        "--cpu",
        dest="gpu",
        action="store_false",
        help="第一遍也使用 CPU 软件解码。",
    )
    parser.add_argument("--sample-interval", type=float, default=60.0, help="抽样起点间隔秒数。")
    parser.add_argument("--sample-duration", type=float, default=3.0, help="每个抽样窗口解码秒数。")
    parser.add_argument("--threads", type=int, default=1, help="FFmpeg 解码线程数，默认 1。")
    parser.add_argument("--merge-gap", type=float, default=2.0, help="合并相邻错误的最大秒数。")
    parser.add_argument("--context", type=float, default=1.0, help="问题区间前后扩展秒数。")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.sample_interval <= 0 or args.sample_duration <= 0 or args.threads <= 0:
        print("错误：抽样间隔、抽样时长和线程数必须大于 0。")
        return 2
    ffmpeg = find_ffmpeg(args.ffmpeg)
    if not ffmpeg:
        print("错误：找不到 FFmpeg。请安装 FFmpeg，或使用 --ffmpeg 指定 ffmpeg.exe。")
        return 2

    videos = collect_videos(args.target.expanduser().resolve(), not args.no_recursive)
    if not videos:
        print(f"没有找到 MP4 文件：{args.target}")
        return 2

    print(f"使用 FFmpeg：{ffmpeg}")
    if args.full:
        accelerator = "CUDA GPU" if args.gpu else "CPU"
        print(
            f"共发现 {len(videos)} 个 MP4；使用完整检测，第一遍使用 {accelerator}，"
            f"CPU 解码线程数 {args.threads}。"
        )
    else:
        accelerator = "CUDA GPU" if args.gpu else "CPU"
        print(
            f"共发现 {len(videos)} 个 MP4；每 {args.sample_interval:g} 秒抽查 "
            f"{args.sample_duration:g} 秒，第一遍使用 {accelerator}，"
            f"CPU 复检线程数 {args.threads}。"
        )
    files_with_issues = 0
    gpu_enabled = args.gpu

    for index, video_path in enumerate(videos, 1):
        print(f"\n[{index}/{len(videos)}] 正在检测：{video_path}")
        duration = probe_duration(ffmpeg, video_path)
        if duration is None:
            files_with_issues += 1
            print("  发现问题：无法读取视频时长或容器信息。")
            continue

        try:
            if args.full:
                issues, _ = decode_issues(
                    ffmpeg,
                    video_path,
                    threads=args.threads,
                    hardware_acceleration="cuda" if gpu_enabled else None,
                )
                if gpu_enabled and gpu_setup_failed(issues):
                    raise RuntimeError(issues[0].message)
            else:
                issues = sample_decode_issues(
                    ffmpeg,
                    video_path,
                    duration,
                    args.sample_interval,
                    args.sample_duration,
                    args.context,
                    args.threads,
                    use_gpu=gpu_enabled,
                )
        except RuntimeError as error:
            print(f"  CUDA 不可用，自动回退 CPU：{error}")
            gpu_enabled = False
            if args.full:
                issues, _ = decode_issues(ffmpeg, video_path, threads=args.threads)
            else:
                issues = sample_decode_issues(
                    ffmpeg,
                    video_path,
                    duration,
                    args.sample_interval,
                    args.sample_duration,
                    args.context,
                    args.threads,
                )
        if not issues:
            if args.full:
                print("  没问题：视频流可完整解码。")
            else:
                starts = build_sample_starts(duration, args.sample_interval, args.sample_duration)
                sampled = sum(min(args.sample_duration, duration - start) for start in starts)
                coverage = min(100.0, sampled / duration * 100)
                print(f"  抽样未发现问题：检测覆盖约 {coverage:.1f}%。")
            continue

        if args.full:
            print("  检测到解码错误，正在进行第二遍精确定位...")
            precise_issues, _ = decode_issues(
                ffmpeg,
                video_path,
                precise_timestamps=True,
                threads=args.threads,
            )
            if precise_issues:
                issues = precise_issues

        files_with_issues += 1
        ranges = merge_problem_ranges(issues, args.merge_gap, args.context)
        print(f"  发现问题：共记录 {len(issues)} 条解码错误。")
        for problem in ranges:
            print(
                f"  - {format_timestamp(problem.start)} - {format_timestamp(problem.end)} "
                f"({problem.issue_count} 条错误)"
            )
        unknown_count = sum(issue.timestamp is None for issue in issues)
        if unknown_count:
            print(f"  - 另有 {unknown_count} 条错误无法关联到具体时间。")
        for issue in issues[:3]:
            print(f"    FFmpeg: {issue.message}")
        if len(issues) > 3:
            print(f"    ... 其余 {len(issues) - 3} 条错误已省略")

    print("\n检测完成。")
    if files_with_issues:
        print(f"{files_with_issues}/{len(videos)} 个文件发现问题。")
        return 1
    if args.full:
        print(f"全部 {len(videos)} 个文件均没问题。")
    else:
        print(f"全部 {len(videos)} 个文件抽样未发现问题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())