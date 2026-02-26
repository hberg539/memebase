import shutil
import time
import uuid
from pathlib import Path

from memebase.common import TEMP_DIR
from memebase.log import get_logger

log = get_logger(__name__)


def make_temp_dir() -> Path:
    """Create and return a unique temporary subdirectory inside TEMP_DIR."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    dirname = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    tmp_path = TEMP_DIR / dirname
    tmp_path.mkdir()
    return tmp_path


def cleanup() -> None:
    """Remove the temp directory and all its contents. Safe to call if it doesn't exist."""
    if not TEMP_DIR.exists():
        return
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    log.info("cleaned up temp directory: %s", TEMP_DIR)
