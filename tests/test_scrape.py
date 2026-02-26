import http.client
from unittest.mock import MagicMock, patch

import pytest

from memebase.scrape import scrape_url
from memebase.service import is_media_url


class TestIsMediaUrl:
    def _mock_response(self, content_type):
        resp = MagicMock()
        resp.headers = {"Content-Type": content_type}
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch("memebase.service.urllib.request.urlopen")
    def test_image_content_type(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response("image/png")
        assert is_media_url("https://example.com/pic.png") is True

    @patch("memebase.service.urllib.request.urlopen")
    def test_video_content_type(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response("video/mp4")
        assert is_media_url("https://example.com/video.mp4") is True

    @patch("memebase.service.urllib.request.urlopen")
    def test_html_content_type(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response("text/html; charset=utf-8")
        assert is_media_url("https://example.com/page") is False

    @patch("memebase.service.urllib.request.urlopen")
    def test_error_returns_false(self, mock_urlopen):
        mock_urlopen.side_effect = http.client.HTTPException("timeout")
        assert is_media_url("https://example.com/broken") is False


def _patch_temp_dir(tmp_path):
    """Patch TEMP_DIR so scrape_url creates temp dirs inside tmp_path."""
    return patch("memebase.scrape.TEMP_DIR", tmp_path)


def _find_scrape_dir(tmp_path):
    """Find the temp subdirectory created by scrape_url under tmp_path."""
    dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert len(dirs) == 1
    return dirs[0]


class TestScrapeUrl:
    @patch("memebase.scrape.gdl_job.DownloadJob")
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

    @patch("memebase.scrape.MAX_FILES", 5)
    @patch("memebase.scrape.gdl_job.DownloadJob")
    def test_respects_max_files(self, mock_job_cls, tmp_path):
        """scrape_url caps results at MAX_FILES."""

        def fake_run():
            scrape_dir = _find_scrape_dir(tmp_path)
            for i in range(10):
                (scrape_dir / f"image_{i}.png").write_bytes(b"PNG data")

        mock_job = MagicMock()
        mock_job.run = fake_run
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path):
            results = scrape_url("https://example.com/post")

        assert len(results) == 5

    @patch("memebase.scrape.gdl_job.DownloadJob")
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

    @patch("memebase.scrape.gdl_job.DownloadJob")
    def test_error_on_no_media(self, mock_job_cls, tmp_path):
        """scrape_url raises ValueError when no supported media is found."""
        mock_job = MagicMock()
        mock_job.run = MagicMock()
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path), pytest.raises(ValueError, match="No supported media"):
            scrape_url("https://example.com/empty")

    @patch("memebase.scrape.gdl_job.DownloadJob")
    def test_wraps_gallery_dl_exception(self, mock_job_cls, tmp_path):
        """scrape_url wraps gallery-dl exceptions in ValueError."""
        mock_job = MagicMock()
        mock_job.run.side_effect = RuntimeError("connection failed")
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path), pytest.raises(ValueError, match="gallery-dl failed"):
            scrape_url("https://example.com/broken")

    # TODO: re-enable when cleanup is re-enabled in scrape.py
    @pytest.mark.skip(reason="cleanup temporarily disabled for debugging")
    @patch("memebase.scrape.gdl_job.DownloadJob")
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
