"""Apply pending Supabase migrations on startup.

This script is idempotent: it tracks which migrations have been applied
in a `schema_migrations` table and only runs pending ones.

Migrations are fetched directly from GitHub at runtime to avoid build-context
issues in Docker (the supabase/migrations/ directory is outside the API
Docker build context).

Logging is kept minimal to avoid Railway's 500 logs/sec rate limit.
"""
import asyncio
import hashlib
import logging
import os
import re
import sys

import asyncpg
import httpx

logger = logging.getLogger("migrations")

GITHUB_API_URL = (
    "https://api.github.com/repos/ungardev/lawebcore/"
    "contents/supabase/migrations"
)
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/ungardev/lawebcore/"
    "main/supabase/migrations"
)
GITHUB_TOKEN = os.environ.get("GH_TOKEN")


def parse_migration_version(filename: str) -> str | None:
    """Extract version from filename like '00000000000017_sentiment_analysis.sql'."""
    m = re.match(r"^0*(\d+)_.*\.sql$", filename)
    return m.group(1) if m else None


def file_checksum(content: str) -> str:
    """Return MD5 hex digest of file content."""
    return hashlib.md5(content.encode()).hexdigest()


async def list_remote_migrations() -> list[str]:
    """List .sql migration files from the GitHub repo."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(GITHUB_API_URL, headers=headers)
        r.raise_for_status()
        return [
            item["name"]
            for item in r.json()
            if item["name"].endswith(".sql")
        ]


async def fetch_migration_content(filename: str) -> str:
    """Download .sql file content from GitHub raw."""
    url = f"{GITHUB_RAW_URL}/{filename}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


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
    """Main logic: fetch and apply any pending migrations."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("migrations_skipped", reason="DATABASE_URL not set")
        return

    try:
        all_migrations = await list_remote_migrations()
    except Exception as e:
        logger.error("migrations_failed_to_fetch_list", error=str(e))
        return

    conn = await asyncpg.connect(db_url, command_timeout=120)
    try:
        await ensure_tracking_table(conn)

        applied = await get_applied_migrations(conn)

        pending: list[tuple[str, str]] = []
        for filename in all_migrations:
            version = parse_migration_version(filename)
            if version and version not in applied:
                pending.append((version, filename))

        if not pending:
            logger.info("migrations_all_applied", count=len(applied))
            return

        logger.info("migrations_pending", count=len(pending), versions=[v for v, _ in pending])

        for version, filename in pending:
            try:
                sql = await fetch_migration_content(filename)
            except Exception as e:
                logger.error("migration_download_failed", filename=filename, error=str(e))
                continue

            checksum = file_checksum(sql)
            try:
                async with conn.transaction():
                    await conn.execute(sql)
                    await record_migration(conn, version, filename, checksum)
                logger.info("migration_applied", version=version, filename=filename)
            except Exception as e:
                logger.error("migration_failed", version=version, filename=filename, error=str(e))
                continue

        total = len(applied) + len(pending)
        logger.info("migrations_complete", applied=len(pending), total=total)
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
