# Configuration & Deployment

## 1. Environment variables

```bash
# --- Postgres / Supabase ---
# Two DIFFERENT connection strings on purpose — see §2 below for why.
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres   # SESSION pooler, for apps/api's long-lived pool
LANGGRAPH_CHECKPOINT_DB_URI=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres  # SESSION pooler, for PostgresSaver
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_JWT_SECRET=...           # to validate customer JWTs locally without a round trip, or use JWKS

# --- Pinecone ---
PINECONE_API_KEY=...
PINECONE_INDEX_HOST=...           # from pc.create_index() / pc.describe_index()

# --- Embeddings + LLM ---
LLM_API_KEY=...
EMBEDDING_MODEL=text-embedding-3-small     # or your chosen provider's equivalent; must match Pinecone index `dimension`

# --- Gmail ---
GMAIL_SERVICE_ACCOUNT_JSON=/run/secrets/gmail-service-account.json
GMAIL_SENDER_ADDRESS=bookings@yourdomain.com
GMAIL_DELEGATED_SUBJECT=bookings@yourdomain.com   # domain-wide delegation subject, if using a Workspace service account

# --- Payments ---
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SIGNING_SECRET=...

# --- Worker ---
WORKER_URL=http://apps-worker:8001    # apps/api and the external scheduler both need this
```

## 2. Supabase connection pooling — the gotcha that will otherwise cost you a debugging afternoon

Supabase's pooler (Supavisor) has two modes on the same host, different ports:

| Mode | Port | Prepared statements | Best for |
|---|---|---|---|
| Session | 5432 | ✅ supported | Long-lived backend processes (FastAPI, LangGraph worker) — **use this** |
| Transaction | 6543 | ❌ not supported | Serverless functions with a huge number of short-lived connections |
| Direct | 5432 (no pooler host) | ✅ supported | IPv6-only, or paid dedicated pooler |

**Why this matters here specifically:** `psycopg` (used by `PostgresSaver`) and most ORMs use protocol-level prepared statements by default. Transaction mode reassigns the underlying server connection between transactions, so a prepared statement created in one transaction may not exist on the connection your next transaction gets — this surfaces as confusing "prepared statement does not exist" errors under load, not on first boot. Two ways to be safe:
1. **Preferred here:** point `apps/api` and `apps/worker` at the **session pooler** (port 5432). It's slightly more connection-hungry than transaction mode but both are always-on, moderate-connection-count processes (not a serverless-per-request fleet), so this is the right trade-off.
2. If you must use transaction mode (e.g. deploying `apps/api` itself as serverless functions), disable prepared statements explicitly: for `psycopg`, `connect(..., prepare_threshold=None)`; for SQLAlchemy's asyncpg dialect, `create_async_engine(url, connect_args={"statement_cache_size": 0})`.

Either way, **don't run both a session-mode pool and a transaction-mode pool against the same project without a reason** — Supabase's own guidance is to pick one per connection pattern, since running both increases pressure on the same underlying max-connection limit.

## 3. Gmail integration setup

1. Create a Google Workspace service account (or OAuth client if not on Workspace) in Google Cloud Console.
2. Enable the Gmail API for the project.
3. If using a service account with domain-wide delegation: grant it the `https://www.googleapis.com/auth/gmail.send` scope, delegated to `GMAIL_DELEGATED_SUBJECT` (the mailbox that should appear as the sender).
4. Both `apps/api` (transactional mail: booking confirmation, cancellation receipt) and `apps/worker` (scheduled mail: reminders, price-drop alerts, RAG-approved answers) use the same credentials and the same thin `gmail_client` wrapper — this is a good candidate for living in `flight_domain` too, so both processes share one send path and one place to add retry/rate-limit handling.
5. Every outbound send should be logged (recipient, template/type, related `booking_id`/`run_id`, timestamp) — this is what makes the audit trail in PRD §8 actually answerable ("did we tell this customer X") rather than just a promise.

## 4. Docker Compose skeleton

```yaml
services:
  api:
    build: ./apps/api
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - STRIPE_WEBHOOK_SIGNING_SECRET=${STRIPE_WEBHOOK_SIGNING_SECRET}
      - WORKER_URL=http://worker:8001
    ports: ["8000:8000"]

  worker:
    build: ./apps/worker
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - LANGGRAPH_CHECKPOINT_DB_URI=${LANGGRAPH_CHECKPOINT_DB_URI}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_INDEX_HOST=${PINECONE_INDEX_HOST}
      - LLM_API_KEY=${LLM_API_KEY}
      - GMAIL_SERVICE_ACCOUNT_JSON=/run/secrets/gmail-service-account.json
    secrets: [gmail-service-account]
    ports: ["8001:8001"]

  scheduler:
    build: ./apps/scheduler   # thin APScheduler process, see 05_langgraph_rag_pinecone.md §9 Option A
    environment:
      - WORKER_URL=http://worker:8001
    depends_on: [worker]

secrets:
  gmail-service-account:
    file: ./secrets/gmail-service-account.json
```
Note: no `postgres` service here — Supabase Postgres is managed/external; both `api` and `worker` connect out to it via `DATABASE_URL`.

## 5. Observability

- Structured JSON logging in `flight_domain` for every mutation: function name, actor, entity id, outcome, latency.
- `audit_log` (§9 of the architecture doc) is your business-level audit trail; application logs are your operational trail — keep them separate, don't try to make one serve both purposes.
- Optional: point `apps/worker` at LangSmith (`LANGSMITH_API_KEY` + `LANGSMITH_TRACING=true`) for per-node tracing on the graphs — genuinely useful for debugging the policy-RAG graph's retrieval/draft/consistency-check chain, since "why did it flag this" is otherwise hard to answer after the fact.

## 6. Testing strategy (brief — this is a spec, not a test plan doc)

- Unit-test every `flight_domain` function against a real Postgres test database (not mocks) — the whole point of this architecture is transactional/locking behavior, which mocks can't verify.
- Concurrency test: spin up N concurrent calls to `release_seat_and_promote()` for the same `seat_class_id` and assert exactly one promotion happens and `booked_seats` never goes negative or over capacity.
- Contract test for the policy-RAG graph: feed a booking with a known `fare_rules` row and a question that would tempt a generic wrong answer (e.g. ask about refunds on a non-refundable fare); assert `consistency_flags` catches an intentionally-wrong stubbed LLM response before assuming the real LLM will always get it right.
