from pathlib import Path
from unittest.mock import patch

from PIL import Image

from memebase.thumbnails import get_or_create_thumbnail


def _make_test_image(path: Path) -> Path:
    Image.new("RGB", (800, 600), color=(255, 0, 0)).save(path)
    return path


def _thumb_config(enabled=True, skip_types=None):
    return {
        "enabled": enabled,
        "max_size": 200,
        "quality": 80,
        "format": "webp",
        "skip_types": skip_types or [],
    }


def _mock_thumbdir(mock, tmp_path):
    mock.__truediv__ = lambda self, name: tmp_path / name
    mock.mkdir = lambda **kw: None
    mock.glob = lambda pattern: tmp_path.glob(pattern)


@patch("memebase.thumbnails.THUMBNAILS_DIR")
def test_disabled_and_skip_types_return_none(mock_dir, tmp_path):
    cfg = _thumb_config(enabled=False)
    assert get_or_create_thumbnail("abc", _make_test_image(tmp_path / "a.png"), cfg) is None

    cfg = _thumb_config(skip_types=["gif"])
    assert get_or_create_thumbnail("abc", _make_test_image(tmp_path / "b.gif"), cfg) is None


@patch("memebase.thumbnails.THUMBNAILS_DIR")
def test_generates_and_caches(mock_thumbdir, tmp_path):
    cfg = _thumb_config()
    _mock_thumbdir(mock_thumbdir, tmp_path)

    result = get_or_create_thumbnail("abc123", _make_test_image(tmp_path / "test.png"), cfg)
    assert result is not None
    assert result.exists()
    assert get_or_create_thumbnail("abc123", tmp_path / "test.png", cfg) == result


@patch("memebase.thumbnails.THUMBNAILS_DIR")
def test_corrupt_file_returns_none(mock_thumbdir, tmp_path):
    cfg = _thumb_config()
    _mock_thumbdir(mock_thumbdir, tmp_path)
    (tmp_path / "corrupt.png").write_bytes(b"not an image")

    assert get_or_create_thumbnail("abc123", tmp_path / "corrupt.png", cfg) is None


@patch("memebase.thumbnails.THUMBNAILS_DIR")
def test_tall_image_short_side_preserved(mock_thumbdir, tmp_path):
    cfg = _thumb_config()
    _mock_thumbdir(mock_thumbdir, tmp_path)

    tall = tmp_path / "tall.png"
    Image.new("RGB", (400, 4000), color=(0, 0, 255)).save(tall)

    result = get_or_create_thumbnail("tall1", tall, cfg)
    assert result is not None
    with Image.open(result) as thumb:
        w, h = thumb.size
        # Short side (width) should stay at max_size, not be scaled down
        assert w == 200
        assert h == 2000
