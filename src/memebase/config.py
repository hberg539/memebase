import logging
import shutil
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from memebase.common import CONFIG_DEFAULT, CONFIG_PATH, ROOT_DIR
from memebase.schemas import AppConfig

log = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "server": {
        "host": "0.0.0.0",
        "port": 5000,
    },
    "grid": {
        "layout": "grid",
        "thumbnail_size": 220,
        "per_page": "auto",
    },
    "thumbnails": {
        "enabled": False,
        "max_size": 440,
        "quality": 80,
        "format": "webp",
        "skip_types": ["gif"],
    },
    "ai": {
        "enabled": False,
        "parallel": 3,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


_cached: AppConfig | None = None


def load_config() -> AppConfig:
    """Return the cached application config, loading from disk on first call.

    Copies the default config into the data directory if missing, then
    deep-merges the user config over built-in defaults so every expected
    key is always present.
    """
    global _cached
    if _cached is not None:
        return _cached
    if not CONFIG_PATH.exists():
        shutil.copy2(CONFIG_DEFAULT, CONFIG_PATH)
        log.info("default config created: path=%s", CONFIG_PATH)
    with open(CONFIG_PATH, "rb") as f:
        user_cfg = tomllib.load(f)
    _cached = _deep_merge(_DEFAULTS, user_cfg)
    return _cached


def load_version() -> str:
    """Read the project version from pyproject.toml."""
    try:
        with open(ROOT_DIR / "pyproject.toml", "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return ""
