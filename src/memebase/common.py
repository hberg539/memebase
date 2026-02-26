import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_DEFAULT = ROOT_DIR / "config.default.toml"
CONFIG_PATH = DATA_DIR / "config.toml"
DB_PATH = DATA_DIR / "memes.db"
TEMP_DIR = DATA_DIR / "temp"
MEMES_DIR = DATA_DIR / "memes"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
THEMES_DIR = DATA_DIR / "themes"

DEFAULT_THEME = "midnight"


DEBUG = os.getenv("MEMEBASE_DEBUG", "1") == "1"

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".webm", ".mp4"}

CACHE_MAX_AGE = 604800

SORT_OPTIONS = {
    "name": "m.filename",
    "newest": "m.created_at DESC",
    "oldest": "m.created_at",
    "favorites": "m.favorite DESC, m.created_at DESC",
}
