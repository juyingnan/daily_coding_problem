from pathlib import Path
import argparse


# 默认处理目录
# Windows 示例：
DEFAULT_DIRECTORY = r'E:\ARCHIVE'

# macOS / Linux 示例：
# DEFAULT_DIRECTORY = "/Users/yourname/Videos"


VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".wmv",
    ".flv", ".webm", ".m4v", ".ts", ".m2ts",
    ".mpg", ".mpeg"
}

SUBTITLE_EXTENSIONS = {
    ".srt", ".ass", ".ssa", ".sub", ".vtt", ".smi"
}


def rename_subtitles(root_dir: Path, dry_run: bool = False):
    renamed = 0
    skipped = 0

    directories = [root_dir] + [
        p for p in root_dir.rglob("*") if p.is_dir()
    ]

    for directory in directories:
        videos = [
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        ]

        if not videos:
            continue

        subtitles = [
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in SUBTITLE_EXTENSIONS
        ]

        for subtitle in subtitles:
            subtitle_stem = subtitle.stem

            matches = [
                video for video in videos
                if video.stem.lower().startswith(subtitle_stem.lower())
            ]

            if not matches:
                continue

            if len(matches) > 1:
                print("[跳过] 找到多个匹配视频：")
                print(f"       字幕: {subtitle}")

                for video in matches:
                    print(f"       视频: {video.name}")

                skipped += 1
                continue

            video = matches[0]

            new_subtitle = subtitle.with_name(
                video.stem + subtitle.suffix
            )

            # 已经是正确文件名
            if subtitle == new_subtitle:
                continue

            # 防止覆盖
            if new_subtitle.exists():
                print("[跳过] 目标文件已存在：")
                print(f"       {new_subtitle}")
                skipped += 1
                continue

            print(
                f"{'[预览]' if dry_run else '[重命名]'} "
                f"{subtitle.name} -> {new_subtitle.name}"
            )

            if not dry_run:
                subtitle.rename(new_subtitle)

            renamed += 1

    print()

    if dry_run:
        print(
            f"预览完成：将重命名 {renamed} 个字幕，"
            f"跳过 {skipped} 个。"
        )
    else:
        print(
            f"处理完成：已重命名 {renamed} 个字幕，"
            f"跳过 {skipped} 个。"
        )


def main():
    parser = argparse.ArgumentParser(
        description="递归查找视频和字幕，并根据视频文件名重命名字幕。"
    )

    # directory 现在是可选参数
    parser.add_argument(
        "directory",
        nargs="?",
        default=DEFAULT_DIRECTORY,
        help=f"需要处理的目录，默认：{DEFAULT_DIRECTORY}"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示将进行的重命名，不实际修改文件"
    )

    args = parser.parse_args()

    root_dir = Path(args.directory).expanduser().resolve()

    if not root_dir.exists():
        print(f"错误：目录不存在：{root_dir}")
        return

    if not root_dir.is_dir():
        print(f"错误：不是目录：{root_dir}")
        return

    print(f"处理目录：{root_dir}")
    print()

    rename_subtitles(root_dir, args.dry_run)


if __name__ == "__main__":
    main()