import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from memebase.app import create_app
from memebase.common import CONFIG_PATH, DEBUG
from memebase.config import get_config
from memebase.db import init_db
from memebase.temp import cleanup as cleanup_temp

if __name__ == "__main__":
    init_db()
    cleanup_temp()
    cfg = get_config()
    app = create_app(cfg)
    app.run(
        host=cfg["server"]["host"],
        debug=DEBUG,
        port=cfg["server"]["port"],
        extra_files=[str(CONFIG_PATH)],
    )
