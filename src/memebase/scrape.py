import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import unquote, urlparse

from gallery_dl import config as gdl_config
from gallery_dl import exception as gdl_exception
from gallery_dl import extractor as gdl_extractor
from gallery_dl import job as gdl_job
from gallery_dl.extractor.common import Extractor, Message

from memebase.common import ALLOWED_EXTENSIONS
from memebase.log import get_logger
from memebase.schemas import SourceMeta
from memebase.temp import make_temp_dir
from memebase.util import sanitize_filename

log = get_logger(__name__)

_DEFAULT_MAX_FILES = 4

_CONTENT_TYPE_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "video/webm": "webm",
    "video/mp4": "mp4",
}

_lock = threading.Lock()


class ScrapedFile(NamedTuple):
    basename: str
    content: bytes
    source: SourceMeta


def _first_str(kwdict: dict[str, Any], *keys: str) -> str:
    """Return the first non-empty string value found under *keys*."""
    for key in keys:
        value = kwdict.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _author_from(kwdict: dict[str, Any]) -> str:
    """Pick an author handle/username from the varied shapes extractors use."""
    for key in ("author", "user", "uploader", "account", "blog", "owner"):
        value = kwdict.get(key)
        if isinstance(value, dict):
            handle = _first_str(value, "name", "handle", "username", "screen_name", "nick")
            if handle:
                return handle.lstrip("@")
        elif isinstance(value, str) and value.strip():
            return value.strip().lstrip("@")
    return _first_str(kwdict, "blog_name", "username", "user_name").lstrip("@")


def _date_from(kwdict: dict[str, Any]) -> str | None:
    """Normalize gallery-dl's date to 'YYYY-MM-DD HH:MM:SS' (UTC) or None."""
    value = kwdict.get("date")
    if isinstance(value, datetime):
        if value.year <= 1:  # gallery-dl's NullDatetime sentinel
            return None
        if value.tzinfo is not None:
            value = value.astimezone(tz=None).replace(tzinfo=None)
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str) and value.strip():
        return value.strip()[:19].replace("T", " ")
    return None


def source_from_kwdict(url: str, kwdict: dict[str, Any]) -> SourceMeta:
    """Map a gallery-dl kwdict to the source columns we store."""
    return {
        "source_url": url,
        "source_site": _first_str(kwdict, "category"),
        "source_author": _author_from(kwdict),
        "source_text": _first_str(kwdict, "content", "text", "title", "caption", "description"),
        "source_date": _date_from(kwdict),
    }


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
            self.file_meta = parent.file_meta
        else:
            self._counter = [0]
            self._max_files = max_files if max_files is not None else _DEFAULT_MAX_FILES
            # final path on disk -> kwdict for that download
            self.file_meta: dict[str, dict[str, Any]] = {}

    def handle_url(self, url, kwdict):
        if self._counter[0] >= self._max_files:
            log.info("scrape: reached max files limit (%d), stopping", self._max_files)
            raise gdl_exception.StopExtraction()
        super().handle_url(url, kwdict)
        self._counter[0] += 1
        log.info("scrape: downloaded file %d/%d: %s", self._counter[0], self._max_files, url)
        path = self.pathfmt.path if self.pathfmt else ""
        if path and Path(path).is_file():
            self.file_meta[str(Path(path).resolve())] = dict(kwdict)


def _configure_gallery_dl(base_dir: str) -> None:
    """Set gallery-dl config for flat output to base_dir, no archive."""
    gdl_config.clear()
    gdl_config.set(("extractor",), "base-directory", base_dir)
    gdl_config.set(("extractor",), "directory", [])
    gdl_config.set(("extractor",), "archive", None)
    gdl_config.set(("output",), "mode", "null")


def scrape_url(url: str, *, max_files: int = _DEFAULT_MAX_FILES) -> list[ScrapedFile]:
    """Use gallery-dl to scrape media from a URL.

    Returns a list of ScrapedFile(basename, content, source) tuples, where
    source holds the post metadata gallery-dl attached to that download.
    Raises ValueError on failure or if no media is found.
    """
    log.info("scrape: starting gallery-dl for %s", url)
    tmp_path = make_temp_dir()

    try:
        with _lock:
            _configure_gallery_dl(str(tmp_path))
            job = _LimitedDownloadJob(url, max_files=max_files)
            try:
                job.run()
            except Exception as e:
                log.warning("scrape: gallery-dl failed for %s: %s", url, e)
                raise ValueError(f"gallery-dl failed: {e}") from e
        log.info("scrape: gallery-dl finished for %s", url)
        file_meta = getattr(job, "file_meta", None) or {}

        results = []
        for f in tmp_path.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in ALLOWED_EXTENSIONS:
                log.debug("scrape skipped unsupported file: %s", f.name)
                continue
            basename = sanitize_filename(f.name)
            content = f.read_bytes()
            kwdict = file_meta.get(str(f.resolve()), {})
            results.append(ScrapedFile(basename, content, source_from_kwdict(url, kwdict)))
            log.info("scrape: collected %s (%d bytes)", basename, len(content))
            if len(results) >= max_files:
                break
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

    if not results:
        raise ValueError("No supported media found at URL")

    log.info("scrape: url=%s files=%d", url, len(results))
    return results
