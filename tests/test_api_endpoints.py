import uuid

def test_missing_idempotency_key_returns_400(client, seed_data):
    """
    Every mutating endpoint requires and validates the Idempotency-Key header.
    """
    payload = {
        "flight_id": str(seed_data["flight"].id),
        "seat_class_id": str(seed_data["economy_class"].id),
        "quantity": 1,
        "passenger_email": "test@example.com",
        "passenger_name": "Test Passenger",
    }
    # Request without Idempotency-Key header
    resp = client.post("/bookings/hold", json=payload)
    assert resp.status_code == 422 or resp.status_code == 400

def test_search_flights_api(client, seed_data):
    resp = client.get("/search/flights?origin=LHR&destination=DXB")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    flight = data[0]
    assert flight["flight_number"] == "BA105"
    assert len(flight["seat_classes"]) >= 1

def test_booking_hold_and_confirm_flow(client, seed_data):
    headers = {"Idempotency-Key": f"test-key-{uuid.uuid4()}"}
    hold_payload = {
        "flight_id": str(seed_data["flight"].id),
        "seat_class_id": str(seed_data["economy_class"].id),
        "quantity": 1,
        "passenger_email": "api_user@example.com",
        "passenger_name": "API User",
    }

    # 1. Hold seat
    hold_resp = client.post("/bookings/hold", json=hold_payload, headers=headers)
    assert hold_resp.status_code == 200
    hold_data = hold_resp.json()
    assert "hold_id" in hold_data

    # 2. Confirm booking
    confirm_headers = {"Idempotency-Key": f"confirm-key-{uuid.uuid4()}"}
    confirm_payload = {
        "hold_id": hold_data["hold_id"],
        "payment_method_id": "pm_card_visa",
    }
    confirm_resp = client.post(
        f"/bookings/{hold_data['hold_id']}/confirm",
        json=confirm_payload,
        headers=confirm_headers,
    )
    assert confirm_resp.status_code == 200
    booking_data = confirm_resp.json()
    assert booking_data["status"] == "confirmed"
    assert "booking_reference" in booking_data

    # 3. Retrieve booking
    get_resp = client.get(f"/bookings/{booking_data['booking_id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["booking_reference"] == booking_data["booking_reference"]

def test_waitlist_join_api(client, seed_data):
    headers = {"Idempotency-Key": f"wl-key-{uuid.uuid4()}"}
    payload = {
        "flight_id": str(seed_data["flight"].id),
        "seat_class_id": str(seed_data["economy_class"].id),
        "quantity": 1,
        "passenger_email": "waitlist_user@example.com",
        "passenger_name": "Waitlist User",
    }
    resp = client.post("/waitlist", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "waitlist_entry_id" in data
    assert data["status"] == "waiting"
