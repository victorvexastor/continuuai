from __future__ import annotations

import argparse
import os
from pathlib import Path
import hashlib
import psycopg


def ensure_schema_migrations(conn: psycopg.Connection) -> None:
    with conn.transaction():
        conn.execute("""
          CREATE TABLE IF NOT EXISTS schema_migrations (
            filename text PRIMARY KEY,
            applied_at timestamptz NOT NULL DEFAULT now(),
            file_sha256 text
          );
        """)


def already_applied(conn: psycopg.Connection, filename: str) -> bool:
    # Use a savepoint to handle any transaction state issues
    try:
        with conn.transaction():
            row = conn.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,)).fetchone()
            return row is not None
    except psycopg.errors.InFailedSqlTransaction:
        conn.rollback()
        with conn.transaction():
            row = conn.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,)).fetchone()
            return row is not None

def applied_hash(conn: psycopg.Connection, filename: str) -> str | None:
    try:
        row = conn.execute("SELECT file_sha256 FROM schema_migrations WHERE filename = %s", (filename,)).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def apply_file(conn: psycopg.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    h = sha256_str(sql)
    with conn.transaction():
        conn.execute(sql)
        # insert with hash if column exists
        try:
            conn.execute("INSERT INTO schema_migrations(filename, file_sha256) VALUES (%s, %s)", (path.name, h))
        except Exception:
            conn.execute("INSERT INTO schema_migrations(filename) VALUES (%s)", (path.name,))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--migrations", required=True, help="Path to migrations dir")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL missing")

    mig_dir = Path(args.migrations)
    files = sorted([p for p in mig_dir.glob("*.sql")], key=lambda p: p.name)

    with psycopg.connect(dsn) as conn:
        ensure_schema_migrations(conn)
        for f in files:
            if already_applied(conn, f.name):
                # hash drift detection (best-effort if column exists)
                try:
                    sql = f.read_text(encoding="utf-8")
                    current_hash = sha256_str(sql)
                    stored = applied_hash(conn, f.name)
                    if stored and stored != current_hash:
                        raise SystemExit(f"ERROR: migration drift for {f.name}: stored hash differs")
                except FileNotFoundError:
                    pass
                print(f"skip {f.name}")
                continue
            print(f"apply {f.name}")
            apply_file(conn, f)

    print("migrations complete")


if __name__ == "__main__":
    main()
