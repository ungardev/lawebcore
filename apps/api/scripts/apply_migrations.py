"""Apply pending Supabase migrations on startup.

This script is idempotent: it tracks which migrations have been applied
in a `schema_migrations` table and only runs pending ones.

Usage:
    python -m app.scripts.apply_migrations

Environment:
    DATABASE_URL - PostgreSQL connection string (required for migrations to run)
"""
import asyncio
import hashlib
import os
import re
import sys
from pathlib import Path

import asyncpg


MIGRATIONS_DIR = Path(__file__).parent.parent.parent.parent / "supabase" / "migrations"


def parse_migration_version(filename: str) -> str | None:
    """Extract version from filename like '00000000000017_sentiment_analysis.sql'."""
    m = re.match(r"^0*(\d+)_.*\.sql$", filename)
    return m.group(1) if m else None


def file_checksum(content: str) -> str:
    """Return MD5 hex digest of file content."""
    return hashlib.md5(content.encode()).hexdigest()


async def get_applied_migrations(conn: asyncpg.Connection) -> set[str]:
    """Return set of migration versions already tracked."""
    try:
        rows = await conn.fetch("SELECT version FROM schema_migrations")
        return {str(row["version"]) for row in rows}
    except asyncpg.UndefinedTableError:
        return set()


async def record_migration(
    conn: asyncpg.Connection,
    version: str,
    filename: str,
    checksum: str,
) -> None:
    """Record a migration as applied."""
    await conn.execute(
        """
        INSERT INTO schema_migrations (version, filename, checksum)
        VALUES ($1, $2, $3)
        ON CONFLICT (version) DO NOTHING
        """,
        version,
        filename,
        checksum,
    )


async def ensure_tracking_table(conn: asyncpg.Connection) -> None:
    """Create schema_migrations table if it doesn't exist."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     TEXT PRIMARY KEY,
            filename    TEXT NOT NULL,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            checksum    TEXT
        )
    """)


async def apply_migrations() -> None:
    """Main logic: apply any pending migrations."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[migrations] DATABASE_URL not set, skipping migrations")
        return

    conn = await asyncpg.connect(db_url, command_timeout=60)
    try:
        await ensure_tracking_table(conn)

        applied = await get_applied_migrations(conn)
        pending: list[tuple[str, Path]] = []

        for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = parse_migration_version(migration_path.name)
            if version and version not in applied:
                pending.append((version, migration_path))

        if not pending:
            total = len(applied)
            print(f"[migrations] All {total} migrations already applied")
            return

        print(f"[migrations] Found {len(pending)} pending migrations:")
        for version, path in pending:
            print(f"  → {path.name}")

        for version, path in pending:
            sql = path.read_text()
            checksum = file_checksum(sql)
            try:
                async with conn.transaction():
                    await conn.execute(sql)
                    await record_migration(conn, version, path.name, checksum)
                print(f"  ✓ {path.name} applied")
            except Exception as e:
                print(f"  ✗ {path.name} failed: {e}", file=sys.stderr)
                raise

        total = len(applied) + len(pending)
        print(f"[migrations] Done: {len(pending)} applied, {total} total")
    finally:
        await conn.close()


def main() -> None:
    try:
        asyncio.run(apply_migrations())
    except Exception as e:
        print(f"[migrations] Fatal: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
