import shutil
import threading

from gallery_dl import config as gdl_config
from gallery_dl import job as gdl_job

from memebase.common import ALLOWED_EXTENSIONS
from memebase.log import get_logger
from memebase.temp import make_temp_dir
from memebase.util import sanitize_filename

log = get_logger(__name__)

MAX_FILES = 4

_lock = threading.Lock()


def _configure_gallery_dl(base_dir: str) -> None:
    """Set gallery-dl config for flat output to base_dir, no archive."""
    gdl_config.clear()
    gdl_config.set(("extractor",), "base-directory", base_dir)
    gdl_config.set(("extractor",), "directory", [])
    gdl_config.set(("extractor",), "archive", None)
    gdl_config.set(("extractor",), "image-range", f"1-{MAX_FILES}")
    gdl_config.set(("output",), "mode", "null")


def scrape_url(url: str) -> list[tuple[str, bytes]]:
    """Use gallery-dl to scrape media from a URL.

    Returns a list of (sanitized_basename, content_bytes) tuples.
    Raises ValueError on failure or if no media is found.
    """
    tmp_path = make_temp_dir()

    try:
        with _lock:
            _configure_gallery_dl(str(tmp_path))
            try:
                gdl_job.DownloadJob(url).run()
            except Exception as e:
                raise ValueError(f"gallery-dl failed: {e}") from e

        results = []
        for f in tmp_path.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in ALLOWED_EXTENSIONS:
                log.debug("scrape skipped unsupported file: %s", f.name)
                continue
            basename = sanitize_filename(f.name)
            content = f.read_bytes()
            results.append((basename, content))
            if len(results) >= MAX_FILES:
                break
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

    if not results:
        raise ValueError("No supported media found at URL")

    log.info("scrape: url=%s files=%d", url, len(results))
    return results
