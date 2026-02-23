import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from memebase.config import load_config
from memebase.db import init_db
from memebase.app import app
from memebase.common import DEBUG

if __name__ == "__main__":
    init_db()
    load_config()
    app.run(host="0.0.0.0", debug=DEBUG, port=5000)
