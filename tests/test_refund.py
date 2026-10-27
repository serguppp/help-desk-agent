import json
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from helpdesk import booking as booking_tools
from helpdesk import refund as refund_tools


@pytest.mark.parametrize(
    ("booking_id", "expected_refund"),
    [
        ("CW-1001", "90"),
        ("CW-1002", "340"),
        ("CW-1003", "50"),
        ("CW-1004", "73"),
        ("CW-1005", "0"),
        ("CW-1006", "0"),
        ("CW-1007", "186"),
        ("CW-1008", "0"),
        ("CW-1009", "169"),
        ("CW-1010", "170"),
    ],
)
def test_refund_for_supplied_bookings(booking_id, expected_refund):
    result = refund_tools.calculate_refund(booking_id)

    amount = result.get("refund")
    assert isinstance(amount, Decimal)
    assert amount == Decimal(expected_refund)

    booking = result["booking"]
    assert booking is not None
    assert booking["id"] == booking_id

    message = result.get("message")

    if booking["status"] == "confirmed":
        assert message is None
    else:
        assert isinstance(message, str)
        assert booking["status"] in message


@pytest.mark.parametrize(
    ("remaining", "expected_refund"),
    [
        (timedelta(hours=48, seconds=1), "186"),
        (timedelta(hours=48), "186"),
        (timedelta(hours=48, seconds=-1), "168"),
        (timedelta(hours=24, seconds=1), "168"),
        (timedelta(hours=24), "168"),
        (timedelta(hours=24, seconds=-1), "150"),
    ],
    ids=[
        "more-than-48-hours",
        "exactly-48-hours",
        "less-than-48-hours",
        "more-than-24-hours",
        "exactly-24-hours",
        "less-than-24-hours",
    ],
)
def test_refund_at_time_boundaries(remaining, expected_refund, monkeypatch):
    start = datetime.fromisoformat("2026-06-12T09:00:00+02:00")

    monkeypatch.setattr(
        refund_tools,
        "TIME_NOW",
        start - remaining,
    )

    result = refund_tools.calculate_refund("CW-1007")

    amount = result.get("refund")
    assert isinstance(amount, Decimal)
    assert amount == Decimal(expected_refund)


def test_refund_returns_not_found_for_unknown_booking():
    result = refund_tools.calculate_refund("CW-9999")

    assert result["booking"] is None
    assert result.get("booking_id") == "CW-9999"
    assert result.get("error") == "Booking not found."
    assert "refund" not in result


@pytest.mark.parametrize(
    "booking_id",
    ["", "   ", None, 123, [], {}],
)
def test_refund_rejects_invalid_booking_id(booking_id):
    with pytest.raises(ValueError, match="booking_id"):
        refund_tools.calculate_refund(booking_id)


def test_refund_handles_cents_and_excludes_booking_fee(tmp_path, monkeypatch):
    raw_booking = {
        "id": "CW-2001",
        "status": "confirmed",
        "bike_type": "city",
        "bikes": 1,
        "start": "2026-06-11T18:00:00+02:00",
        "end": "2026-06-12T18:00:00+02:00",
        "add_ons": [],
        "rental_price_eur": 12.34,
        "booking_fee_eur": 2.99,
        "deposit_eur": 50.01,
        "paid_with": "card",
    }

    bookings_path = tmp_path / "bookings.json"
    bookings_path.write_text(
        json.dumps([raw_booking]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        booking_tools,
        "BOOKINGS_PATH",
        bookings_path,
    )
    monkeypatch.setattr(
        refund_tools,
        "TIME_NOW",
        datetime.fromisoformat("2026-06-10T09:00:00+02:00"),
    )

    result = refund_tools.calculate_refund("CW-2001")

    amount = result.get("refund")
    assert isinstance(amount, Decimal)
    assert amount == Decimal("56.18")


def test_refund_does_not_modify_bookings_file(tmp_path, monkeypatch):
    original_data = booking_tools.BOOKINGS_PATH.read_bytes()

    bookings_path = tmp_path / "bookings.json"
    bookings_path.write_bytes(original_data)
    monkeypatch.setattr(booking_tools, "BOOKINGS_PATH", bookings_path)

    refund_tools.calculate_refund("CW-1002")
    refund_tools.calculate_refund("CW-1005")

    assert bookings_path.read_bytes() == original_data


@pytest.mark.parametrize(
    ("booking_id", "rental", "deposit", "rental_method"),
    [
        ("CW-1001", "40", "50", "Same card within 5 working days."),
        ("CW-1002", "40", "300", "Same card within 5 working days."),
        ("CW-1003", "0", "50", None),
        ("CW-1004", "23", "50", "New voucher, never money."),
    ],
)
def test_refund_breakdown_and_methods(booking_id, rental, deposit, rental_method):
    result = refund_tools.calculate_refund(booking_id)

    assert "refund" in result
    assert result.get("cancellation_allowed") is True
    assert result.get("rental_refund_eur") == Decimal(rental)
    assert result.get("deposit_refund_eur") == Decimal(deposit)
    assert result.get("booking_fee_refund_eur") == Decimal(0)
    assert result.get("refund") == Decimal(rental) + Decimal(deposit)
    assert result.get("rental_refund_method") == rental_method
    assert result.get("deposit_refund_method") == "Original deposit payment method."
    assert result.get("policy_source") == "data/policies/cancellations.md"

    for field in (
        "rental_refund_eur",
        "deposit_refund_eur",
        "booking_fee_refund_eur",
        "refund",
    ):
        assert isinstance(result.get(field), Decimal)


@pytest.mark.parametrize("booking_id", ["CW-1005", "CW-1006", "CW-1008"])
def test_disallowed_cancellation_has_no_refund_components_or_methods(booking_id):
    result = refund_tools.calculate_refund(booking_id)

    assert "refund" in result
    assert result.get("cancellation_allowed") is False
    assert result.get("rental_refund_eur") == Decimal(0)
    assert result.get("deposit_refund_eur") == Decimal(0)
    assert result.get("booking_fee_refund_eur") == Decimal(0)
    assert result.get("refund") == Decimal(0)
    assert result.get("rental_refund_method") is None
    assert result.get("deposit_refund_method") is None


def test_refund_rejects_unknown_payment_method(monkeypatch):
    result = booking_tools.get_booking("CW-1001")
    assert result["booking"] is not None
    result["booking"]["paid_with"] = "unsupported"

    monkeypatch.setattr(refund_tools, "get_booking", lambda _: result)

    with pytest.raises(ValueError, match="Unsupported payment method"):
        refund_tools.calculate_refund("CW-1001")


def test_allowed_cancellation_with_zero_amounts_has_no_refund_methods(monkeypatch):
    result = booking_tools.get_booking("CW-1003")
    assert result["booking"] is not None
    result["booking"]["deposit_eur"] = Decimal(0)

    monkeypatch.setattr(refund_tools, "get_booking", lambda _: result)

    refund = refund_tools.calculate_refund("CW-1003")

    assert "refund" in refund
    assert refund.get("cancellation_allowed") is True
    assert refund.get("refund") == Decimal(0)
    assert refund.get("rental_refund_method") is None
    assert refund.get("deposit_refund_method") is None
