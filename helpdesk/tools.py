import json
from typing import TypedDict

from .config import BOOKINGS_PATH


class Booking(TypedDict):
    id: str
    status: str
    bike_type: str
    bikes: int
    start: str
    end: str
    add_ons: list[str]
    rental_price_eur: float
    booking_fee_eur: float
    deposit_eur: float
    paid_with: str


class BookingInfo(TypedDict):
    booking: Booking | None
    booking_id: str
    error: str | None


def get_booking(booking_id: str) -> BookingInfo:
    if not isinstance(booking_id, str) or not booking_id.strip():
        raise ValueError("booking_id must be a non-empty string")

    with BOOKINGS_PATH.open(mode="r", encoding="utf-8") as file:
        bookings: list[Booking] = json.load(file)

    for booking in bookings:
        if booking["id"] == booking_id:
            return BookingInfo(booking=booking, booking_id=booking_id, error=None)

    return BookingInfo(booking=None, booking_id=booking_id, error="booking not found")
