import shutil
import threading
from urllib.parse import unquote, urlparse

from gallery_dl import config as gdl_config
from gallery_dl import exception as gdl_exception
from gallery_dl import extractor as gdl_extractor
from gallery_dl import job as gdl_job
from gallery_dl.extractor.common import Extractor, Message

from memebase.common import ALLOWED_EXTENSIONS
from memebase.log import get_logger
from memebase.temp import make_temp_dir
from memebase.util import sanitize_filename

log = get_logger(__name__)

MAX_FILES = 4

_CONTENT_TYPE_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "video/webm": "webm",
    "video/mp4": "mp4",
}

_lock = threading.Lock()


class _DirectMediaExtractor(Extractor):
    """Catch-all extractor for direct media URLs without file extensions.

    Registered after all built-in extractors so it only handles URLs
    that no other extractor matched.  Does a HEAD request to check
    Content-Type and yields the URL if it points to supported media.
    """

    category = "directmedia"
    subcategory = ""
    filename_fmt = "{filename}.{extension}"
    pattern = r"https?://.+"

    def items(self):
        resp = self.request(self.url, method="HEAD", allow_redirects=True)
        ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()

        ext = _CONTENT_TYPE_EXT.get(ct)
        if not ext:
            return

        # Try Content-Disposition header for filename
        cd = resp.headers.get("Content-Disposition", "")
        filename = ""
        if "filename=" in cd:
            filename = cd.split("filename=")[-1].strip().strip('"').strip("'")
            if "." in filename:
                filename = filename.rsplit(".", 1)[0]

        if not filename:
            path = unquote(urlparse(self.url).path)
            filename = path.rsplit("/", 1)[-1] or "download"
            if "." in filename:
                filename = filename.rsplit(".", 1)[0]

        if not filename:
            filename = "download"

        data = {"filename": filename, "extension": ext}
        yield Message.Directory, "", data
        yield Message.Url, self.url, data


# Force all built-in extractors to load, then register our fallback last
gdl_extractor.find("")
gdl_extractor.add(_DirectMediaExtractor)


class _LimitedDownloadJob(gdl_job.DownloadJob):
    """DownloadJob subclass that stops after max_files downloads globally.

    Child jobs (spawned for Queue items like tweets) inherit the shared
    counter via the parent reference, so the limit applies across all
    children rather than per-child.
    """

    def __init__(self, url, parent=None, *, max_files=None):
        super().__init__(url, parent)
        if isinstance(parent, _LimitedDownloadJob):
            self._counter = parent._counter
            self._max_files = parent._max_files
        else:
            self._counter = [0]
            self._max_files = max_files if max_files is not None else MAX_FILES

    def handle_url(self, url, kwdict):
        if self._counter[0] >= self._max_files:
            log.info("scrape: reached max files limit (%d), stopping", self._max_files)
            raise gdl_exception.StopExtraction()
        super().handle_url(url, kwdict)
        self._counter[0] += 1
        log.info("scrape: downloaded file %d/%d: %s", self._counter[0], self._max_files, url)


def _configure_gallery_dl(base_dir: str) -> None:
    """Set gallery-dl config for flat output to base_dir, no archive."""
    gdl_config.clear()
    gdl_config.set(("extractor",), "base-directory", base_dir)
    gdl_config.set(("extractor",), "directory", [])
    gdl_config.set(("extractor",), "archive", None)
    gdl_config.set(("output",), "mode", "null")


def scrape_url(url: str) -> list[tuple[str, bytes]]:
    """Use gallery-dl to scrape media from a URL.

    Returns a list of (sanitized_basename, content_bytes) tuples.
    Raises ValueError on failure or if no media is found.
    """
    log.info("scrape: starting gallery-dl for %s", url)
    tmp_path = make_temp_dir()

    try:
        with _lock:
            _configure_gallery_dl(str(tmp_path))
            try:
                _LimitedDownloadJob(url).run()
            except Exception as e:
                log.warning("scrape: gallery-dl failed for %s: %s", url, e)
                raise ValueError(f"gallery-dl failed: {e}") from e
        log.info("scrape: gallery-dl finished for %s", url)

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
            log.info("scrape: collected %s (%d bytes)", basename, len(content))
            if len(results) >= MAX_FILES:
                break
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

    if not results:
        raise ValueError("No supported media found at URL")

    log.info("scrape: url=%s files=%d", url, len(results))
    return results
