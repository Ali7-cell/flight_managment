# API Endpoints & Schemas — FastAPI

All endpoints below are FastAPI's (LangGraph never exposes a public HTTP surface — it's triggered by the scheduler-trigger endpoints in `apps/worker`, listed separately at the bottom). Every mutating endpoint requires an `Idempotency-Key` header and validates it against `idempotency_keys` inside the same `flight_domain` transaction. Auth: customer endpoints require a Supabase JWT (`Authorization: Bearer <token>`); admin endpoints additionally require the caller's `admin_users.role` to match.

## Endpoint index

| Method | Path | Owner | Auth | Domain |
|---|---|---|---|---|
| POST | `/admin/flights` | FastAPI | super_admin, ops_agent | Admin |
| PATCH | `/admin/flights/{flight_id}` | FastAPI | super_admin, ops_agent | Admin |
| POST | `/admin/flights/{flight_id}/cancel` | FastAPI | super_admin | Admin |
| PATCH | `/admin/flights/{flight_id}/seat-classes` | FastAPI | super_admin | Admin |
| GET | `/admin/flights/{flight_id}/audit-log` | FastAPI | super_admin, ops_agent | Admin |
| GET | `/search/flights` | FastAPI | public | Search |
| GET | `/fares/{fare_class_id}/rules` | FastAPI | public | Search |
| POST | `/bookings/hold` | FastAPI | customer or guest | Booking |
| POST | `/bookings/group-hold` | FastAPI | customer or guest | Booking |
| POST | `/bookings/{hold_id}/confirm` | FastAPI | customer or guest | Booking |
| GET | `/bookings/{booking_id}` | FastAPI | owner or admin | Booking |
| POST | `/bookings/{booking_id}/cancel` | FastAPI | owner or admin | Cancellation |
| POST | `/bookings/{booking_id}/refund` | FastAPI | owner or admin | Refund |
| GET | `/refunds/{refund_id}` | FastAPI | owner or admin | Refund |
| POST | `/waitlist` | FastAPI | customer or guest | Waitlist |
| GET | `/waitlist/{flight_id}/position` | FastAPI | owner | Waitlist |
| POST | `/payments/webhook` | FastAPI | provider signature | Payments |
| GET | `/payments/{payment_id}/status` | FastAPI | owner or admin | Payments |
| POST | `/auth/signup` | FastAPI (proxies Supabase Auth) | public | Auth |
| POST | `/auth/login` | FastAPI (proxies Supabase Auth) | public | Auth |
| POST | `/policy/questions` | FastAPI | customer | Policy/RAG |
| GET | `/internal/policy/pending` | FastAPI | ops_agent | Policy/RAG |
| POST | `/internal/policy/{run_id}/approve` | FastAPI | ops_agent | Policy/RAG |
| POST | `/internal/policy/{run_id}/reject` | FastAPI | ops_agent | Policy/RAG |

Worker trigger endpoints (internal, not customer-facing, not in public OpenAPI schema):

| Method | Path | Fires |
|---|---|---|
| POST | `/trigger/waitlist-promotion` | waitlist promotion graph |
| POST | `/trigger/checkin-reminders` | check-in reminder graph |
| POST | `/trigger/price-drop-alerts` | price-drop alert graph |
| POST | `/trigger/ops-report` | daily/weekly ops report graph |
| POST | `/trigger/fraud-scan` | fraud scoring batch graph |
| POST | `/trigger/pinecone-ingest` | policy doc ingestion graph |
| POST | `/trigger/refund-escalation` | stuck-refund escalation graph |

---

## Booking domain — schemas

```python
# apps/api/schemas/booking.py
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from uuid import UUID

class SeatHoldRequest(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(gt=0, le=9)
    passenger_email: str
    passenger_name: str

class SeatHoldResponse(BaseModel):
    hold_id: UUID
    seat_class_id: UUID
    quantity: int
    expires_at: datetime
    fare_amount: Decimal
    currency: str

class GroupHoldRequest(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(gt=1, le=9)
    passenger_email: str
    passenger_name: str
    # Group-hold policy per PRD §3: full-fail if fewer than `quantity` are available.
    # No partial-hold field here on purpose — partial semantics are decided server-side
    # and returned as an explicit reason if the hold cannot be fully satisfied.

class BookingConfirmRequest(BaseModel):
    hold_id: UUID
    payment_method_id: str        # Stripe PaymentMethod id, charged server-side

class BookingResponse(BaseModel):
    booking_id: UUID
    booking_reference: str
    status: str
    flight_id: UUID
    seat_class_id: UUID
    quantity: int
    total_amount: Decimal
    currency: str
    fare_rules_id: UUID
    created_at: datetime

class BookingCancelRequest(BaseModel):
    reason: str | None = None

class BookingCancelResponse(BaseModel):
    booking_id: UUID
    status: str
    refund_id: UUID | None
    credit_issued_amount: Decimal | None
```

## Waitlist domain — schemas

```python
class WaitlistJoinRequest(BaseModel):
    flight_id: UUID
    seat_class_id: UUID
    quantity: int = Field(gt=0, le=9)
    passenger_email: str
    passenger_name: str

class WaitlistJoinResponse(BaseModel):
    waitlist_entry_id: UUID
    priority_score: float
    status: str

class WaitlistPositionResponse(BaseModel):
    waitlist_entry_id: UUID
    status: str
    estimated_position: int | None
```

## Payments domain — schemas

```python
class PaymentWebhookEvent(BaseModel):
    # Raw provider payload is verified via signature header (Stripe-Signature) BEFORE
    # this model is even parsed — see 06_configuration_deployment.md for the verification step.
    id: str                 # provider event id -> payment_webhook_events.provider_event_id (idempotency key)
    type: str                # e.g. 'payment_intent.succeeded'
    data: dict

class PaymentStatusResponse(BaseModel):
    payment_id: UUID
    booking_id: UUID
    status: str
    amount: Decimal
    currency: str
```

## Admin domain — schemas

```python
class FlightCreateRequest(BaseModel):
    flight_number: str
    origin: str = Field(min_length=3, max_length=3)       # IATA
    destination: str = Field(min_length=3, max_length=3)
    origin_tz: str          # IANA tz name, validated against zoneinfo.available_timezones()
    destination_tz: str
    departure_local: datetime   # interpreted as local to origin_tz, converted to UTC on write
    arrival_local: datetime     # interpreted as local to destination_tz
    seat_allocation: dict[str, int]   # {'first': 20, 'business': 30, 'economy': 50}

    # Validated in flight_domain.create_flight(), not just here:
    #  - sum(seat_allocation.values()) == declared total capacity
    #  - all counts are positive integers
    #  - no duplicate flight_number on the same departure date

class SeatClassResizeRequest(BaseModel):
    class_name: str
    new_total_seats: int = Field(ge=0)
    # flight_domain.resize_seat_class() rejects if new_total_seats < current booked_seats;
    # the Postgres trigger trg_seat_classes_no_shrink is the backstop, not the primary check.

class AuditLogEntry(BaseModel):
    id: int
    actor_type: str
    actor_id: str | None
    action: str
    before: dict | None
    after: dict | None
    created_at: datetime
```

## Policy / RAG domain — schemas

```python
class PolicyQuestionRequest(BaseModel):
    booking_id: UUID | None = None   # if the question references a specific booking
    question: str = Field(min_length=1, max_length=2000)

class PolicyQuestionAccepted(BaseModel):
    run_id: str          # == LangGraph thread_id
    status: str          # 'drafting' immediately after submit

class PendingApprovalItem(BaseModel):
    run_id: str
    customer_question: str
    draft_answer: str
    consistency_flags: list[str]   # empty list = programmatic check found nothing suspicious
    booking_id: UUID | None
    created_at: datetime

class ApproveRunRequest(BaseModel):
    edited_answer: str | None = None   # ops agent can edit before sending; null = send draft as-is

class RejectRunRequest(BaseModel):
    reason: str
```

## Idempotency contract (applies to every POST/PATCH above)

```python
from fastapi import Header, HTTPException

async def require_idempotency_key(idempotency_key: str = Header(..., alias="Idempotency-Key")):
    if not idempotency_key or len(idempotency_key) > 255:
        raise HTTPException(400, "Idempotency-Key header required")
    return idempotency_key
```
Every mutating route depends on this, then passes the key into the corresponding `flight_domain` function, which checks `idempotency_keys` for `(key, endpoint, request_hash)` inside the same transaction as the mutation — see `02_system_architecture.md` §4 and the table in `03_database_schema.sql`.
