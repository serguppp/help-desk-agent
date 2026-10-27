from datetime import timedelta
from decimal import Decimal
from typing import TypedDict

from .booking import Booking, BookingInfo, get_booking
from .config import TIME_NOW

RENTAL_REFUND_METHODS = {
    "card": "Same card within 5 working days.",
    "voucher": "New voucher, never money.",
}
POLICY_SOURCE = "data/policies/cancellations.md"


class RefundResult(TypedDict):
    booking: Booking
    cancellation_allowed: bool
    rental_refund_eur: Decimal
    deposit_refund_eur: Decimal
    booking_fee_refund_eur: Decimal
    refund: Decimal
    rental_refund_method: str | None
    deposit_refund_method: str | None
    policy_source: str
    message: str | None


def calculate_refund(booking_id: str) -> BookingInfo | RefundResult:
    result = get_booking(booking_id)
    booking = result["booking"]
    if booking is None:
        return result

    if booking["status"] != "confirmed":
        return RefundResult(
            booking=booking,
            cancellation_allowed=False,
            rental_refund_eur=Decimal(0),
            deposit_refund_eur=Decimal(0),
            booking_fee_refund_eur=Decimal(0),
            refund=Decimal(0),
            rental_refund_method=None,
            deposit_refund_method=None,
            policy_source=POLICY_SOURCE,
            message=f"You cannot cancel booking with status {booking['status']}.",
        )

    payment_method = booking["paid_with"]
    if payment_method not in RENTAL_REFUND_METHODS:
        raise ValueError(f"Unsupported payment method: {payment_method}")

    remaining_time = booking["start"] - TIME_NOW
    if remaining_time >= timedelta(hours=48):
        refund_rate = Decimal(1)
    elif remaining_time >= timedelta(hours=24):
        refund_rate = Decimal("0.5")
    else:
        refund_rate = Decimal(0)

    rental_refund = booking["rental_price_eur"] * refund_rate
    deposit_refund = booking["deposit_eur"]

    return RefundResult(
        booking=booking,
        cancellation_allowed=True,
        rental_refund_eur=rental_refund,
        deposit_refund_eur=deposit_refund,
        booking_fee_refund_eur=Decimal(0),
        refund=rental_refund + deposit_refund,
        rental_refund_method=(
            RENTAL_REFUND_METHODS[payment_method] if rental_refund > 0 else None
        ),
        deposit_refund_method=(
            "Original deposit payment method." if deposit_refund > 0 else None
        ),
        policy_source=POLICY_SOURCE,
        message=None,
    )
