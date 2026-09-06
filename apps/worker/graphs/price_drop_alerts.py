from typing import TypedDict, Any
from datetime import timedelta
from decimal import Decimal
from langgraph.graph import StateGraph, START, END
from sqlalchemy import select, func
from flight_domain.db import SessionLocal
from flight_domain.models.alerts import PriceAlert
from flight_domain.models.flights import Flight, SeatClass
from flight_domain.models.base import utcnow
from flight_domain.clients.gmail import gmail_client

try:
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from checkpointer import checkpointer  # type: ignore

class PriceDropAlertState(TypedDict):
    alerts_evaluated: int
    alerts_sent: int

def scan_and_send_price_drops(state: PriceDropAlertState) -> dict:
    evaluated = 0
    sent = 0
    now_dt = utcnow()
    cooldown = timedelta(days=3)  # Per-passenger cooldown to prevent spam

    with SessionLocal() as session:
        alerts = session.scalars(select(PriceAlert)).all()
        for alert in alerts:
            evaluated += 1
            if alert.last_notified_at and (now_dt - alert.last_notified_at) < cooldown:
                continue

            # Find lowest available base fare for this route
            lowest_fare = session.scalar(
                select(func.min(SeatClass.fare_base_amount))
                .join(Flight, SeatClass.flight_id == Flight.id)
                .where(
                    Flight.origin == alert.origin,
                    Flight.destination == alert.destination,
                    Flight.status == "scheduled",
                    Flight.departure_at > now_dt,
                    (SeatClass.total_seats - (SeatClass.booked_seats + SeatClass.held_seats)) > 0,
                )
            )

            if lowest_fare is not None:
                target = Decimal(str(alert.target_price))
                last_price = Decimal(str(alert.last_notified_price)) if alert.last_notified_price else None

                # Must be at or below target price
                if lowest_fare <= target:
                    # De-duplication: Must be either first notification or a significant drop (>= 10%)
                    is_significant_drop = True
                    if last_price and last_price > Decimal("0.00"):
                        drop_pct = (last_price - lowest_fare) / last_price
                        if drop_pct < Decimal("0.10"):
                            is_significant_drop = False

                    if is_significant_drop:
                        gmail_client.send(
                            to=alert.passenger_email,
                            subject=f"Price Drop Alert: {alert.origin} to {alert.destination} now from ${lowest_fare}!",
                            body=(
                                f"Great news! We detected a price drop on your watched route {alert.origin} -> {alert.destination}.\n\n"
                                f"Current lowest fare: ${lowest_fare} (Your target: ${alert.target_price}).\n"
                                f"Book now before seats sell out!"
                            ),
                            metadata={"alert_id": str(alert.id), "fare": str(lowest_fare)},
                        )
                        alert.last_notified_price = lowest_fare
                        alert.last_notified_at = now_dt
                        sent += 1

        session.commit()

    return {"alerts_evaluated": evaluated, "alerts_sent": sent}

builder = StateGraph(PriceDropAlertState)
builder.add_node("scan_and_send_price_drops", scan_and_send_price_drops)
builder.add_edge(START, "scan_and_send_price_drops")
builder.add_edge("scan_and_send_price_drops", END)

price_drop_alerts_graph = builder.compile(checkpointer=checkpointer)
