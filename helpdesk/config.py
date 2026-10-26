from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOOKINGS_PATH = PROJECT_ROOT / "data" / "bookings.json"
POLICIES_PATH = PROJECT_ROOT / "data" / "policies"
TIME_NOW = datetime.fromisoformat("2026-06-10T09:00:00+02:00")
