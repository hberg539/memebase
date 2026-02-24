import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from memebase.common import THUMBNAILS_DIR
from memebase.config import load_config
from memebase.log import get_logger

log = get_logger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
VIDEO_EXTS = {".webm", ".mp4"}

# config format -> (Pillow save format, file extension)
THUMB_FORMATS: dict[str, tuple[str, str]] = {
    "webp": ("WEBP", ".webp"),
    "jpeg": ("JPEG", ".jpg"),
}


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _fit_cover(img: Image.Image, max_size: int) -> Image.Image:
    """Downscale so the short side = *max_size* (no upscale)."""
    w, h = img.size
    short = min(w, h)
    if short > max_size:
        scale = max_size / short
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    return img


def _generate_image_thumbnail(source: Path, dest: Path, cfg: dict) -> Path:
    """Generate a thumbnail from an image file using Pillow."""
    max_size = cfg["max_size"]
    quality = cfg["quality"]
    fmt = cfg["format"]

    with Image.open(source) as img:
        img = _fit_cover(img, max_size)

        # Composite RGBA onto dark background for JPEG output
        if fmt == "jpeg" and img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (30, 30, 30))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif fmt == "jpeg" and img.mode != "RGB":
            img = img.convert("RGB")

        tmp = dest.with_suffix(".tmp")
        pillow_fmt, _ = THUMB_FORMATS[fmt]
        img.save(tmp, format=pillow_fmt, quality=quality)
        tmp.rename(dest)

    log.info("thumbnail generated (image): %s -> %s", source.name, dest.name)
    return dest


def _generate_video_thumbnail(source: Path, dest: Path, cfg: dict) -> Path | None:
    """Extract a frame from a video with ffmpeg, then resize with Pillow."""
    if not _has_ffmpeg():
        log.debug("ffmpeg not available, skipping video thumbnail: %s", source.name)
        return None

    max_size = cfg["max_size"]
    quality = cfg["quality"]
    fmt = cfg["format"]

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_frame:
        tmp_frame_path = Path(tmp_frame.name)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "1",
                "-i",
                str(source),
                "-frames:v",
                "1",
                str(tmp_frame_path),
            ],
            capture_output=True,
            timeout=15,
        )

        if not tmp_frame_path.exists() or tmp_frame_path.stat().st_size == 0:
            log.warning("ffmpeg produced no output for: %s", source.name)
            return None

        with Image.open(tmp_frame_path) as img:
            img = _fit_cover(img, max_size)
            if img.mode != "RGB":
                img = img.convert("RGB")

            tmp = dest.with_suffix(".tmp")
            pillow_fmt, _ = THUMB_FORMATS[fmt]
            img.save(tmp, format=pillow_fmt, quality=quality)
            tmp.rename(dest)

        log.info("thumbnail generated (video): %s -> %s", source.name, dest.name)
        return dest
    except subprocess.TimeoutExpired:
        log.warning("ffmpeg timed out for: %s", source.name)
        return None
    except Exception:
        log.exception("video thumbnail failed for: %s", source.name)
        return None
    finally:
        tmp_frame_path.unlink(missing_ok=True)


def delete_thumbnails(uuid: str) -> None:
    """Remove all cached thumbnails for a uuid."""
    for path in THUMBNAILS_DIR.glob(f"{uuid}.*"):
        path.unlink()
        log.info("removed thumbnail: %s", path.name)


def get_or_create_thumbnail(uuid: str, source_path: Path) -> Path | None:
    """Return cached or freshly generated thumbnail path, or None on failure."""
    cfg = load_config()["thumbnails"]
    if not cfg["enabled"]:
        return None

    ext = source_path.suffix.lower()
    if ext.lstrip(".") in cfg["skip_types"]:
        return None

    _, thumb_ext = THUMB_FORMATS[cfg["format"]]
    dest = THUMBNAILS_DIR / f"{uuid}{thumb_ext}"

    # Serve cached thumbnail
    if dest.exists():
        return dest

    # Current format doesn't exist - clear old format files before generating
    delete_thumbnails(uuid)

    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    if ext in IMAGE_EXTS:
        try:
            return _generate_image_thumbnail(source_path, dest, cfg)
        except Exception:
            log.exception("image thumbnail failed for: %s", source_path.name)
            return None
    elif ext in VIDEO_EXTS:
        return _generate_video_thumbnail(source_path, dest, cfg)

    return None
