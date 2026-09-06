import uuid
import httpx

def run_tests():
    base = "http://127.0.0.1:8000"
    client = httpx.Client(base_url=base, timeout=15.0)

    print("========================================")
    print("1. Testing GET /healthz")
    print("========================================")
    r = client.get("/healthz")
    print("Response:", r.status_code, r.json())
    assert r.status_code == 200

    print("\n========================================")
    print("2. Testing GET /search/flights")
    print("========================================")
    r = client.get("/search/flights?origin=LHR&destination=DXB")
    print("Status:", r.status_code)
    flights = r.json()
    assert len(flights) >= 1
    flight = flights[0]
    print("Flight Number:", flight["flight_number"])
    print("Route:", flight["origin"], "->", flight["destination"])
    seat_class = flight["seat_classes"][0]
    print("Seat Class:", seat_class["class_name"], "| Available:", seat_class["available_seats"], "| Fare:", seat_class["fare_base_amount"], seat_class["currency"])

    print("\n========================================")
    print("3. Testing POST /bookings/hold")
    print("========================================")
    idempotency_key_hold = str(uuid.uuid4())
    hold_payload = {
        "flight_id": flight["flight_id"],
        "seat_class_id": seat_class["seat_class_id"],
        "quantity": 1,
        "passenger_email": "ali.test@example.com",
        "passenger_name": "Ali Khan",
    }
    r = client.post(
        "/bookings/hold",
        json=hold_payload,
        headers={"Idempotency-Key": idempotency_key_hold},
    )
    print("Status:", r.status_code)
    hold_data = r.json()
    print("Hold ID:", hold_data.get("hold_id"))
    print("Expires At:", hold_data.get("expires_at"))
    assert r.status_code == 200
    hold_id = hold_data["hold_id"]

    print("\n========================================")
    print("4. Testing POST /bookings/{hold_id}/confirm")
    print("========================================")
    idempotency_key_confirm = str(uuid.uuid4())
    confirm_payload = {
        "hold_id": hold_id,
        "payment_method_id": "pm_card_visa",
    }
    r = client.post(
        f"/bookings/{hold_id}/confirm",
        json=confirm_payload,
        headers={"Idempotency-Key": idempotency_key_confirm},
    )
    print("Status:", r.status_code)
    booking_data = r.json()
    print("Booking Ref:", booking_data.get("booking_reference"))
    print("Status:", booking_data.get("status"))
    print("Total Amount:", booking_data.get("total_amount"), booking_data.get("currency"))
    assert r.status_code == 200
    booking_id = booking_data["booking_id"]
    booking_ref = booking_data["booking_reference"]

    print("\n========================================")
    print("5. Testing GET /bookings/{booking_id}")
    print("========================================")
    r = client.get(f"/bookings/{booking_id}")
    print("Status:", r.status_code)
    details = r.json()
    print("Retrieved Booking Ref:", details.get("booking_reference"))
    print("Passenger ID:", details.get("passenger_id"))
    print("Booking Status:", details.get("status"))
    assert r.status_code == 200
    assert details["booking_reference"] == booking_ref

    print("\n========================================")
    print("6. Testing POST /waitlist (Join waitlist)")
    print("========================================")
    idempotency_key_wl = str(uuid.uuid4())
    wl_payload = {
        "flight_id": flight["flight_id"],
        "seat_class_id": seat_class["seat_class_id"],
        "quantity": 1,
        "passenger_email": "waitlist.passenger@example.com",
        "passenger_name": "Waitlist Passenger",
    }
    r = client.post(
        "/waitlist",
        json=wl_payload,
        headers={"Idempotency-Key": idempotency_key_wl},
    )
    print("Status:", r.status_code)
    wl_data = r.json()
    print("Waitlist ID:", wl_data.get("waitlist_id"))
    print("Status:", wl_data.get("status"))
    assert r.status_code == 200

    print("\n========================================")
    print("7. Testing GET /payments/{payment_id}/status")
    print("========================================")
    payment_id = booking_data.get("payment_id")
    if payment_id:
        r = client.get(f"/payments/{payment_id}/status")
        print("Status:", r.status_code)
        pay_status = r.json()
        print("Payment Status:", pay_status.get("status"))
        print("Provider Payment ID:", pay_status.get("provider_payment_id"))
        assert r.status_code == 200

    print("\n========================================")
    print("8. Testing POST /bookings/{booking_id}/cancel")
    print("========================================")
    idempotency_key_cancel = str(uuid.uuid4())
    r = client.post(
        f"/bookings/{booking_id}/cancel",
        json={"reason": "Customer cancellation test"},
        headers={"Idempotency-Key": idempotency_key_cancel},
    )
    print("Status:", r.status_code)
    cancel_data = r.json()
    print("Cancel Response:", cancel_data)
    assert r.status_code == 200
    assert cancel_data["status"] == "cancelled"

    print("\n========================================")
    print(">>> ALL LIVE API ENDPOINTS PASSED SUCCESSFULLY! <<<")
    print("========================================")

if __name__ == "__main__":
    run_tests()
