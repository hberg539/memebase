import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from db import init_db
from app import app

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", debug=True, port=5000)
