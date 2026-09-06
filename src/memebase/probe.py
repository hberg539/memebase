"""Probe intrinsic media metadata (dimensions, duration) from files on disk."""

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from memebase.log import get_logger
from memebase.schemas import FileMeta
from memebase.thumbnails import IMAGE_EXTS, VIDEO_EXTS

log = get_logger(__name__)

_FFPROBE_TIMEOUT = 10


def _empty() -> FileMeta:
    return {"width": None, "height": None, "duration": None}


def _probe_image(path: Path) -> FileMeta:
    with Image.open(path) as img:
        width, height = img.size
        duration = None
        if getattr(img, "is_animated", False):
            total_ms = 0
            for i in range(img.n_frames):
                img.seek(i)
                total_ms += img.info.get("duration", 0)
            if total_ms > 0:
                duration = round(total_ms / 1000, 3)
    return {"width": width, "height": height, "duration": duration}


def _probe_video(path: Path) -> FileMeta:
    if shutil.which("ffprobe") is None:
        log.debug("ffprobe not available, skipping probe: %s", path.name)
        return _empty()

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=_FFPROBE_TIMEOUT,
    )
    if result.returncode != 0:
        log.warning("ffprobe failed for %s: %s", path.name, result.stderr.strip())
        return _empty()

    data = json.loads(result.stdout or "{}")
    streams = data.get("streams") or [{}]
    stream = streams[0]
    duration_raw = (data.get("format") or {}).get("duration")
    duration = round(float(duration_raw), 3) if duration_raw else None
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "duration": duration,
    }


def probe_file(path: Path) -> FileMeta:
    """Return width/height/duration for a media file.

    Never raises: any failure is logged and yields None values so an
    upload is not blocked by a probe problem.
    """
    ext = path.suffix.lower()
    try:
        if ext in IMAGE_EXTS:
            return _probe_image(path)
        if ext in VIDEO_EXTS:
            return _probe_video(path)
    except Exception as e:
        log.warning("probe failed for %s: %s", path.name, e)
    return _empty()
