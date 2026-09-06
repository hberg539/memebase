from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from memebase.scrape import ScrapedFile, scrape_url, source_from_kwdict


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


class TestSourceFromKwdict:
    def test_twitter_shape(self):
        kw = {
            "category": "twitter",
            "author": {"name": "someone", "nick": "Some One"},
            "content": "this is the tweet",
            "date": datetime(2024, 5, 6, 7, 8, 9),
        }
        src = source_from_kwdict("https://x.com/someone/status/1", kw)
        assert src == {
            "source_url": "https://x.com/someone/status/1",
            "source_site": "twitter",
            "source_author": "someone",
            "source_text": "this is the tweet",
            "source_date": "2024-05-06 07:08:09",
        }

    def test_reddit_shape_uses_title_and_string_author(self):
        kw = {
            "category": "reddit",
            "author": "u_person",
            "title": "post title",
            "date": datetime(2024, 1, 1),
        }
        src = source_from_kwdict("https://reddit.com/r/x/1", kw)
        assert src["source_author"] == "u_person"
        assert src["source_text"] == "post title"

    def test_bluesky_shape_uses_handle(self):
        kw = {"category": "bluesky", "author": {"handle": "someone.bsky.social"}, "text": "hi"}
        src = source_from_kwdict("https://bsky.app/x", kw)
        assert src["source_author"] == "someone.bsky.social"
        assert src["source_text"] == "hi"

    def test_leading_at_stripped_from_author(self):
        src = source_from_kwdict("u", {"author": "@handle"})
        assert src["source_author"] == "handle"

    def test_null_datetime_becomes_none(self):
        src = source_from_kwdict("u", {"date": datetime(1, 1, 1)})
        assert src["source_date"] is None

    def test_string_date_normalized(self):
        src = source_from_kwdict("u", {"date": "2024-05-06T07:08:09Z"})
        assert src["source_date"] == "2024-05-06 07:08:09"

    def test_empty_kwdict(self):
        src = source_from_kwdict("https://example.com/x.png", {})
        assert src == {
            "source_url": "https://example.com/x.png",
            "source_site": "",
            "source_author": "",
            "source_text": "",
            "source_date": None,
        }


class TestScrapeUrlSource:
    @patch("memebase.scrape._LimitedDownloadJob")
    def test_attaches_kwdict_to_file(self, mock_job_cls, tmp_path):
        """scrape_url pairs each file with the kwdict recorded by the job."""
        mock_job = MagicMock()
        mock_job.file_meta = {}

        def fake_run():
            scrape_dir = _find_scrape_dir(tmp_path)
            f = scrape_dir / "1_1.jpg"
            f.write_bytes(b"JPG")
            mock_job.file_meta[str(f.resolve())] = {
                "category": "twitter",
                "author": {"name": "someone"},
                "content": "text",
            }

        mock_job.run = fake_run
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path):
            results = scrape_url("https://x.com/someone/status/1")

        assert isinstance(results[0], ScrapedFile)
        assert results[0].source["source_site"] == "twitter"
        assert results[0].source["source_author"] == "someone"
        assert results[0].source["source_url"] == "https://x.com/someone/status/1"

    @patch("memebase.scrape._LimitedDownloadJob")
    def test_missing_kwdict_yields_url_only_source(self, mock_job_cls, tmp_path):
        def fake_run():
            (_find_scrape_dir(tmp_path) / "image.png").write_bytes(b"PNG")

        mock_job = MagicMock()
        mock_job.file_meta = {}
        mock_job.run = fake_run
        mock_job_cls.return_value = mock_job

        with _patch_temp_dir(tmp_path):
            results = scrape_url("https://example.com/image.png")

        assert results[0].source["source_url"] == "https://example.com/image.png"
        assert results[0].source["source_site"] == ""
