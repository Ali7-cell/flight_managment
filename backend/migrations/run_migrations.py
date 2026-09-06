"""
Database migration runner for Flight Management System.
Executes SQL migrations against target Postgres database.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg

load_dotenv()

def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    # Ensure postgresql:// prefix if using sqlalchemy style or sslmode
    return url

def run_migrations():
    db_url = get_database_url()
    migrations_dir = Path(__file__).parent
    sql_files = sorted(migrations_dir.glob("*.sql"))

    print(f"Connecting to database to apply {len(sql_files)} migration(s)...")
    # Using psycopg with autocommit so DDL runs cleanly
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Create migrations tracking table if not exists
            cur.execute("""
                create table if not exists schema_migrations (
                    version text primary key,
                    applied_at timestamptz not null default now()
                );
            """)

            for sql_file in sql_files:
                version = sql_file.name
                cur.execute("select 1 from schema_migrations where version = %s", (version,))
                if cur.fetchone():
                    print(f"[-] Skipping already applied migration: {version}")
                    continue

                print(f"[+] Applying migration: {version}...")
                content = sql_file.read_text(encoding="utf-8")
                cur.execute(content)
                cur.execute("insert into schema_migrations (version) values (%s)", (version,))
                print(f"[OK] Successfully applied: {version}")

    print("All migrations applied successfully.")

if __name__ == "__main__":
    run_migrations()
