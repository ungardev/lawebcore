"""Apply database schema on startup.

Single-file approach: reads schema.sql from the supabase/ directory.
Idempotent: checks schema_migrations table to avoid re-applying.

No GitHub fetch — schema.sql is bundled with the application.
"""
import asyncio
import logging
import os
import sys

import asyncpg

logger = logging.getLogger("migrations")

SCHEMA_VERSION = "00000000000001"
SCHEMA_FILENAME = "schema.sql"


async def get_applied_versions(conn: asyncpg.Connection) -> set[str]:
    """Return set of migration versions already tracked."""
    try:
        rows = await conn.fetch("SELECT version FROM schema_migrations")
        return {str(row["version"]) for row in rows}
    except asyncpg.UndefinedTableError:
        return set()


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


def find_schema_file() -> str | None:
    """Locate schema.sql relative to this script or working directory."""
    search_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "supabase", SCHEMA_FILENAME),
        os.path.join(os.getcwd(), "supabase", SCHEMA_FILENAME),
        f"/app/supabase/{SCHEMA_FILENAME}",
    ]
    for path in search_paths:
        path = os.path.normpath(path)
        if os.path.exists(path):
            return path
    return None


async def apply_migrations() -> None:
    """Apply schema if not already applied."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("migrations_skipped", reason="DATABASE_URL not set")
        return

    schema_path = find_schema_file()
    if not schema_path:
        logger.warning("schema_sql_not_found", reason="schema.sql not found in search paths")
        return

    conn = await asyncpg.connect(db_url, command_timeout=120)
    try:
        await ensure_tracking_table(conn)

        applied = await get_applied_versions(conn)

        if SCHEMA_VERSION in applied:
            logger.info("schema_already_applied", version=SCHEMA_VERSION)
            return

        logger.info("applying_schema", version=SCHEMA_VERSION, path=schema_path)

        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()

        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                """
                INSERT INTO schema_migrations (version, filename)
                VALUES ($1, $2)
                ON CONFLICT (version) DO NOTHING
                """,
                SCHEMA_VERSION,
                SCHEMA_FILENAME,
            )

        logger.info("schema_applied", version=SCHEMA_VERSION)
    except Exception as e:
        logger.error("schema_apply_failed", error=str(e))
    finally:
        await conn.close()


def main() -> None:
    try:
        asyncio.run(apply_migrations())
    except Exception as e:
        logger.error("migrations_fatal_error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
