"""Config."""
import os
DB_URL = os.getenv("DB_URL", "sqlite:///app.db")
CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))
DEBUG = os.getenv("DEBUG", "0") == "1"
