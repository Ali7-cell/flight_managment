import pytest
from unittest.mock import patch, MagicMock
from flight_domain.clients.aviation import (
    flight_info_lookup,
    FlightInfoResult,
    FlightInfoItem,
    clear_aviation_cache,
)
from apps.worker.graphs.live_chat import live_chat_graph, LiveChatState

def test_aviation_lookup_graceful_missing_key():
    clear_aviation_cache()
    with patch.dict("os.environ", {"AVIATIONSTACK_API_KEY": "", "AVIATION_PROVIDER": "aviationstack"}):
        res = flight_info_lookup(flight_number="PK301")
        assert res.success is False
        assert res.is_available is False
        assert "temporarily unavailable" in res.error_message
        assert res.flights == []

def test_aviation_lookup_caching():
    clear_aviation_cache()
    mock_item = FlightInfoItem(
        flight_number="PK301",
        airline="Pakistan International Airlines",
        origin="KHI",
        destination="ISB",
        scheduled_departure="2026-09-10T08:00:00Z",
        scheduled_arrival="2026-09-10T10:00:00Z",
        status="scheduled",
    )
    with patch("flight_domain.clients.aviation._query_aviationstack", return_value=[mock_item]):
        with patch.dict("os.environ", {"AVIATIONSTACK_API_KEY": "fake_test_key", "AVIATION_PROVIDER": "aviationstack"}):
            res1 = flight_info_lookup(flight_number="PK301")
            assert res1.success is True
            assert res1.cached is False
            assert len(res1.flights) == 1
            assert res1.flights[0].flight_number == "PK301"

            # Second call should be served from 10-minute cache
            res2 = flight_info_lookup(flight_number="PK301")
            assert res2.success is True
            assert res2.cached is True

def test_live_chat_intent_routing_policy():
    state: LiveChatState = {
        "message": "What is your refund policy for basic economy tickets?",
        "booking_id": None,
        "user_email": None,
        "intent": "other",
        "flight_info_result": None,
        "bookable_flights": None,
        "bookable_alternative_note": None,
        "policy_pending": False,
        "response_type": "other",
        "final_reply": "",
    }
    out = live_chat_graph.invoke(state)
    assert out["intent"] == "policy_question"
    assert out["response_type"] == "policy_question"
    assert out["policy_pending"] is True
    assert "reviewing your policy question" in out["final_reply"]

def test_live_chat_intent_routing_flight_info_and_comparison():
    clear_aviation_cache()
    mock_item = FlightInfoItem(
        flight_number="PK786",
        airline="Pakistan International Airlines",
        origin="KHI",
        destination="LHE",
        scheduled_departure="2026-09-10T12:00:00Z",
        scheduled_arrival="2026-09-10T13:45:00Z",
        status="active",
    )
    with patch("flight_domain.clients.aviation._query_aviationstack", return_value=[mock_item]):
        with patch.dict("os.environ", {"AVIATIONSTACK_API_KEY": "fake_test_key", "AVIATION_PROVIDER": "aviationstack"}):
            state: LiveChatState = {
                "message": "Can you check status of flight PK 786?",
                "booking_id": None,
                "user_email": None,
                "intent": "other",
                "flight_info_result": None,
                "bookable_flights": None,
                "bookable_alternative_note": None,
                "policy_pending": False,
                "response_type": "other",
                "final_reply": "",
            }
            out = live_chat_graph.invoke(state)
            assert out["intent"] == "flight_info"
            assert out["response_type"] == "flight_info"
            assert "PK786" in out["final_reply"]
            # Critical rule check: states that it's NOT in our bookable inventory
            assert "NOT available in our bookable flight inventory" in out["final_reply"] or "IMPORTANT" in out["final_reply"]
