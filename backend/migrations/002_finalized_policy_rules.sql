-- =========================================================================
-- Migration 002: Finalized Policy Rules & Schema Fixes
-- =========================================================================

-- 1. Add fare_type ENUM & CHECK constraint on bookings
do $$
begin
    -- Create enum type if it does not exist
    if not exists (select 1 from pg_type where typname = 'fare_type_enum') then
        create type fare_type_enum as enum ('basic_economy', 'flex');
    end if;

    -- Add fare_type column to bookings if not present
    if not exists (
        select 1 from information_schema.columns
        where table_name = 'bookings' and column_name = 'fare_type'
    ) then
        alter table bookings add column fare_type text not null default 'flex';
    end if;
end $$;

alter table bookings drop constraint if exists chk_bookings_fare_type;
alter table bookings add constraint chk_bookings_fare_type
    check (fare_type in ('basic_economy', 'flex'));

-- 2. Trigger rejecting fare_type='basic_economy' unless seat_classes.class_name = 'Economy'
create or replace function trg_fn_bookings_check_basic_economy() returns trigger as $$
declare
    sc_class_name text;
begin
    if new.fare_type = 'basic_economy' then
        select class_name into sc_class_name
        from seat_classes
        where id = new.seat_class_id;

        if lower(coalesce(sc_class_name, '')) != 'economy' then
            raise exception 'basic_economy fare type is only valid for Economy seat class, got %', sc_class_name;
        end if;
    end if;
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_bookings_check_basic_economy on bookings;
create trigger trg_bookings_check_basic_economy
    before insert or update on bookings
    for each row execute function trg_fn_bookings_check_basic_economy();

-- 3. Drop priority_rank column if present from waitlist_entries and ensure fare_type exists
do $$
begin
    if exists (
        select 1 from information_schema.columns
        where table_name = 'waitlist_entries' and column_name = 'priority_rank'
    ) then
        alter table waitlist_entries drop column priority_rank;
    end if;

    if not exists (
        select 1 from information_schema.columns
        where table_name = 'waitlist_entries' and column_name = 'fare_type'
    ) then
        alter table waitlist_entries add column fare_type text not null default 'flex';
    end if;
end $$;

alter table waitlist_entries drop constraint if exists chk_waitlist_fare_type;
alter table waitlist_entries add constraint chk_waitlist_fare_type
    check (fare_type in ('basic_economy', 'flex'));

-- Dynamic waitlist promotion index (promotes candidates ordered by passenger loyalty, fare_type, created_at)
create index if not exists idx_waitlist_promotion_lookup
    on waitlist_entries (flight_id, seat_class_id, status, created_at);

-- 4. Update refunds.status ENUM / check constraint to ('pending','approved','rejected','escalated','completed')
alter table refunds drop constraint if exists chk_refund_status;
alter table refunds drop constraint if exists refunds_status_check;
alter table refunds add constraint chk_refund_status
    check (status in ('pending', 'approved', 'rejected', 'escalated', 'completed'));
