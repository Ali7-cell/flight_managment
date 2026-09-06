# Flight Management System — PRD v2 (LangGraph edition)

Stack: **FastAPI** (live/transactional writer) + **LangGraph** (scheduled/background writer, replaces n8n) + **Supabase Postgres** (single ledger of truth) + **Pinecone** (policy vector store) + **RAG** (policy Q&A) + **Gmail API** (all outbound mail).

Ownership tags: **[FastAPI]** live, request-triggered · **[LangGraph]** scheduled/background, no live request waiting on it · **[Both]** shared design decision or coordination point that both systems must honor.

> **What changed from the original 56-item n8n version:** every `[n8n]` tag becomes `[LangGraph]` — same ownership split, same reasoning (live/transactional → FastAPI, time-based/no-request-in-loop → LangGraph). Nothing was reassigned between FastAPI and the background system; only the background system's identity changed. Beyond the swap, three things are added at the end (**Payments**, **Customer Auth**, **Timezone** as a cross-cutting rule) because a backend billed as "full production ready" can't ship without them — the original 56 didn't cover money coming in or who a customer is. The dual-writer, conflict-resolution, and RAG-grounding items are expanded beyond one bullet each; the concrete mechanism for each is in `02_system_architecture.md`, not just named here.

---

## 1. Admin & Flight Management — `[FastAPI]` only

- Create flight: origin, destination, departure/arrival datetime (stored UTC — see §12 Timezone), flight number, IANA origin/destination tz.
- Example: UK → Dubai, 100 seats — 20 First / 30 Business / 50 Economy.
- Seat class totals must sum exactly to declared aircraft capacity.
- Reject negative/zero/non-integer seat counts.
- Edit flight schedule (time/route change) with cascading effect on existing bookings.
- Cancel a flight entirely → triggers downstream rebook/refund flow.
- Seat map/layout per flight (physical seat → class mapping).
- Adjust seat class allocation after bookings exist — **cannot shrink a class below its already-booked count** (enforced in `flight_domain.resize_seat_class()`, backstopped by a Postgres trigger — see §2 of architecture doc).
- Duplicate flight-number detection for same day/route.
- Admin role tiers: `super_admin` (schedule/cancel/refund-policy changes) vs `ops_agent` (day-to-day edits, no cancellation/refund-policy authority).
- Audit log of every admin change (who, what, when, before/after).

## 2. Search & Fare Rules — `[FastAPI]` only

- Search endpoint: available seats per class for a route/date.
- Fare class rules: basic economy (no changes, no seat choice) vs flexible fare.
- Price-hold duration between search results and booking confirmation.
- Multi-leg itinerary where one leg's fare disappears before the other is booked.
- Currency/locale handling for displayed fares.

## 3. Seat Holds & Booking — `[FastAPI]` only, the atomic core

- Temporary seat hold during checkout, expiry if payment isn't completed.
- **Atomic seat-class decrement** — one row-locked transaction inside `flight_domain.hold_seats()`, never a separate read-then-write across two calls.
- Idempotency-Key handling for duplicate/retried booking requests (dedicated table, see schema).
- Explicit overbooking policy per class: allowed-with-buffer vs hard never-oversell.
- Group booking of N seats where only some are available: partial-hold / partial-fail / full-fail — pick one and encode it (spec picks **full-fail with an immediate waitlist offer** for the shortfall; document if you choose differently).
- Class-specific booking cutoffs (First/Business allow later cutoff than Economy).

## 4. Changes, Cancellations & Refunds — `[FastAPI]` decides, `[LangGraph]` escalates

- `[FastAPI]` Cancellation policy branching by fare type (refundable / credit-only / non-refundable).
- `[FastAPI]` Partial cancellation on multi-passenger booking — proportional refund + re-pricing.
- `[FastAPI]` Airline-initiated schedule change — automatic rebooking rule + fare-policy override.
- `[FastAPI]` Flight cancellation — refund vs rebook vs travel credit, with credit expiration.
- `[LangGraph]` Escalation notification if a refund stays unresolved after N days (scheduled graph, polls `refunds` where `status='pending' AND created_at < now() - N days`).

## 5. Waitlist & Standby — `[FastAPI]` join, `[LangGraph]` promote

- `[FastAPI]` Add passenger to waitlist when class/flight is full.
- `[FastAPI]` Waitlist priority rule (loyalty tier vs booking time vs fare class).
- `[LangGraph]` Scheduled job detects freed-up seats and promotes next waitlisted passenger.
- `[LangGraph]` Notification window before an auto-promoted seat reassigns to next person if unclaimed.
- `[Both]` **Row-locking so a gate-agent action (FastAPI) and a LangGraph promotion run can't assign the same freed seat twice** — this is not a bullet to "pick," it's the item with the concrete design in `02_system_architecture.md` §3. Both paths call the *same* `flight_domain.release_seat_and_promote()` function; the seat-class row lock serializes them. This is the single most important line item in the whole document.

## 6. Scheduled Automations — `[LangGraph]` only

- Check-in reminder email, timezone-correct for origin/destination (compute local time from `flights.origin_tz`/`destination_tz`, never assume server tz).
- Price-drop alert with de-duplication (don't fire on every micro-fluctuation — debounce on a `%` threshold + a per-passenger cooldown).
- Daily/weekly ops reporting (load factor, revenue per flight) from Postgres.
- Detection + suppression of reminder workflows for already-cancelled flights (check `flights.status` before sending, inside the same graph run, not as a separate cleanup pass).

## 7. Fraud, Policy & RAG Support — `[LangGraph]` only

- **RAG-drafted answer must reflect the booking's actual fare rule, not a generic match.** The mechanism (structured DB lookup + Pinecone retrieval + a programmatic consistency check *before* the human ever sees the draft) is in `05_langgraph_rag_pinecone.md`. The human-approval gate alone does not satisfy this requirement — it checks tone/completeness, not fact-grounding; the consistency-check node is what checks facts.
- Human approval gate (LangGraph `interrupt()`) before any RAG-drafted answer sends via Gmail.
- Scheduled bot/mass-booking fraud-scoring job scanning recent bookings.
- **Named trade-off, not hidden:** every fraud check here is post-hoc batch scoring. A fraudulent booking can complete, hold a seat, and trigger a Gmail confirmation before any score runs. Accepted for this scope; if that's wrong for your grading rubric, the fix is a lightweight synchronous rule-check (velocity/blacklist, not full ML scoring) inside `flight_domain.confirm_booking()` itself, with the heavier LangGraph batch job catching what the fast synchronous check can't.
- Scheduled ingestion pipeline embedding updated policy docs into Pinecone.
- Batch review job scanning historical bookings for fraud patterns missed in real time.

## 8. Approval & Autonomy Boundaries — `[Both]`

- Explicit auto-approved list: reminders, standard in-policy refunds, waitlist promotions within stated priority rule.
- Explicit human-sign-off-required list: schedule-change compensation, denied-boarding compensation, any RAG-drafted policy answer before send.
- Audit trail sufficient to justify an automated decision to a regulator or complaint review (every `flight_domain` call writes to `audit_log` with actor type `system:fastapi` / `system:langgraph:<graph_name>` / `human:<user_id>`).

## 9. Shared Database Architecture (FastAPI + LangGraph dual-writer) — `[Both]`

This is the domain the original doc under-weighted. Full design in `02_system_architecture.md`; summary of what each bullet now *means*, concretely:

- **Table-ownership rules**: not "which system may touch which table" as a policy document — enforced by *only exposing mutation through `flight_domain` functions*, so ownership is a code-review fact, not a promise.
- **Postgres-level invariants** (CHECK constraints, triggers): kept, but reclassified as **backstop**, not the primary contract. A CHECK constraint cannot see an aggregate across rows; the capacity/no-shrink rules are enforced in triggers as a second line of defense behind the application-layer check in `flight_domain`.
- **Change-detection mechanism**: `domain_events` outbox table, written in the same transaction as the state change. LangGraph schedulers poll or `LISTEN/NOTIFY` on this table — not on raw booking/seat state — so "did something change" is a well-defined question with one answer, not inferred from timestamps.
- **Row-locking strategy**: two distinct patterns, not one — plain `SELECT ... FOR UPDATE` (blocking) on a `seat_classes` row for count mutation (you must not skip it, you must wait for it); `SELECT ... FOR UPDATE SKIP LOCKED` for queue-style tables (`domain_events`, `waitlist_entries`) where multiple workers compete and skipping to a different row is correct. Conflating these two was the original ambiguity.
- **Reconciliation/audit job**: `[LangGraph]` scheduled graph comparing `seat_classes.booked_seats` against `count(bookings where status='confirmed')` per class; alerts on drift instead of silently trusting the counter.
- **Explicit conflict-resolution rule** for concurrent writes (FastAPI cancellation vs LangGraph waitlist promotion on the same seat): resolved by construction — both call `flight_domain.release_seat_and_promote()`, one waits on the other's row lock, no separate "rule" needs to be written down because there's only one code path capable of causing the conflict in the first place.

## 10. Core Infrastructure

- `[FastAPI]` Typed request/response schemas + validation for every booking-affecting endpoint.
- `[FastAPI]` Idempotency-Key header contract for all write endpoints.
- `[Both]` Supabase Postgres as the single ledger of truth.
- `[LangGraph]` Pinecone index maintenance job for policy docs + fraud-pattern embeddings.
- `[LangGraph]` Gmail integration for all customer-facing *scheduled* notifications.
- `[FastAPI]` Gmail send for transactional, request-triggered emails (booking confirmation, cancellation receipt).

---

## 11. Payments — *added, not in the original 56*

No capture confirmation, no provider webhook, no webhook idempotency existed in the original scope. Refunds were covered; money coming in wasn't.

- `[FastAPI]` `POST /payments/webhook` — provider (Stripe assumed; swap freely) webhook receiver. Verifies signature, checks `payment_webhook_events` for the provider's event id before processing (idempotent by construction — a redelivered webhook is a no-op, not a double-charge-side-effect).
- `[FastAPI]` Booking confirmation is gated on a `payment_intent.succeeded` event, not on the client reporting success — never trust the browser/app to say a payment worked.
- `[FastAPI]` Payment status state machine: `requires_payment → processing → succeeded | failed | refunded`.
- `[LangGraph]` Scheduled reconciliation: compare Stripe's payment records against local `payments` table, flag drift (double-entry-style check, same spirit as the seat reconciliation job).

## 12. Customer-Facing Auth — *added, not in the original 56*

Original scope addressed admin role tiers only; no model existed for who a *customer* is.

- Use **Supabase Auth** (already in the stack) rather than hand-rolling password storage — FastAPI validates the Supabase-issued JWT (JWKS) on every customer-facing endpoint and reads `sub` as the passenger's user id.
- `passengers.user_id` is nullable (guest checkout allowed) but bookings *can* be claimed onto an account after the fact by email match.
- Admin auth is separate from customer auth: `admin_users` table with a `role` column (`super_admin` / `ops_agent`), checked via a FastAPI dependency, never inferred from the customer JWT.

## 13. Timezone Handling — *cross-cutting rule, added*

The original doc only mentioned timezone-correctness on the check-in reminder item; flight datetime storage itself was ambiguous ("departing 05:00" — local? UTC? browser?).

- **Rule:** every timestamp in Postgres is `timestamptz`, stored in UTC. Every flight additionally stores `origin_tz` and `destination_tz` as IANA strings (`"Europe/London"`, `"Asia/Dubai"`).
- Display/local-time conversion happens only at the presentation layer (API response formatting, email templates) — never in storage, never in business-logic comparisons.
- Admin-entered "05:00 departure" is interpreted as *local to the origin airport* at entry time, converted to UTC before insert; the admin UI must show which tz it's interpreting to avoid a silent off-by-several-hours bug.
