import unittest

from qbittorrent_filter import CONFIG_DEFAULT, QBFile, choose_files, find_junk_file_ids


MB = 1024 * 1024


class JunkFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = dict(CONFIG_DEFAULT)

    def test_filters_configured_extension_without_main_decision(self) -> None:
        files = [
            QBFile(0, "movie-a.mkv", 400 * MB, 1),
            QBFile(1, "movie-b.mkv", 300 * MB, 1),
            QBFile(2, "visit-us.url", 1, 1),
        ]

        self.assertEqual(find_junk_file_ids(files, self.cfg), {2})
        self.assertIsNone(choose_files(files, self.cfg))

    def test_filters_small_video_next_to_large_video(self) -> None:
        files = [
            QBFile(0, "movie.mkv", 2000 * MB, 1),
            QBFile(1, "bonus.mp4", 50 * MB, 1),
        ]

        self.assertEqual(find_junk_file_ids(files, self.cfg), {1})

    def test_preserves_ordinary_small_video_in_episodic_set(self) -> None:
        files = [
            QBFile(0, "Show.S01E01.mkv", 1000 * MB, 1),
            QBFile(1, "Show.S01E02.mkv", 1000 * MB, 1),
            QBFile(2, "Show.S01E03.mkv", 1000 * MB, 1),
            QBFile(3, "behind-the-scenes.mp4", 20 * MB, 1),
        ]

        self.assertEqual(find_junk_file_ids(files, self.cfg), set())

    def test_filters_suspicious_small_video_in_episodic_set(self) -> None:
        files = [
            QBFile(0, "Show.S01E01.mkv", 1000 * MB, 1),
            QBFile(1, "Show.S01E02.mkv", 1000 * MB, 1),
            QBFile(2, "Show.S01E03.mkv", 1000 * MB, 1),
            QBFile(3, "www.example.com-promo.mp4", 20 * MB, 1),
        ]

        self.assertEqual(find_junk_file_ids(files, self.cfg), {3})

    def test_existing_single_dominant_rule_is_unchanged(self) -> None:
        files = [
            QBFile(0, "movie.mkv", 990 * MB, 1),
            QBFile(1, "readme.txt", 10 * MB, 1),
        ]

        self.assertEqual(choose_files(files, self.cfg), ("single", [0], [1]))


if __name__ == "__main__":
    unittest.main()