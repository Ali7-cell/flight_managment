-- Flight Management System — Postgres schema
-- Target: Supabase Postgres. Run via Supabase SQL editor or a migration tool (alembic/sqitch).
--
-- OWNERSHIP CONVENTION (enforced by code review, not by grants — see 02_system_architecture.md):
--   Every table below is annotated with which layer is allowed to write to it.
--   "flight_domain only" means: FastAPI and LangGraph both mutate this table exclusively through
--   packages/flight_domain functions. No raw UPDATE/INSERT against these tables anywhere else in
--   either codebase.

create extension if not exists "pgcrypto";      -- gen_random_uuid()
create extension if not exists "pg_net";        -- optional: only if you wire LISTEN/NOTIFY -> webhook

-- =========================================================================
-- AUTH / IDENTITY
-- =========================================================================

-- Customer identity is Supabase Auth (auth.users); this table extends it with app-specific fields.
-- Owner: flight_domain only (created on first booking or on signup webhook).
create table passengers (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid references auth.users(id) on delete set null,  -- null = guest checkout
    email           text not null,
    full_name       text not null,
    phone           text,
    loyalty_tier    text not null default 'none' check (loyalty_tier in ('none','silver','gold','platinum')),
    created_at      timestamptz not null default now()
);
create index idx_passengers_email on passengers (email);
create index idx_passengers_user_id on passengers (user_id);

-- Admin/ops identity is separate from customer identity on purpose (see PRD §12).
-- Owner: flight_domain only, super_admin-gated.
create table admin_users (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references auth.users(id) on delete cascade,
    role            text not null check (role in ('super_admin','ops_agent')),
    created_at      timestamptz not null default now(),
    unique (user_id)
);

-- =========================================================================
-- FLIGHTS / INVENTORY  (FastAPI is the only writer, per PRD §1)
-- =========================================================================

create table flights (
    id                  uuid primary key default gen_random_uuid(),
    flight_number       text not null,
    origin              text not null,             -- IATA code, e.g. 'LHR'
    destination         text not null,              -- IATA code, e.g. 'DXB'
    origin_tz           text not null,              -- IANA tz, e.g. 'Europe/London'
    destination_tz      text not null,              -- IANA tz, e.g. 'Asia/Dubai'
    departure_at        timestamptz not null,       -- always UTC in storage (see PRD §13)
    arrival_at          timestamptz not null,
    status              text not null default 'scheduled'
                            check (status in ('scheduled','cancelled','departed','completed')),
    total_seats         integer not null check (total_seats > 0),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    check (arrival_at > departure_at)
);
create unique index uq_flight_number_per_day
    on flights (flight_number, (departure_at::date));
create index idx_flights_route_date on flights (origin, destination, departure_at);

create table fare_rules (
    id                      uuid primary key default gen_random_uuid(),
    fare_class              text not null,           -- 'basic_economy','economy','flexible_economy','business','first'
    refundable              boolean not null default false,
    change_allowed          boolean not null default false,
    change_fee_amount       numeric(10,2),
    seat_choice_allowed     boolean not null default false,
    cancellation_window_hrs integer,                 -- null = not applicable
    policy_text             text not null,            -- human-readable summary, also the source for Pinecone chunking
    created_at              timestamptz not null default now()
);

create table seat_classes (
    id              uuid primary key default gen_random_uuid(),
    flight_id       uuid not null references flights(id) on delete cascade,
    class_name      text not null check (class_name in ('economy','business','first')),
    total_seats     integer not null check (total_seats >= 0),
    booked_seats    integer not null default 0 check (booked_seats >= 0),
    held_seats      integer not null default 0 check (held_seats >= 0),
    fare_rules_id   uuid not null references fare_rules(id),
    fare_base_amount numeric(10,2) not null check (fare_base_amount >= 0),
    currency        text not null default 'USD',
    updated_at      timestamptz not null default now(),
    unique (flight_id, class_name),
    check (booked_seats + held_seats <= total_seats)   -- backstop; primary check is in flight_domain
);
create index idx_seat_classes_flight on seat_classes (flight_id);

-- =========================================================================
-- BOOKING / HOLDS  (flight_domain only)
-- =========================================================================

create table seat_holds (
    id                  uuid primary key default gen_random_uuid(),
    seat_class_id       uuid not null references seat_classes(id),
    passenger_id        uuid references passengers(id),
    quantity            integer not null check (quantity > 0),
    status              text not null default 'active'
                            check (status in ('active','expired','converted','released')),
    idempotency_key     text,
    expires_at          timestamptz not null,
    created_at          timestamptz not null default now()
);
create index idx_seat_holds_expiry on seat_holds (expires_at) where status = 'active';

create table bookings (
    id                  uuid primary key default gen_random_uuid(),
    booking_reference   text not null unique,        -- customer-facing PNR-style code
    passenger_id        uuid not null references passengers(id),
    flight_id           uuid not null references flights(id),
    seat_class_id       uuid not null references seat_classes(id),
    quantity            integer not null check (quantity > 0),
    fare_rules_id       uuid not null references fare_rules(id),
    total_amount        numeric(10,2) not null check (total_amount >= 0),
    currency            text not null default 'USD',
    status              text not null default 'pending_payment'
                            check (status in ('pending_payment','confirmed','cancelled','refunded','completed')),
    payment_id          uuid,                        -- fk added after payments table below
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);
create index idx_bookings_passenger on bookings (passenger_id);
create index idx_bookings_flight on bookings (flight_id);
create index idx_bookings_status on bookings (status);

create table waitlist_entries (
    id              uuid primary key default gen_random_uuid(),
    flight_id       uuid not null references flights(id),
    seat_class_id   uuid not null references seat_classes(id),
    passenger_id    uuid not null references passengers(id),
    quantity        integer not null check (quantity > 0),
    priority_score  numeric not null,                -- computed from loyalty tier + booking time, see flight_domain
    status          text not null default 'waiting'
                        check (status in ('waiting','promotion_offered','promoted','expired','cancelled')),
    offer_expires_at timestamptz,
    created_at      timestamptz not null default now()
);
create index idx_waitlist_pending
    on waitlist_entries (seat_class_id, priority_score)
    where status = 'waiting';

create table refunds (
    id              uuid primary key default gen_random_uuid(),
    booking_id      uuid not null references bookings(id),
    amount          numeric(10,2) not null check (amount >= 0),
    reason          text,
    status          text not null default 'pending'
                        check (status in ('pending','processing','completed','failed')),
    created_at      timestamptz not null default now(),
    resolved_at     timestamptz
);
create index idx_refunds_pending_age on refunds (created_at) where status = 'pending';

-- =========================================================================
-- PAYMENTS  (PRD §11 — added domain)
-- =========================================================================

create table payments (
    id                      uuid primary key default gen_random_uuid(),
    booking_id              uuid not null references bookings(id),
    provider                text not null default 'stripe',
    provider_payment_id     text not null,
    status                  text not null default 'requires_payment'
                                check (status in ('requires_payment','processing','succeeded','failed','refunded')),
    amount                  numeric(10,2) not null,
    currency                text not null default 'USD',
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    unique (provider, provider_payment_id)
);
alter table bookings
    add constraint fk_bookings_payment foreign key (payment_id) references payments(id);

-- Idempotency for provider webhooks — keyed on the PROVIDER's event id, not a client key.
create table payment_webhook_events (
    provider_event_id   text primary key,
    provider            text not null default 'stripe',
    payload_json        jsonb not null,
    processed_at        timestamptz not null default now()
);

-- =========================================================================
-- SHARED CONTRACT PLUMBING
-- =========================================================================

-- Idempotency for FastAPI write endpoints (client-supplied Idempotency-Key header).
create table idempotency_keys (
    key                 text primary key,
    endpoint            text not null,
    request_hash        text not null,
    response_snapshot_json jsonb,
    created_at          timestamptz not null default now()
);

-- Outbox: every flight_domain mutation worth reacting to writes one row here,
-- in the SAME transaction as the state change. LangGraph schedulers consume this,
-- not raw booking/seat state. See 02_system_architecture.md §5.
create table domain_events (
    id              bigserial primary key,
    event_type      text not null,      -- 'seat_released','booking_confirmed','booking_cancelled',
                                         -- 'refund_requested','flight_cancelled','schedule_changed'
    payload_json    jsonb not null,
    created_at      timestamptz not null default now(),
    processed       boolean not null default false,
    processed_at    timestamptz
);
create index idx_domain_events_unprocessed
    on domain_events (created_at) where processed = false;

-- Audit log: every flight_domain call writes here. actor_type distinguishes
-- system:fastapi / system:langgraph:<graph_name> / human:<admin_user_id>.
create table audit_log (
    id              bigserial primary key,
    actor_type      text not null,
    actor_id        text,
    action          text not null,
    entity_type     text not null,
    entity_id       uuid,
    before_json     jsonb,
    after_json      jsonb,
    created_at      timestamptz not null default now()
);
create index idx_audit_entity on audit_log (entity_type, entity_id);

-- =========================================================================
-- FRAUD  (LangGraph batch jobs only)
-- =========================================================================

create table fraud_scores (
    id              uuid primary key default gen_random_uuid(),
    booking_id      uuid not null references bookings(id),
    score           numeric not null,       -- 0..1
    signals_json    jsonb not null,
    scored_at       timestamptz not null default now()
);
create index idx_fraud_scores_booking on fraud_scores (booking_id);

-- =========================================================================
-- POLICY / RAG  (LangGraph only for writes; FastAPI may read fare_rules directly)
-- =========================================================================

create table policy_docs (
    id              uuid primary key default gen_random_uuid(),
    title           text not null,
    source_url      text,
    content_hash    text not null,          -- detect "did this doc actually change" before re-embedding
    fare_type_scope text,                   -- 'all' or a specific fare_class this doc governs
    updated_at      timestamptz not null default now()
);

create table policy_doc_chunks (
    id                  uuid primary key default gen_random_uuid(),
    policy_doc_id       uuid not null references policy_docs(id) on delete cascade,
    chunk_index         integer not null,
    content             text not null,
    pinecone_vector_id  text not null unique,
    updated_at          timestamptz not null default now()
);

-- One row per customer policy question, tracks the LangGraph thread end to end.
create table policy_question_runs (
    id                  uuid primary key default gen_random_uuid(),
    thread_id           text not null unique,    -- LangGraph checkpointer thread_id
    booking_id          uuid references bookings(id),
    customer_question   text not null,
    draft_answer        text,
    consistency_flags_json jsonb,               -- output of the programmatic fact-check node
    status              text not null default 'drafting'
                            check (status in ('drafting','pending_approval','approved','rejected','sent')),
    approved_by         uuid references admin_users(id),
    approved_at         timestamptz,
    created_at          timestamptz not null default now()
);

-- =========================================================================
-- TRIGGERS — backstop invariants (defense in depth behind flight_domain checks)
-- =========================================================================

-- Cannot end up over capacity. Primary enforcement is in flight_domain.hold_seats() /
-- confirm_booking(); this trigger exists so a bug or an out-of-band write still can't
-- push booked+held over total.
create or replace function trg_fn_seat_classes_capacity() returns trigger as $$
begin
    if new.booked_seats + new.held_seats > new.total_seats then
        raise exception 'seat_classes capacity exceeded for %: booked % + held % > total %',
            new.id, new.booked_seats, new.held_seats, new.total_seats;
    end if;
    return new;
end;
$$ language plpgsql;

create trigger trg_seat_classes_capacity
    before insert or update on seat_classes
    for each row execute function trg_fn_seat_classes_capacity();

-- Cannot shrink a class below its already-booked count (PRD §1).
create or replace function trg_fn_seat_classes_no_shrink() returns trigger as $$
begin
    if new.total_seats < old.booked_seats then
        raise exception 'cannot shrink seat_classes % total to % below booked_seats %',
            new.id, new.total_seats, old.booked_seats;
    end if;
    return new;
end;
$$ language plpgsql;

create trigger trg_seat_classes_no_shrink
    before update of total_seats on seat_classes
    for each row execute function trg_fn_seat_classes_no_shrink();

-- Auto-touch updated_at on the tables that carry it.
create or replace function trg_fn_touch_updated_at() returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_flights_touch before update on flights
    for each row execute function trg_fn_touch_updated_at();
create trigger trg_seat_classes_touch before update on seat_classes
    for each row execute function trg_fn_touch_updated_at();
create trigger trg_bookings_touch before update on bookings
    for each row execute function trg_fn_touch_updated_at();
create trigger trg_payments_touch before update on payments
    for each row execute function trg_fn_touch_updated_at();

-- Notify path for LISTEN/NOTIFY consumers (optional — polling domain_events works fine too).
create or replace function trg_fn_notify_domain_event() returns trigger as $$
begin
    perform pg_notify('domain_events', new.id::text);
    return new;
end;
$$ language plpgsql;

create trigger trg_domain_events_notify
    after insert on domain_events
    for each row execute function trg_fn_notify_domain_event();
