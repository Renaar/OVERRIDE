"""Runtime settings (environment variables) and paths."""
from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

APP_NAME = os.environ.get("APP_NAME", "OVERRIDE")
APP_VERSION = "0.1.0"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
DEFAULTS_DIR = Path(os.environ.get("DEFAULTS_DIR", ROOT / "data"))
WEB_DIR = ROOT / "web"
DB_PATH = DATA_DIR / "override.db"
BACKUP_DIR = DATA_DIR / "backups"

TZ = ZoneInfo(os.environ.get("TZ", "Europe/Zurich") or "Europe/Zurich")
PORT = int(os.environ.get("PORT", "8087"))

NTFY_URL = os.environ.get("NTFY_URL", "").rstrip("/")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "")

DATA_FILES = ("config", "skills", "ranks", "titles", "system_messages")
