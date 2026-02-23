import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from memebase.app import app
from memebase.common import DEBUG
from memebase.config import load_config
from memebase.db import init_db

if __name__ == "__main__":
    init_db()
    cfg = load_config()
    app.run(host=cfg["server"]["host"], debug=DEBUG, port=cfg["server"]["port"])
