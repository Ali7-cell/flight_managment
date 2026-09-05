from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from flight_domain.models.flights import Flight, SeatClass
from flight_domain.models.bookings import Booking

def generate_ops_report(session: Session) -> dict[str, Any]:
    """
    Daily/weekly ops reporting:
    Load factor, revenue per flight pulled directly from Postgres (PRD §6).
    """
    flights = session.scalars(select(Flight).where(Flight.status == "scheduled")).all()
    report_items = []

    total_seats_all = 0
    total_booked_all = 0
    total_revenue_all = 0.0

    for f in flights:
        f_seats = int(getattr(f, "total_seats", 0))
        # calculate booked count
        raw_booked = session.scalar(
            select(func.coalesce(func.sum(Booking.quantity), 0)).where(
                Booking.flight_id == f.id,
                Booking.status == "confirmed",
            )
        )
        booked_count = int(raw_booked) if raw_booked is not None else 0

        raw_rev = session.scalar(
            select(func.coalesce(func.sum(Booking.total_amount), 0)).where(
                Booking.flight_id == f.id,
                Booking.status == "confirmed",
            )
        )
        revenue = float(raw_rev) if raw_rev is not None else 0.0

        load_factor = (float(booked_count) / float(f_seats) * 100.0) if f_seats > 0 else 0.0

        total_seats_all += f_seats
        total_booked_all += booked_count
        total_revenue_all += revenue

        report_items.append({
            "flight_id": str(f.id),
            "flight_number": str(f.flight_number),
            "origin": str(f.origin),
            "destination": str(f.destination),
            "total_capacity": f_seats,
            "booked_seats": booked_count,
            "load_factor_pct": round(load_factor, 1),
            "revenue": revenue,
        })

    overall_load_factor = (float(total_booked_all) / float(total_seats_all) * 100.0) if total_seats_all > 0 else 0.0

    return {
        "flights_reported": len(report_items),
        "overall_load_factor_pct": round(overall_load_factor, 1),
        "total_revenue": round(total_revenue_all, 2),
        "flight_breakdown": report_items,
    }
