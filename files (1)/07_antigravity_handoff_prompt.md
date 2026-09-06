# Handoff prompt for Google Antigravity (Gemini 3)

Attach these files to the task alongside this prompt (Antigravity's Editor/Manager view lets you attach multiple files to one agent task — attach all of them, not just this one):

- `01_PRD_requirements.md`
- `02_system_architecture.md`
- `03_database_schema.sql`
- `04_api_endpoints_schemas.md`
- `05_langgraph_rag_pinecone.md`
- `06_configuration_deployment.md`

Then paste the prompt below as the task description.

---

```
Build a production-ready backend for a Flight Management System from the attached spec files.
Stack is fixed: FastAPI, LangGraph, Supabase Postgres, Pinecone, Gmail API, Stripe.
Do not redesign the architecture — implement it as specified. In particular:

1. Repo layout is fixed: packages/flight_domain (shared business logic + SQLAlchemy models,
   imported directly by both apps below — no internal HTTP hop between them), apps/api
   (FastAPI, public-facing), apps/worker (LangGraph graphs + internal /trigger/* endpoints),
   apps/scheduler (thin process that calls apps/worker's trigger endpoints on a schedule).
   This split is the fix for the dual-writer problem described in 02_system_architecture.md
   §1 — do not let apps/worker write to Postgres by any path other than importing
   packages/flight_domain.

2. Every function in packages/flight_domain that mutates seat/booking state must do its
   SELECT ... FOR UPDATE and its write inside one transaction, inside one function call —
   never split across two calls or two LangGraph nodes. 02_system_architecture.md §2 explains
   which tables need blocking FOR UPDATE vs. FOR UPDATE SKIP LOCKED; implement both correctly,
   don't default to one everywhere.

3. Apply 03_database_schema.sql as-is (or via a migration tool of your choice, e.g. alembic) —
   it already encodes the CHECK constraints and triggers that back up the application-layer
   validation. Don't remove the triggers because "the application already checks this" — they're
   deliberately redundant (defense in depth), see the comments in the SQL file.

4. Implement every endpoint in 04_api_endpoints_schemas.md with the exact request/response
   models given. Every mutating endpoint requires and validates the Idempotency-Key header
   against the idempotency_keys table inside the same transaction as the mutation it guards.

5. Implement the LangGraph graphs in 05_langgraph_rag_pinecone.md as specified, including the
   consistency_check node in the policy-RAG graph — this is not optional polish, it's the fix
   for a factual-grounding gap the spec identifies explicitly. Use langgraph's interrupt()/
   Command(resume=...) pattern for the human-approval step exactly as shown, with a Postgres
   checkpointer (PostgresSaver), not the in-memory saver, since approval can take longer than
   one process lifetime.

6. Apply the configuration in 06_configuration_deployment.md verbatim, especially the Supabase
   session-pooler vs. transaction-pooler distinction — this determines which port and which
   psycopg/SQLAlchemy connection flags to use, and getting it wrong produces intermittent
   "prepared statement does not exist" errors under load rather than a clean failure at boot.

7. Generate: the full repo scaffold, all Pydantic models, all flight_domain functions (with
   real transactional bodies, not stubs), the six LangGraph graphs, a Dockerfile per app,
   the docker-compose.yml from 06_configuration_deployment.md, and a README documenting how
   to run migrations and start all four processes locally.

8. After generating, write tests for: the concurrency behavior described in
   02_system_architecture.md §3 (two concurrent callers racing on the same seat_class_id,
   asserting exactly one promotion and no capacity violation), and the consistency_check
   node catching a deliberately-wrong stubbed LLM answer against a known fare_rules row.

Ask me before making any architectural change that isn't already specified in these files —
the design decisions here (shared domain package, outbox table, two-tier locking, structured-
output grounding check) were made deliberately and aren't meant to be reinterpreted.
```

---

**Why this prompt is shaped this way:** Antigravity/Gemini 3 works best when given a concrete plan to execute rather than an open design problem — its own docs describe it generating a task list and artifacts *from* a spec, then self-verifying against it. The six attached files are that spec. The explicit "ask before changing the architecture" line matters because the dual-writer fix, the two lock types, and the RAG grounding check are exactly the kind of thing a capable coding agent might "simplify" if it doesn't understand why they're there — each of those decisions closes a specific gap that was identified by working through the original design, and quietly reverting any one of them reopens it.
