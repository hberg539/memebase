import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from memebase.probe import probe_file

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _make_video(path: Path, width: int = 64, height: int = 48, seconds: float = 1.0) -> Path:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={width}x{height}:d={seconds}",
            str(path),
        ],
        check=True,
    )
    return path


class TestProbeImage:
    def test_static_png(self, tmp_path):
        f = tmp_path / "a.png"
        Image.new("RGB", (123, 45)).save(f)
        assert probe_file(f) == {"width": 123, "height": 45, "duration": None}

    def test_jpeg(self, tmp_path):
        f = tmp_path / "a.jpg"
        Image.new("RGB", (10, 20)).save(f)
        meta = probe_file(f)
        assert (meta["width"], meta["height"]) == (10, 20)

    def test_animated_gif_duration(self, tmp_path):
        f = tmp_path / "a.gif"
        frames = [Image.new("RGB", (8, 8), color=(i * 60, 0, 0)) for i in range(4)]
        frames[0].save(f, save_all=True, append_images=frames[1:], duration=250, loop=0)
        meta = probe_file(f)
        assert (meta["width"], meta["height"]) == (8, 8)
        assert meta["duration"] == pytest.approx(1.0)

    def test_static_gif_has_no_duration(self, tmp_path):
        f = tmp_path / "a.gif"
        Image.new("P", (8, 8)).save(f)
        assert probe_file(f)["duration"] is None

    def test_corrupt_image_returns_empty(self, tmp_path):
        f = tmp_path / "bad.png"
        f.write_bytes(b"not an image")
        assert probe_file(f) == {"width": None, "height": None, "duration": None}


class TestProbeVideo:
    @pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
    def test_mp4(self, tmp_path):
        f = _make_video(tmp_path / "a.mp4", 64, 48, 1.0)
        meta = probe_file(f)
        assert (meta["width"], meta["height"]) == (64, 48)
        assert meta["duration"] == pytest.approx(1.0, abs=0.1)

    @pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
    def test_webm(self, tmp_path):
        f = _make_video(tmp_path / "a.webm", 32, 32, 0.5)
        meta = probe_file(f)
        assert (meta["width"], meta["height"]) == (32, 32)
        assert meta["duration"] == pytest.approx(0.5, abs=0.1)

    def test_without_ffprobe_returns_empty(self, tmp_path):
        f = tmp_path / "a.mp4"
        f.write_bytes(b"fake")
        with patch("memebase.probe.shutil.which", return_value=None):
            assert probe_file(f) == {"width": None, "height": None, "duration": None}

    def test_ffprobe_failure_returns_empty(self, tmp_path):
        f = tmp_path / "a.mp4"
        f.write_bytes(b"fake")
        failed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad")
        with (
            patch("memebase.probe.shutil.which", return_value="/usr/bin/ffprobe"),
            patch("memebase.probe.subprocess.run", return_value=failed),
        ):
            assert probe_file(f) == {"width": None, "height": None, "duration": None}

    def test_ffprobe_timeout_returns_empty(self, tmp_path):
        f = tmp_path / "a.mp4"
        f.write_bytes(b"fake")
        with (
            patch("memebase.probe.shutil.which", return_value="/usr/bin/ffprobe"),
            patch(
                "memebase.probe.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="ffprobe", timeout=10),
            ),
        ):
            assert probe_file(f) == {"width": None, "height": None, "duration": None}


class TestProbeUnknown:
    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("hi")
        assert probe_file(f) == {"width": None, "height": None, "duration": None}
