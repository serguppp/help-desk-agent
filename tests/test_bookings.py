import json

import pytest

from helpdesk import tools


def test_get_booking_returns_booking_details_from_any_working_directory(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    result = tools.get_booking("CW-1002")
    booking = result["booking"]
    assert booking is not None
    assert booking["id"] == "CW-1002"
    assert booking["status"] == "confirmed"
    assert booking["bike_type"] == "e-bike"
    assert booking["bikes"] == 2
    assert booking["start"] == "2026-06-11T18:00:00+02:00"
    assert booking["end"] == "2026-06-12T18:00:00+02:00"
    assert booking["add_ons"] == []
    assert booking["rental_price_eur"] == 80
    assert booking["booking_fee_eur"] == 2
    assert booking["deposit_eur"] == 300
    assert booking["paid_with"] == "card"


def test_get_booking_returns_cancelled_booking():
    result = tools.get_booking("CW-1005")
    booking = result["booking"]
    assert booking is not None
    assert booking["id"] == "CW-1005"
    assert booking["status"] == "cancelled"


def test_get_booking_returns_not_found_for_unknown_id():
    assert tools.get_booking("CW-9999") == {
        "booking_id": "CW-9999",
        "booking": None,
        "error": "booking not found",
    }


@pytest.mark.parametrize("booking_id", ["", "   ", None, 123, [], {}])
def test_get_booking_rejects_invalid_argument(booking_id):
    with pytest.raises(ValueError, match="booking_id"):
        tools.get_booking(booking_id)


def test_get_booking_reads_the_configured_file(tmp_path, monkeypatch):
    booking = {
        "id": "CW-2001",
        "status": "confirmed",
        "bike_type": "city",
        "bikes": 1,
        "start": "2026-06-13T10:00:00+02:00",
        "end": "2026-06-13T12:00:00+02:00",
        "add_ons": [],
        "rental_price_eur": 8,
        "booking_fee_eur": 0,
        "deposit_eur": 50,
        "paid_with": "card",
    }
    bookings_path = tmp_path / "bookings.json"
    bookings_path.write_text(json.dumps([booking]), encoding="utf-8")
    monkeypatch.setattr(tools, "BOOKINGS_PATH", bookings_path)

    assert tools.get_booking("CW-2001") == {
        "booking_id": booking["id"],
        "booking": booking,
        "error": None,
    }


def test_get_booking_does_not_hide_missing_data_file(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "BOOKINGS_PATH", tmp_path / "missing.json")

    with pytest.raises(FileNotFoundError):
        tools.get_booking("CW-1002")


def test_get_booking_does_not_hide_invalid_json(tmp_path, monkeypatch):
    bookings_path = tmp_path / "bookings.json"
    bookings_path.write_text("not valid JSON", encoding="utf-8")
    monkeypatch.setattr(tools, "BOOKINGS_PATH", bookings_path)

    with pytest.raises(json.JSONDecodeError):
        tools.get_booking("CW-1002")
