from typing import TypedDict, Any
from zoneinfo import ZoneInfo
from langgraph.graph import StateGraph, START, END
from flight_domain.db import SessionLocal
from flight_domain.domain.policy import flights_needing_checkin_reminder
from flight_domain.clients.gmail import gmail_client

try:
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from checkpointer import checkpointer  # type: ignore

class CheckinReminderState(TypedDict):
    flights: list[dict[str, Any]]
    sent_count: int

def find_upcoming_flights(state: CheckinReminderState) -> dict:
    with SessionLocal() as session:
        # Departure between now+23h and now+25h, status='scheduled' (suppresses cancelled flights)
        flights = flights_needing_checkin_reminder(session)
    return {"flights": flights, "sent_count": 0}

def send_reminders(state: CheckinReminderState) -> dict:
    count = 0
    for f in state.get("flights", []):
        origin_tz = f.get("origin_tz", "UTC")
        dep_utc = f["departure_at"]
        local_dep = dep_utc.astimezone(ZoneInfo(origin_tz))
        
        gmail_client.send_checkin_reminder(
            flight=f,
            local_departure=local_dep,
            passenger_email=f.get("passenger_email", "passenger@example.com"),
        )
        count += 1
    return {"sent_count": count}

builder = StateGraph(CheckinReminderState)
builder.add_node("find_upcoming_flights", find_upcoming_flights)
builder.add_node("send_reminders", send_reminders)
builder.add_edge(START, "find_upcoming_flights")
builder.add_edge("find_upcoming_flights", "send_reminders")
builder.add_edge("send_reminders", END)

checkin_reminder_graph = builder.compile(checkpointer=checkpointer)
