# Flight Management System (FMS) Backend

Production-ready backend for a Flight Management System built with **FastAPI**, **LangGraph**, **Supabase Postgres**, **Pinecone**, **Gmail API**, and **Stripe**.

---

## 1. Architectural Overview

### Dual-Writer Solution
Both live customer/admin requests (`apps/api`) and background automated workflows (`apps/worker`) interact with inventory, bookings, and waitlists exclusively through **`packages/flight_domain`**.
There is no internal HTTP hop between API and Worker; both import `flight_domain` directly as a shared Python package. This eliminates the dual-writer divergence problem and guarantees that all database state changes go through atomic, validated transactions.

### Two-Tier Locking Strategy
To prevent concurrency bugs and deadlocks, two distinct row-level locking patterns are strictly enforced:
1. **Blocking `SELECT ... FOR UPDATE`**: Used on `seat_classes` counters (`booked_seats`, `held_seats`). Writers must serialize on counter increments/decrements. Skipping is prohibited because there is only one shared counter row per flight class.
2. **Non-blocking `SELECT ... FOR UPDATE SKIP LOCKED`**: Used on queue/outbox tables (`domain_events`, `waitlist_entries`). Multiple concurrent worker processes can claim independent items without contention.

### Defense-in-Depth Database Invariants
The database schema in `migrations/001_initial_schema.sql` enforces triggers and CHECK constraints that backstop application-layer validation:
- `trg_seat_classes_capacity`: Guarantees `booked_seats + held_seats <= total_seats`.
- `trg_seat_classes_no_shrink`: Prevents shrinking `total_seats` below already-booked seats.
- Outbox table `domain_events` captures all domain state mutations within the same transaction.

---

## 2. Repository Structure

```
flightbooking/
├── packages/
│   └── flight_domain/             # Shared core business logic & SQLAlchemy models
│       ├── flight_domain/
│       │   ├── models/            # SQLAlchemy models matching 03_database_schema.sql
│       │   ├── domain/            # Transactional mutation functions (seats, bookings, admin, waitlist)
│       │   └── clients/           # Gmail and Pinecone clients (with local mock fallbacks)
│       └── pyproject.toml
├── apps/
│   ├── api/                       # Public & Admin FastAPI application (Port 8000)
│   │   ├── routers/               # Endpoints: admin, search, bookings, waitlist, payments, policy, auth
│   │   ├── schemas/               # Pydantic request & response models
│   │   ├── dependencies.py        # Idempotency header validation & Supabase Auth JWT parsing
│   │   └── Dockerfile
│   ├── worker/                    # LangGraph workflow engine & trigger endpoints (Port 8001)
│   │   ├── graphs/                # 6 LangGraph graphs (Policy RAG, waitlist, checkin, fraud, ingest, refunds)
│   │   ├── services/              # Grounding diff checker, fraud detector, ops reporter
│   │   ├── checkpointer.py        # PostgresSaver checkpointer (Session pooler configuration)
│   │   └── Dockerfile
│   └── scheduler/                 # Standalone APScheduler process triggering worker endpoints
│       ├── main.py                # Recurring crons and intervals for triggers
│       └── Dockerfile
├── migrations/
│   ├── 001_initial_schema.sql     # Complete PostgreSQL DDL with triggers and indexes
│   └── run_migrations.py          # Python database migration runner
├── tests/
│   ├── conftest.py                # Database fixtures & TestClient configuration
│   ├── test_concurrency.py        # Two concurrent callers race test on release_seat_and_promote
│   ├── test_consistency_check.py  # Fact-grounding test catching hallucinated LLM claims
│   ├── test_flight_domain.py      # Unit tests for domain functions, capacity, and idempotency
│   └── test_api_endpoints.py      # FastAPI HTTP endpoint tests
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 3. Configuration & Supabase Pooling

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### Supabase Pooler Distinction
- **Session Pooler (Port 5432)**: **Use this** for `DATABASE_URL` and `LANGGRAPH_CHECKPOINT_DB_URI`. Both FastAPI and LangGraph `PostgresSaver` maintain prepared statements over persistent connections.
- **Transaction Pooler (Port 6543)**: Does not support server-level prepared statements. If transaction mode is mandatory, set `prepare_threshold=None` in `psycopg` connection flags.

---

## 4. Running Migrations

Apply the database schema against your PostgreSQL database:

```bash
# Set your target database connection string
export DATABASE_URL="postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres"

# Execute migration runner
python migrations/run_migrations.py
```

Or execute `migrations/001_initial_schema.sql` directly in Supabase SQL Editor.

---

## 5. Running Locally

### Option A: Docker Compose (All 3 Services)
```bash
docker compose up --build
```
Services started:
- `api`: `http://localhost:8000` (OpenAPI Swagger docs at `/docs`)
- `worker`: `http://localhost:8001`
- `scheduler`: Runs background scheduled triggers targeting `worker:8001`

### Option B: Local Python Development
1. Install packages:
   ```bash
   pip install -e packages/flight_domain
   pip install -r apps/api/requirements.txt
   pip install -r apps/worker/requirements.txt
   pip install -r apps/scheduler/requirements.txt
   ```

2. Start FastAPI API:
   ```bash
   uvicorn apps.api.main:app --port 8000 --reload
   ```

3. Start LangGraph Worker:
   ```bash
   uvicorn apps.worker.main:app --port 8001 --reload
   ```

4. Start Scheduler:
   ```bash
   python apps/scheduler/main.py
   ```

---

## 6. Running Tests

Run the full automated test suite:
```bash
pytest -v tests/
```

### Key Test Suites:
- `test_concurrency_race_on_freed_seat`: Simulates two concurrent threads calling `release_seat_and_promote` on the same seat class simultaneously. Verifies that exactly one promotion occurs, the waitlist entry is claimed, and capacity limits are never violated.
- `test_consistency_check_catches_wrong_refundability`: Injects an intentionally wrong stubbed LLM response (claiming a non-refundable economy ticket is refundable) against a known database fare rule, verifying that `consistency_check` flags the discrepancy before human review.
