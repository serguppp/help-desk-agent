from datetime import datetime, timedelta
from decimal import Decimal
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
REQUEST_TIMEOUT_SECONDS: float | None = None
SDK_RETRY_ATTEMPTS = 1
DEFAULT_EVALUATION_VARIANT = "current"
EVALUATION_STATUSES = ("PASS", "FAIL", "MANUAL_REVIEW", "ERROR")

FULL_REFUND_NOTICE = timedelta(hours=48)
HALF_REFUND_NOTICE = timedelta(hours=24)
HALF_REFUND_RATE = Decimal("0.5")
REFUND_POLICY_SOURCE = "data/policies/cancellations.md"
RENTAL_REFUND_METHODS = {
    "card": "Same card within 5 working days.",
    "voucher": "New voucher, never money.",
}
POLICY_DOCUMENT_NAMES = ("faq.md", "prices.md", "cancellations.md")
TOKEN_ALIASES = {
    "bikes": "bike",
    "buy": "sell",
    "purchase": "sell",
    "sales": "sell",
    "payment": "pay",
    "payments": "pay",
}
TOOL_ARGUMENT_NAMES = {
    "search_policies": "query",
    "get_booking": "booking_id",
    "calculate_refund": "booking_id",
    "read_policy_document": "file_name",
}
STEP_LIMIT_MESSAGE = (
    "Unable to complete the request within the step limit. Please contact the staff."
)

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
