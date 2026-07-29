import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check_video_integrity import (
    DecodeIssue,
    ProblemRange,
    build_parser,
    build_sample_starts,
    find_ffmpeg,
    format_timestamp,
    gpu_setup_failed,
    is_decode_error,
    merge_problem_ranges,
)


class VideoIntegrityTests(unittest.TestCase):
    def test_gpu_is_default_and_cpu_can_override_it(self) -> None:
        self.assertTrue(build_parser().parse_args([]).gpu)
        self.assertTrue(build_parser().parse_args(["--gpu"]).gpu)
        self.assertFalse(build_parser().parse_args(["--cpu"]).gpu)

    def test_detects_cuda_setup_failure(self) -> None:
        issues = [DecodeIssue(None, "Device setup failed for decoder: CUDA_ERROR_NO_DEVICE")]
        self.assertTrue(gpu_setup_failed(issues))
        self.assertFalse(gpu_setup_failed([DecodeIssue(1.0, "Invalid NAL unit size")]))

    def test_builds_sample_windows_including_video_end(self) -> None:
        self.assertEqual(build_sample_starts(125.0, 60.0, 3.0), [0.0, 60.0, 122.0])
        self.assertEqual(build_sample_starts(10.0, 60.0, 3.0), [0.0, 7.0])
        self.assertEqual(build_sample_starts(2.0, 60.0, 3.0), [0.0])

    def test_finds_winget_ffmpeg_when_current_path_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as local_app_data:
            ffmpeg = (
                Path(local_app_data)
                / "Microsoft"
                / "WinGet"
                / "Packages"
                / "Gyan.FFmpeg_Test"
                / "ffmpeg-test"
                / "bin"
                / "ffmpeg.exe"
            )
            ffmpeg.parent.mkdir(parents=True)
            ffmpeg.touch()

            environment = {"LOCALAPPDATA": local_app_data}
            with patch.dict(os.environ, environment, clear=True), patch(
                "check_video_integrity.shutil.which", return_value=None
            ):
                self.assertEqual(find_ffmpeg(), str(ffmpeg))

    def test_recognizes_decode_errors_but_not_progress(self) -> None:
        self.assertTrue(is_decode_error("[h264] error while decoding MB 12 3"))
        self.assertTrue(is_decode_error("[h264] concealing 42 DC errors in P frame"))
        self.assertFalse(is_decode_error("out_time_us=1234000"))

    def test_merges_nearby_timestamps_with_context(self) -> None:
        issues = [
            DecodeIssue(10.0, "first"),
            DecodeIssue(11.5, "second"),
            DecodeIssue(30.0, "third"),
            DecodeIssue(None, "no timestamp"),
        ]

        self.assertEqual(
            merge_problem_ranges(issues, merge_gap=2.0, context=1.0),
            [
                ProblemRange(9.0, 12.5, 2),
                ProblemRange(29.0, 31.0, 1),
            ],
        )

    def test_formats_timestamp(self) -> None:
        self.assertEqual(format_timestamp(3661.234), "01:01:01.234")


if __name__ == "__main__":
    unittest.main()