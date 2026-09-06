from __future__ import annotations

import os
import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
import urllib.request
import urllib.parse
import json

logger = logging.getLogger("aviation_client")

class FlightInfoItem(BaseModel):
    flight_number: str
    airline: str
    origin: str
    destination: str
    scheduled_departure: Optional[str] = None
    scheduled_arrival: Optional[str] = None
    status: str = "scheduled"

class FlightInfoResult(BaseModel):
    success: bool = True
    is_available: bool = True
    error_message: Optional[str] = None
    provider: str = "aviationstack"
    cached: bool = False
    flights: List[FlightInfoItem] = Field(default_factory=list)

# In-memory TTL Cache: 10 minutes (600 seconds)
_CACHE_TTL_SECONDS = 600
_flight_cache: Dict[str, Tuple[float, FlightInfoResult]] = {}

def _get_cache_key(
    origin: Optional[str],
    destination: Optional[str],
    flight_number: Optional[str],
    date: Optional[str],
) -> str:
    parts = [
        (origin or "").strip().upper(),
        (destination or "").strip().upper(),
        (flight_number or "").strip().upper(),
        (date or "").strip(),
    ]
    return ":".join(parts)

def clear_aviation_cache() -> None:
    global _flight_cache
    _flight_cache.clear()

def _query_aviationstack(
    api_key: str,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    flight_number: Optional[str] = None,
    date: Optional[str] = None,
) -> List[FlightInfoItem]:
    params: Dict[str, str] = {"access_key": api_key, "limit": "10"}
    if origin:
        params["dep_iata"] = origin.strip().upper()
    if destination:
        params["arr_iata"] = destination.strip().upper()
    if flight_number:
        # e.g., PK301 or PK 301
        params["flight_iata"] = flight_number.strip().replace(" ", "").upper()
    if date:
        params["flight_date"] = date.strip()

    url = f"http://api.aviationstack.com/v1/flights?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "FlightManagementSystem/1.0"})
    
    with urllib.request.urlopen(req, timeout=8) as resp:
        if resp.status != 200:
            raise RuntimeError(f"AviationStack returned status {resp.status}")
        raw_data = json.loads(resp.read().decode("utf-8"))

    if "error" in raw_data:
        err_info = raw_data.get("error", {})
        msg = err_info.get("message") or err_info.get("info") or str(err_info)
        raise RuntimeError(f"AviationStack API Error: {msg}")

    results: List[FlightInfoItem] = []
    for item in raw_data.get("data", []):
        fl_iata = (item.get("flight") or {}).get("iata") or (item.get("flight") or {}).get("number") or "Unknown"
        airline_name = (item.get("airline") or {}).get("name") or "Commercial Airline"
        dep = item.get("departure") or {}
        arr = item.get("arrival") or {}
        status_val = item.get("flight_status") or "scheduled"

        results.append(
            FlightInfoItem(
                flight_number=fl_iata,
                airline=airline_name,
                origin=dep.get("iata") or origin or "N/A",
                destination=arr.get("iata") or destination or "N/A",
                scheduled_departure=dep.get("scheduled"),
                scheduled_arrival=arr.get("scheduled"),
                status=status_val,
            )
        )
    return results

def _query_airlabs_fallback(
    api_key: str,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    flight_number: Optional[str] = None,
    date: Optional[str] = None,
) -> List[FlightInfoItem]:
    params: Dict[str, str] = {"api_key": api_key}
    if origin:
        params["dep_iata"] = origin.strip().upper()
    if destination:
        params["arr_iata"] = destination.strip().upper()
    if flight_number:
        params["flight_iata"] = flight_number.strip().replace(" ", "").upper()

    url = f"https://airlabs.co/api/v9/flights?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "FlightManagementSystem/1.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        if resp.status != 200:
            raise RuntimeError(f"AirLabs returned status {resp.status}")
        raw_data = json.loads(resp.read().decode("utf-8"))

    results: List[FlightInfoItem] = []
    for item in raw_data.get("response", []):
        results.append(
            FlightInfoItem(
                flight_number=item.get("flight_iata") or item.get("flight_number") or "Unknown",
                airline=item.get("airline_name") or "Commercial Airline",
                origin=item.get("dep_iata") or origin or "N/A",
                destination=item.get("arr_iata") or destination or "N/A",
                scheduled_departure=item.get("dep_time"),
                scheduled_arrival=item.get("arr_time"),
                status=item.get("status") or "scheduled",
            )
        )
    return results

def flight_info_lookup(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    flight_number: Optional[str] = None,
    date: Optional[str] = None,
) -> FlightInfoResult:
    """Lookup real external flight schedule & status.
    Informational only — NOT for bookable inventory.
    Cached for 10 minutes per query. Never throws on API failure.
    """
    cache_key = _get_cache_key(origin, destination, flight_number, date)
    now = time.time()

    # 1. Check in-memory 10-minute cache
    if cache_key in _flight_cache:
        cached_time, cached_res = _flight_cache[cache_key]
        if now - cached_time < _CACHE_TTL_SECONDS:
            res_copy = cached_res.model_copy()
            res_copy.cached = True
            return res_copy

    provider = os.getenv("AVIATION_PROVIDER", "aviationstack").lower()
    aviationstack_key = os.getenv("AVIATIONSTACK_API_KEY", "")
    airlabs_key = os.getenv("AIRLABS_API_KEY", "")

    # If no provider API key is configured, return graceful typed unavailable response
    if provider == "aviationstack" and not aviationstack_key:
        logger.warning("AviationStack API key not configured in environment.")
        return FlightInfoResult(
            success=False,
            is_available=False,
            error_message="Live flight data temporarily unavailable (Aviation API key not configured).",
            provider="aviationstack",
            flights=[],
        )

    if provider == "airlabs" and not airlabs_key:
        logger.warning("AirLabs API key not configured in environment.")
        return FlightInfoResult(
            success=False,
            is_available=False,
            error_message="Live flight data temporarily unavailable (Fallback API key not configured).",
            provider="airlabs",
            flights=[],
        )

    try:
        if provider == "aviationstack":
            items = _query_aviationstack(aviationstack_key, origin, destination, flight_number, date)
        elif provider == "airlabs":
            items = _query_airlabs_fallback(airlabs_key, origin, destination, flight_number, date)
        else:
            # Unsupported provider config fallback
            items = _query_aviationstack(aviationstack_key, origin, destination, flight_number, date)

        result = FlightInfoResult(
            success=True,
            is_available=True,
            provider=provider,
            cached=False,
            flights=items,
        )
        # Store in cache
        _flight_cache[cache_key] = (now, result)
        return result

    except Exception as exc:
        logger.error(f"External flight info lookup failed ({provider}): {exc}", exc_info=True)
        # If primary failed and fallback configured, try airlabs
        if provider == "aviationstack" and airlabs_key:
            try:
                fallback_items = _query_airlabs_fallback(airlabs_key, origin, destination, flight_number, date)
                res = FlightInfoResult(
                    success=True,
                    is_available=True,
                    provider="airlabs_fallback",
                    cached=False,
                    flights=fallback_items,
                )
                _flight_cache[cache_key] = (now, res)
                return res
            except Exception as fallback_err:
                logger.error(f"Fallback AirLabs also failed: {fallback_err}")

        return FlightInfoResult(
            success=False,
            is_available=False,
            error_message="Live flight data temporarily unavailable right now.",
            provider=provider,
            flights=[],
        )
