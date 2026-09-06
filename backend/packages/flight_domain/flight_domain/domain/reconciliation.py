from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from flight_domain.models.flights import SeatClass, Flight
from flight_domain.models.bookings import Booking
from flight_domain.domain.audit import record_audit_log
from flight_domain.clients.gmail import gmail_client

def run_inventory_reconciliation(session: Session) -> dict[str, Any]:
    """
    Scheduled reconciliation audit job:
    Compares seat_classes.booked_seats against actual count of confirmed bookings per class.
    Logs drift to audit_log with actor 'system:reconciliation' and alerts ops via email.
    """
    seat_classes = session.scalars(select(SeatClass)).all()
    discrepancies = []
    total_checked = 0

    for sc in seat_classes:
        total_checked += 1
        actual_confirmed_sum = session.scalar(
            select(func.coalesce(func.sum(Booking.quantity), 0))
            .where(
                Booking.seat_class_id == sc.id,
                Booking.status == "confirmed",
            )
        ) or 0

        recorded_booked = sc.booked_seats
        if recorded_booked != actual_confirmed_sum:
            drift = recorded_booked - actual_confirmed_sum
            flight = session.get(Flight, sc.flight_id)
            flight_num = flight.flight_number if flight else "Unknown"

            disc_item = {
                "seat_class_id": str(sc.id),
                "flight_number": flight_num,
                "class_name": sc.class_name,
                "recorded_booked_seats": recorded_booked,
                "actual_confirmed_sum": actual_confirmed_sum,
                "drift": drift,
            }
            discrepancies.append(disc_item)

            record_audit_log(
                session,
                actor_type="system:reconciliation",
                actor_id="worker_reconciliation_graph",
                action="inventory_drift_detected",
                entity_type="seat_classes",
                entity_id=sc.id,
                before_json={"recorded_booked": recorded_booked},
                after_json={"actual_confirmed": actual_confirmed_sum, "drift": drift},
            )

    if discrepancies:
        gmail_client.send(
            to="ops-alerts@yourdomain.com",
            subject=f"[ALERT] Inventory Drift Detected in {len(discrepancies)} Seat Classes",
            body=(
                f"Reconciliation audit identified inventory count mismatches:\n\n"
                f"{discrepancies}\n\n"
                f"Please review database state immediately."
            ),
            metadata={"discrepancies_count": len(discrepancies)},
        )

    session.flush()
    return {
        "total_classes_checked": total_checked,
        "discrepancies_count": len(discrepancies),
        "discrepancies": discrepancies,
        "status": "drift_detected" if discrepancies else "clean",
    }
