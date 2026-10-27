from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOOKINGS_PATH = PROJECT_ROOT / "data" / "bookings.json"
POLICIES_PATH = PROJECT_ROOT / "data" / "policies"
QUESTIONS_PATH = PROJECT_ROOT / "eval" / "questions.json"

TIME_NOW = datetime.fromisoformat("2026-06-10T09:00:00+02:00")

MAX_RESULTS = 3
HEADING_WEIGHT = 3
SCORER_VERSION = 2
MAX_STEPS = 5
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "can",
    "do",
    "does",
    "for",
    "i",
    "in",
    "is",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "you",
    "your",
}
