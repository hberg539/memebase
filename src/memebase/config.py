import logging
import shutil
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from memebase.common import CONFIG_DEFAULT, CONFIG_PATH

log = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "grid": {
        "thumbnail_size": 200,
        "page_size": 50,
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


def load_config() -> dict[str, Any]:
    """Load config.toml from the data directory, copying the default if missing.

    The returned dict is the user config deep-merged over built-in defaults,
    so every expected key is always present.
    """
    if not CONFIG_PATH.exists():
        shutil.copy2(CONFIG_DEFAULT, CONFIG_PATH)
        log.info("Copied default config to %s", CONFIG_PATH)
    with open(CONFIG_PATH, "rb") as f:
        user_cfg = tomllib.load(f)
    return _deep_merge(_DEFAULTS, user_cfg)
