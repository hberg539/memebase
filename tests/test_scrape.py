from unittest.mock import MagicMock, patch

import pytest

from memebase.scrape import scrape_url


def _patch_temp_dir(tmp_path):
    """Patch TEMP_DIR so scrape_url creates temp dirs inside tmp_path."""
    return patch("memebase.temp.TEMP_DIR", tmp_path)


def _find_scrape_dir(tmp_path):
    """Find the temp subdirectory created by scrape_url under tmp_path."""
    dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert len(dirs) == 1
    return dirs[0]


class TestScrapeUrl:
    @patch("memebase.scrape._LimitedDownloadJob")
    def test_collects_media_files(self, mock_job_cls, tmp_path):
        """scrape_url collects allowed media files from gallery-dl output."""

        def fake_run():
            scrape_dir = _find_scrape_dir(tmp_path)
            (scrape_dir / "image.png").write_bytes(b"PNG data")

        mock_job = MagicMock()
        mock_job.run = fake_run
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path):
            results = scrape_url("https://example.com/post")

        assert len(results) == 1
        assert results[0][0] == "image.png"
        assert results[0][1] == b"PNG data"

    @patch("memebase.scrape._LimitedDownloadJob")
    def test_respects_max_files(self, mock_job_cls, tmp_path):
        """scrape_url caps results at max_files."""

        def fake_run():
            scrape_dir = _find_scrape_dir(tmp_path)
            for i in range(10):
                (scrape_dir / f"image_{i}.png").write_bytes(b"PNG data")

        mock_job = MagicMock()
        mock_job.run = fake_run
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path):
            results = scrape_url("https://example.com/post", max_files=5)

        assert len(results) == 5

    @patch("memebase.scrape._LimitedDownloadJob")
    def test_filters_unsupported_extensions(self, mock_job_cls, tmp_path):
        """scrape_url skips files with non-allowed extensions."""

        def fake_run():
            scrape_dir = _find_scrape_dir(tmp_path)
            (scrape_dir / "image.png").write_bytes(b"PNG data")
            (scrape_dir / "readme.txt").write_bytes(b"text")
            (scrape_dir / "data.json").write_bytes(b"{}")

        mock_job = MagicMock()
        mock_job.run = fake_run
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path):
            results = scrape_url("https://example.com/post")

        assert len(results) == 1
        assert results[0][0] == "image.png"

    @patch("memebase.scrape._LimitedDownloadJob")
    def test_error_on_no_media(self, mock_job_cls, tmp_path):
        """scrape_url raises ValueError when no supported media is found."""
        mock_job = MagicMock()
        mock_job.run = MagicMock()
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path), pytest.raises(ValueError, match="No supported media"):
            scrape_url("https://example.com/empty")

    @patch("memebase.scrape._LimitedDownloadJob")
    def test_wraps_gallery_dl_exception(self, mock_job_cls, tmp_path):
        """scrape_url wraps gallery-dl exceptions in ValueError."""
        mock_job = MagicMock()
        mock_job.run.side_effect = RuntimeError("connection failed")
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path), pytest.raises(ValueError, match="gallery-dl failed"):
            scrape_url("https://example.com/broken")

    @patch("memebase.scrape._LimitedDownloadJob")
    def test_cleans_up_temp_dir(self, mock_job_cls, tmp_path):
        """scrape_url removes its temp directory after completion."""

        def fake_run():
            scrape_dir = _find_scrape_dir(tmp_path)
            (scrape_dir / "image.png").write_bytes(b"PNG data")

        mock_job = MagicMock()
        mock_job.run = fake_run
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path):
            scrape_url("https://example.com/post")

        # temp dir parent exists but the scrape subdirectory was cleaned up
        assert tmp_path.exists()
        assert list(tmp_path.iterdir()) == []
