import json
from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from .config import BOOKINGS_PATH


class Booking(TypedDict):
    id: str
    status: str
    bike_type: str
    bikes: int
    start: datetime
    end: datetime
    add_ons: list[str]
    rental_price_eur: Decimal
    booking_fee_eur: Decimal
    deposit_eur: Decimal
    paid_with: str


class BookingInfo(TypedDict):
    booking: Booking | None
    booking_id: str
    error: str | None


def parse_booking(raw: dict) -> Booking:
    return Booking(
        id=raw["id"],
        status=raw["status"],
        bike_type=raw["bike_type"],
        bikes=raw["bikes"],
        start=datetime.fromisoformat(raw["start"]),
        end=datetime.fromisoformat(raw["end"]),
        add_ons=raw["add_ons"],
        rental_price_eur=Decimal(str(raw["rental_price_eur"])),
        booking_fee_eur=Decimal(str(raw["booking_fee_eur"])),
        deposit_eur=Decimal(str(raw["deposit_eur"])),
        paid_with=raw["paid_with"],
    )


def get_booking(booking_id: str) -> BookingInfo:
    if not isinstance(booking_id, str) or not booking_id.strip():
        raise ValueError("booking_id must be a non-empty string")

    with BOOKINGS_PATH.open(encoding="utf-8") as file:
        raw_bookings = json.load(file, parse_float=Decimal)

    bookings = [parse_booking(raw) for raw in raw_bookings]

    for booking in bookings:
        if booking["id"] == booking_id:
            return BookingInfo(
                booking=booking,
                booking_id=booking_id,
                error=None,
            )

    return BookingInfo(
        booking=None,
        booking_id=booking_id,
        error="Booking not found.",
    )
