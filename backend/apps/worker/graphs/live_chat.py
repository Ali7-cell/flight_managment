from __future__ import annotations

import re
import uuid
import logging
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from sqlalchemy import select
from flight_domain.db import SessionLocal
from flight_domain.models.flights import Flight, SeatClass
from flight_domain.clients.aviation import flight_info_lookup, FlightInfoResult
from flight_domain.domain.search import search_flights

logger = logging.getLogger("live_chat_graph")

class LiveChatState(TypedDict):
    message: str
    booking_id: Optional[str]
    user_email: Optional[str]
    intent: str  # "flight_info" | "booking_search" | "policy_question" | "other"
    flight_info_result: Optional[Dict[str, Any]]
    bookable_flights: Optional[List[Dict[str, Any]]]
    bookable_alternative_note: Optional[str]
    policy_pending: bool
    response_type: str
    final_reply: str

# Regex helpers for IATA codes and flight numbers
FLIGHT_NUM_PATTERN = re.compile(r"\b([A-Z0-9]{2}\s?\d{3,4})\b", re.IGNORECASE)
IATA_PAIR_PATTERN = re.compile(r"\b([A-Z]{3})\s*(?:to|-|->)\s*([A-Z]{3})\b", re.IGNORECASE)

def intent_router_node(state: LiveChatState) -> Dict[str, Any]:
    msg = (state.get("message") or "").strip().lower()

    # 1. Policy questions
    policy_keywords = [
        "refund", "cancel", "cancellation", "baggage", "bag", "luggage",
        "policy", "terms", "fee", "compensation", "delay compensation",
        "flex", "basic economy", "change flight", "reschedule"
    ]
    if any(k in msg for k in policy_keywords):
        return {"intent": "policy_question"}

    # 2. Flight status / schedule queries
    flight_info_keywords = [
        "status", "schedule", "track", "delay", "on time", "arrived", "departed", "live flight"
    ]
    has_flight_num = bool(FLIGHT_NUM_PATTERN.search(state.get("message") or ""))
    if any(k in msg for k in flight_info_keywords) or (has_flight_num and "book" not in msg):
        return {"intent": "flight_info"}

    # 3. Booking search queries
    booking_keywords = ["book", "ticket", "reserve", "available", "fly from", "search flight", "seat"]
    if any(k in msg for k in booking_keywords) or bool(IATA_PAIR_PATTERN.search(state.get("message") or "")):
        return {"intent": "booking_search"}

    return {"intent": "other"}

def flight_info_branch_node(state: LiveChatState) -> Dict[str, Any]:
    raw_msg = state.get("message") or ""
    
    # Extract flight number or route
    fl_match = FLIGHT_NUM_PATTERN.search(raw_msg)
    route_match = IATA_PAIR_PATTERN.search(raw_msg)

    flight_num = fl_match.group(1).replace(" ", "").upper() if fl_match else None
    origin = route_match.group(1).upper() if route_match else None
    dest = route_match.group(2).upper() if route_match else None

    # Call external Aviation API lookup
    lookup_res: FlightInfoResult = flight_info_lookup(
        origin=origin,
        destination=dest,
        flight_number=flight_num,
    )

    flight_data_dict = lookup_res.model_dump()

    # Critical Rule check: Does this external flight exist in our bookable Postgres inventory?
    bookable_matches: List[Dict[str, Any]] = []
    bookable_note: Optional[str] = None

    with SessionLocal() as db:
        if flight_num:
            # Query exact match in Postgres
            stmt = select(Flight).where(Flight.flight_number == flight_num)
            found = db.scalars(stmt).all()
            for f in found:
                bookable_matches.append({
                    "flight_number": f.flight_number,
                    "origin": f.origin,
                    "destination": f.destination,
                    "departure_at": f.departure_at.isoformat() if f.departure_at else None,
                    "status": f.status,
                })
            
            if not bookable_matches and lookup_res.flights:
                # Flight exists externally, but NOT in bookable Postgres inventory!
                ext_fl = lookup_res.flights[0]
                # Find closest bookable alternatives in Postgres
                alt_stmt = select(Flight).where(
                    Flight.origin == ext_fl.origin,
                    Flight.destination == ext_fl.destination,
                    Flight.status == "scheduled",
                ).limit(3)
                alts = db.scalars(alt_stmt).all()
                alt_list = [f"{a.flight_number} ({a.origin}→{a.destination})" for a in alts]
                
                if alt_list:
                    bookable_note = (
                        f"IMPORTANT: Flight {ext_fl.flight_number} exists in real-world airline schedules, "
                        f"but it is NOT available in our bookable flight inventory. "
                        f"Closest bookable alternatives with us on this route: {', '.join(alt_list)}."
                    )
                else:
                    bookable_note = (
                        f"IMPORTANT: Flight {ext_fl.flight_number} exists in real-world flight operations, "
                        f"but we do not currently operate bookable flights on this route."
                    )
        elif origin and dest:
            # Query route in Postgres
            alt_stmt = select(Flight).where(
                Flight.origin == origin,
                Flight.destination == dest,
                Flight.status == "scheduled",
            ).limit(3)
            alts = db.scalars(alt_stmt).all()
            for a in alts:
                bookable_matches.append({
                    "flight_number": a.flight_number,
                    "origin": a.origin,
                    "destination": a.destination,
                    "departure_at": a.departure_at.isoformat() if a.departure_at else None,
                    "status": a.status,
                })

    return {
        "flight_info_result": flight_data_dict,
        "bookable_flights": bookable_matches,
        "bookable_alternative_note": bookable_note,
        "response_type": "flight_info",
    }

def booking_search_branch_node(state: LiveChatState) -> Dict[str, Any]:
    raw_msg = state.get("message") or ""
    route_match = IATA_PAIR_PATTERN.search(raw_msg)
    origin = route_match.group(1).upper() if route_match else None
    dest = route_match.group(2).upper() if route_match else None

    bookable: List[Dict[str, Any]] = []
    with SessionLocal() as db:
        if origin and dest:
            stmt = select(Flight).where(
                Flight.origin == origin,
                Flight.destination == dest,
                Flight.status == "scheduled",
            )
            flights = db.scalars(stmt).all()
        else:
            # Return active scheduled flights
            stmt = select(Flight).where(Flight.status == "scheduled").limit(5)
            flights = db.scalars(stmt).all()

        for f in flights:
            classes = db.scalars(select(SeatClass).where(SeatClass.flight_id == f.id)).all()
            class_info = [
                {
                    "class_name": sc.class_name,
                    "price": float(sc.fare_base_amount),
                    "available": max(0, sc.total_seats - sc.booked_seats - sc.held_seats),
                }
                for sc in classes
            ]
            bookable.append({
                "id": str(f.id),
                "flight_number": f.flight_number,
                "origin": f.origin,
                "destination": f.destination,
                "departure_at": f.departure_at.isoformat() if f.departure_at else None,
                "arrival_at": f.arrival_at.isoformat() if f.arrival_at else None,
                "seat_classes": class_info,
            })

    return {
        "bookable_flights": bookable,
        "response_type": "booking_search",
        "flight_info_result": None,
    }

def policy_question_branch_node(state: LiveChatState) -> Dict[str, Any]:
    # Pauses / defers to human approval gate per Prompt 6
    return {
        "policy_pending": True,
        "response_type": "policy_question",
        "final_reply": "We are reviewing your policy question. A customer operations representative will inspect your request and reply to your registered email shortly.",
    }

def format_reply_node(state: LiveChatState) -> Dict[str, Any]:
    intent = state.get("intent", "other")
    rtype = state.get("response_type", "other")

    if rtype == "policy_question":
        return {
            "final_reply": "We're reviewing your policy question, and you'll receive an official reply by email."
        }

    if rtype == "flight_info":
        info_res = state.get("flight_info_result") or {}
        note = state.get("bookable_alternative_note")
        flights = info_res.get("flights", [])

        if not info_res.get("is_available", True):
            return {
                "final_reply": "Live flight data temporarily unavailable right now.",
            }

        if not flights:
            reply = "No real-world flight operations found matching your query."
            if note:
                reply += f"\n\n{note}"
            return {"final_reply": reply}

        fl = flights[0]
        reply_lines = [
            f"Flight Information for {fl.get('flight_number')} ({fl.get('airline')}):",
            f"• Route: {fl.get('origin')} → {fl.get('destination')}",
            f"• Status: {fl.get('status', 'scheduled').upper()}",
            f"• Scheduled Departure: {fl.get('scheduled_departure') or 'TBD'}",
            f"• Scheduled Arrival: {fl.get('scheduled_arrival') or 'TBD'}",
        ]
        if note:
            reply_lines.append(f"\n{note}")

        return {"final_reply": "\n".join(reply_lines)}

    if rtype == "booking_search":
        bookable = state.get("bookable_flights") or []
        if not bookable:
            return {
                "final_reply": "We currently do not have scheduled bookable flights for this route. Please try another destination or date."
            }
        reply_lines = ["Available Bookable Flights in our system:"]
        for b in bookable:
            classes_str = ", ".join(
                [f"{c['class_name']}: ${c['price']:.0f} ({c['available']} left)" for c in b.get("seat_classes", [])]
            )
            reply_lines.append(f"• Flight {b['flight_number']} ({b['origin']} → {b['destination']}) - {classes_str}")
        return {"final_reply": "\n".join(reply_lines)}

    return {
        "final_reply": (
            "Hello! I can help you with real-time flight status (e.g. 'Status of PK301'), "
            "searching bookable flights (e.g. 'Flights from KHI to ISB'), or policy inquiries regarding refunds and baggage."
        )
    }

def route_branch(state: LiveChatState) -> str:
    intent = state.get("intent")
    if intent == "flight_info":
        return "flight_info_branch"
    elif intent == "booking_search":
        return "booking_search_branch"
    elif intent == "policy_question":
        return "policy_question_branch"
    return "format_reply"

# Build LangGraph StateGraph
builder = StateGraph(LiveChatState)
builder.add_node("intent_router", intent_router_node)
builder.add_node("flight_info_branch", flight_info_branch_node)
builder.add_node("booking_search_branch", booking_search_branch_node)
builder.add_node("policy_question_branch", policy_question_branch_node)
builder.add_node("format_reply", format_reply_node)

builder.add_edge(START, "intent_router")
builder.add_conditional_edges(
    "intent_router",
    route_branch,
    {
        "flight_info_branch": "flight_info_branch",
        "booking_search_branch": "booking_search_branch",
        "policy_question_branch": "policy_question_branch",
        "format_reply": "format_reply",
    },
)

builder.add_edge("flight_info_branch", "format_reply")
builder.add_edge("booking_search_branch", "format_reply")
builder.add_edge("policy_question_branch", "format_reply")
builder.add_edge("format_reply", END)

live_chat_graph = builder.compile()
