import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_DEFAULT = ROOT_DIR / "config.default.toml"
CONFIG_PATH = DATA_DIR / "config.toml"
DB_PATH = DATA_DIR / "memes.db"
MEMES_DIR = DATA_DIR / "memes"


DEBUG = os.getenv("MEMEBASE_DEBUG", "1") == "1"

USER_AGENT = "memebase/1.0"

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".webm", ".mp4"}

CONTENT_TYPE_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "video/webm": ".webm",
    "video/mp4": ".mp4",
}

SORT_OPTIONS = {
    "name": "m.filename",
    "newest": "m.created_at DESC",
    "oldest": "m.created_at",
    "copies": "m.copy_count DESC",
    "favorites": "m.favorite DESC, m.created_at DESC",
}
