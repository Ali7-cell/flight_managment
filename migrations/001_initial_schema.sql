-- Flight Management System — Postgres schema
-- Target: Supabase Postgres. Run via Supabase SQL editor or a migration tool.
-- Architecture: FastAPI + LangGraph + Supabase Postgres + Pinecone + RAG + Gmail

create extension if not exists "pgcrypto";      -- gen_random_uuid()
create extension if not exists "pg_net";        -- optional: only if you wire LISTEN/NOTIFY -> webhook

-- =========================================================================
-- AUTH / IDENTITY
-- =========================================================================

create table if not exists passengers (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid,  -- references auth.users(id) in Supabase, null = guest checkout
    email           text not null,
    full_name       text not null,
    phone           text,
    password_hash   text,
    loyalty_tier    text not null default 'none' check (loyalty_tier in ('none','silver','gold','platinum')),
    created_at      timestamptz not null default now()
);
create index if not exists idx_passengers_email on passengers (email);
create index if not exists idx_passengers_user_id on passengers (user_id);

create table if not exists admin_users (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null,  -- references auth.users(id)
    email           text,
    full_name       text,
    password_hash   text,
    role            text not null check (role in ('super_admin','ops_agent')),
    created_at      timestamptz not null default now(),
    unique (user_id)
);

-- =========================================================================
-- FLIGHTS / INVENTORY  (FastAPI is the only writer, per PRD §1)
-- =========================================================================

create table if not exists flights (
    id                  uuid primary key default gen_random_uuid(),
    flight_number       text not null,
    origin              text not null,             -- IATA code, e.g. 'LHR'
    destination         text not null,             -- IATA code, e.g. 'DXB'
    origin_tz           text not null,             -- IANA tz, e.g. 'Europe/London'
    destination_tz      text not null,             -- IANA tz, e.g. 'Asia/Dubai'
    departure_at        timestamptz not null,      -- always UTC in storage (see PRD §13)
    arrival_at          timestamptz not null,
    status              text not null default 'scheduled'
                            check (status in ('scheduled','cancelled','departed','completed')),
    total_seats         integer not null check (total_seats > 0),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    check (arrival_at > departure_at)
);
create unique index if not exists uq_flight_number_per_day
    on flights (flight_number, ((departure_at at time zone 'UTC')::date));
create index if not exists idx_flights_route_date on flights (origin, destination, departure_at);

create table if not exists fare_rules (
    id                      uuid primary key default gen_random_uuid(),
    fare_class              text not null,           -- 'basic_economy','economy','flexible_economy','business','first'
    refundable              boolean not null default false,
    change_allowed          boolean not null default false,
    change_fee_amount       numeric(10,2),
    seat_choice_allowed     boolean not null default false,
    cancellation_window_hrs integer,                 -- null = not applicable
    policy_text             text not null,           -- human-readable summary, also source for Pinecone
    created_at              timestamptz not null default now()
);

create table if not exists seat_classes (
    id                      uuid primary key default gen_random_uuid(),
    flight_id               uuid not null references flights(id) on delete cascade,
    class_name              text not null check (class_name in ('basic_economy','economy','flexible_economy','business','first')),
    total_seats             integer not null check (total_seats >= 0),
    booked_seats            integer not null default 0 check (booked_seats >= 0),
    held_seats              integer not null default 0 check (held_seats >= 0),
    overbooking_buffer_pct  numeric(5,2) not null default 0.0 check (overbooking_buffer_pct >= 0.0),
    booking_cutoff_minutes  integer not null default 120 check (booking_cutoff_minutes >= 0),
    fare_rules_id           uuid not null references fare_rules(id),
    fare_base_amount        numeric(10,2) not null check (fare_base_amount >= 0),
    currency                text not null default 'USD',
    updated_at              timestamptz not null default now(),
    unique (flight_id, class_name)
);
create index if not exists idx_seat_classes_flight on seat_classes (flight_id);

-- Physical seat map layout per flight
create table if not exists physical_seats (
    id              uuid primary key default gen_random_uuid(),
    flight_id       uuid not null references flights(id) on delete cascade,
    seat_number     text not null, -- e.g. '1A', '12C'
    seat_row        integer not null,
    seat_col        text not null,
    class_name      text not null check (class_name in ('basic_economy','economy','flexible_economy','business','first')),
    is_available    boolean not null default true,
    booking_id      uuid,
    unique (flight_id, seat_number)
);
create index if not exists idx_physical_seats_flight on physical_seats (flight_id);

-- =========================================================================
-- BOOKING / HOLDS  (flight_domain only)
-- =========================================================================

create table if not exists seat_holds (
    id                  uuid primary key default gen_random_uuid(),
    seat_class_id       uuid not null references seat_classes(id),
    passenger_id        uuid references passengers(id),
    quantity            integer not null check (quantity > 0),
    seat_number         text,
    status              text not null default 'active'
                            check (status in ('active','expired','converted','released')),
    idempotency_key     text,
    expires_at          timestamptz not null,
    created_at          timestamptz not null default now()
);
create index if not exists idx_seat_holds_expiry on seat_holds (expires_at) where status = 'active';

create table if not exists bookings (
    id                  uuid primary key default gen_random_uuid(),
    booking_reference   text not null unique,        -- customer-facing PNR-style code
    passenger_id        uuid not null references passengers(id),
    flight_id           uuid not null references flights(id),
    seat_class_id       uuid not null references seat_classes(id),
    quantity            integer not null check (quantity > 0),
    seat_number         text,
    fare_rules_id       uuid not null references fare_rules(id),
    total_amount        numeric(10,2) not null check (total_amount >= 0),
    currency            text not null default 'USD',
    status              text not null default 'pending_payment'
                            check (status in ('pending_payment','confirmed','cancelled','refunded','completed')),
    payment_id          uuid,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);
create index if not exists idx_bookings_passenger on bookings (passenger_id);
create index if not exists idx_bookings_flight on bookings (flight_id);
create index if not exists idx_bookings_status on bookings (status);

create table if not exists waitlist_entries (
    id                  uuid primary key default gen_random_uuid(),
    flight_id           uuid not null references flights(id),
    seat_class_id       uuid not null references seat_classes(id),
    passenger_id        uuid not null references passengers(id),
    quantity            integer not null check (quantity > 0),
    priority_score      numeric not null,
    status              text not null default 'waiting'
                            check (status in ('waiting','promotion_offered','promoted','expired','cancelled')),
    offer_expires_at    timestamptz,
    created_at          timestamptz not null default now()
);
create index if not exists idx_waitlist_pending
    on waitlist_entries (seat_class_id, priority_score)
    where status = 'waiting';

create table if not exists refunds (
    id              uuid primary key default gen_random_uuid(),
    booking_id      uuid not null references bookings(id),
    amount          numeric(10,2) not null check (amount >= 0),
    reason          text,
    status          text not null default 'pending'
                        check (status in ('pending','processing','completed','failed')),
    created_at      timestamptz not null default now(),
    resolved_at     timestamptz
);
create index if not exists idx_refunds_pending_age on refunds (created_at) where status = 'pending';

create table if not exists travel_credits (
    id              uuid primary key default gen_random_uuid(),
    passenger_id    uuid not null references passengers(id),
    booking_id      uuid references bookings(id),
    amount          numeric(10,2) not null check (amount >= 0),
    currency        text not null default 'USD',
    expires_at      timestamptz not null,
    status          text not null default 'active' check (status in ('active','used','expired')),
    created_at      timestamptz not null default now()
);
create index if not exists idx_travel_credits_passenger on travel_credits (passenger_id);

create table if not exists compensation_claims (
    id                  uuid primary key default gen_random_uuid(),
    flight_id           uuid not null references flights(id),
    passenger_id        uuid not null references passengers(id),
    booking_id          uuid references bookings(id),
    claim_type          text not null check (claim_type in ('schedule_change','denied_boarding','delay_compensation')),
    requested_amount    numeric(10,2) not null check (requested_amount >= 0),
    currency            text not null default 'USD',
    status              text not null default 'pending_review' check (status in ('pending_review','approved','rejected')),
    reviewed_by         uuid references admin_users(id),
    reviewed_at         timestamptz,
    reason              text,
    created_at          timestamptz not null default now()
);
create index if not exists idx_compensation_claims_status on compensation_claims (status);

create table if not exists price_alerts (
    id                  uuid primary key default gen_random_uuid(),
    passenger_email     text not null,
    origin              text not null,
    destination         text not null,
    target_price        numeric(10,2) not null,
    last_notified_price numeric(10,2),
    last_notified_at    timestamptz,
    created_at          timestamptz not null default now()
);
create index if not exists idx_price_alerts_route on price_alerts (origin, destination);

-- =========================================================================
-- PAYMENTS
-- =========================================================================

create table if not exists payments (
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

do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints
        where constraint_name = 'fk_bookings_payment'
    ) then
        alter table bookings
            add constraint fk_bookings_payment foreign key (payment_id) references payments(id);
    end if;
end $$;

create table if not exists payment_webhook_events (
    provider_event_id   text primary key,
    provider            text not null default 'stripe',
    payload_json        jsonb not null,
    processed_at        timestamptz not null default now()
);

-- =========================================================================
-- SHARED CONTRACT PLUMBING
-- =========================================================================

create table if not exists idempotency_keys (
    key                     text primary key,
    endpoint                text not null,
    request_hash            text not null,
    response_snapshot_json  jsonb,
    created_at              timestamptz not null default now()
);

create table if not exists domain_events (
    id              bigserial primary key,
    event_type      text not null,
    payload_json    jsonb not null,
    created_at      timestamptz not null default now(),
    processed       boolean not null default false,
    processed_at    timestamptz
);
create index if not exists idx_domain_events_unprocessed
    on domain_events (created_at) where processed = false;

create table if not exists audit_log (
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
create index if not exists idx_audit_entity on audit_log (entity_type, entity_id);

create table if not exists fraud_scores (
    id              uuid primary key default gen_random_uuid(),
    booking_id      uuid not null references bookings(id),
    score           numeric not null,
    signals_json    jsonb not null,
    scored_at       timestamptz not null default now()
);
create index if not exists idx_fraud_scores_booking on fraud_scores (booking_id);

-- =========================================================================
-- POLICY / RAG
-- =========================================================================

create table if not exists policy_docs (
    id              uuid primary key default gen_random_uuid(),
    title           text not null,
    source_url      text,
    content_hash    text not null,
    fare_type_scope text,
    category        text not null default 'general',
    updated_at      timestamptz not null default now()
);

create table if not exists policy_doc_chunks (
    id                  uuid primary key default gen_random_uuid(),
    policy_doc_id       uuid not null references policy_docs(id) on delete cascade,
    chunk_index         integer not null,
    content             text not null,
    pinecone_vector_id  text not null unique,
    updated_at          timestamptz not null default now()
);

create table if not exists policy_question_runs (
    id                      uuid primary key default gen_random_uuid(),
    thread_id               text not null unique,
    booking_id              uuid references bookings(id),
    customer_question       text not null,
    draft_answer            text,
    consistency_flags_json  jsonb,
    status                  text not null default 'drafting'
                                check (status in ('drafting','pending_approval','approved','rejected','sent')),
    approved_by             uuid references admin_users(id),
    approved_at             timestamptz,
    created_at              timestamptz not null default now()
);

-- =========================================================================
-- TRIGGERS — backstop invariants
-- =========================================================================

create or replace function trg_fn_seat_classes_capacity() returns trigger as $$
declare
    effective_max integer;
begin
    effective_max := ceil(new.total_seats * (1.0 + (new.overbooking_buffer_pct / 100.0)));
    if new.booked_seats + new.held_seats > effective_max then
        raise exception 'seat_classes capacity exceeded for %: booked % + held % > effective max %',
            new.id, new.booked_seats, new.held_seats, effective_max;
    end if;
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_seat_classes_capacity on seat_classes;
create trigger trg_seat_classes_capacity
    before insert or update on seat_classes
    for each row execute function trg_fn_seat_classes_capacity();

create or replace function trg_fn_seat_classes_no_shrink() returns trigger as $$
begin
    if new.total_seats < old.booked_seats then
        raise exception 'cannot shrink seat_classes % total to % below booked_seats %',
            new.id, new.total_seats, old.booked_seats;
    end if;
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_seat_classes_no_shrink on seat_classes;
create trigger trg_seat_classes_no_shrink
    before update of total_seats on seat_classes
    for each row execute function trg_fn_seat_classes_no_shrink();

create or replace function trg_fn_touch_updated_at() returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_flights_touch on flights;
create trigger trg_flights_touch before update on flights
    for each row execute function trg_fn_touch_updated_at();

drop trigger if exists trg_seat_classes_touch on seat_classes;
create trigger trg_seat_classes_touch before update on seat_classes
    for each row execute function trg_fn_touch_updated_at();

drop trigger if exists trg_bookings_touch on bookings;
create trigger trg_bookings_touch before update on bookings
    for each row execute function trg_fn_touch_updated_at();

drop trigger if exists trg_payments_touch on payments;
create trigger trg_payments_touch before update on payments
    for each row execute function trg_fn_touch_updated_at();

create or replace function trg_fn_notify_domain_event() returns trigger as $$
begin
    perform pg_notify('domain_events', new.id::text);
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_domain_events_notify on domain_events;
create trigger trg_domain_events_notify
    after insert on domain_events
    for each row execute function trg_fn_notify_domain_event();
