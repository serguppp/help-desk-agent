from datetime import timedelta
from decimal import Decimal
from typing import TypedDict

from helpdesk.booking import Booking, BookingInfo, get_booking

from .config import TIME_NOW


class RefundResult(TypedDict):
    booking: Booking
    refund: Decimal
    message: str | None


def calculate_refund(booking_id: str) -> BookingInfo | RefundResult:
    result = get_booking(booking_id)
    booking = result["booking"]

    if booking is None:
        return result

    if booking["status"] != "confirmed":
        return RefundResult(
            booking=booking,
            refund=Decimal("0.0"),
            message=f"You cannot cancel booking with status {booking['status']}.",
        )

    remaining_time = booking["start"] - TIME_NOW

    if remaining_time >= timedelta(hours=48):
        refund_rate = Decimal("1.0")
    elif remaining_time >= timedelta(hours=24):
        refund_rate = Decimal("0.5")
    else:
        refund_rate = Decimal("0.0")

    rental_refund = booking["rental_price_eur"] * refund_rate
    total_refund = rental_refund + booking["deposit_eur"]

    return RefundResult(booking=booking, refund=total_refund, message=None)
