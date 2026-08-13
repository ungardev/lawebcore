"""Persistence of conversational state for the Discovery module."""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from shared_core.railway_pg import railway_pg
from discovery.schemas import ConversationStep, DiscoverySearchRequest

logger = logging.getLogger(__name__)


def _generate_run_title(brief: DiscoverySearchRequest) -> str:
    parts = []
    if brief.product_name:
        parts.append(brief.product_name)
    elif brief.industry:
        parts.append(brief.industry)
    if brief.audience_countries:
        parts.append(" · " + ", ".join(brief.audience_countries[:3]))
    if brief.platforms:
        platforms = ", ".join(p.value for p in brief.platforms[:2])
        parts.append(f" [{platforms}]")
    return "".join(parts)[:120] or "Nueva búsqueda"


def _generate_conversation_title(brief_data: dict[str, Any] | None) -> str | None:
    if not brief_data:
        return None
    parts = []
    product_name = brief_data.get("product_name")
    industry = brief_data.get("industry")
    if product_name:
        parts.append(product_name)
    elif industry:
        parts.append(industry)
    countries = brief_data.get("audience_countries") or []
    if countries:
        parts.append(" · " + ", ".join(countries[:3]))
    platforms = brief_data.get("platforms") or []
    if platforms:
        platform_vals = [p.value if hasattr(p, "value") else str(p) for p in platforms[:2]]
        parts.append(f" [{', '.join(platform_vals)}]")
    return "".join(parts)[:80] or None


_COLUMNS = {
    "accumulated_brief": "TEXT",
    "parsed_brief_json": "JSONB",
    "pending_refinements": "JSONB",
    "title": "TEXT",
}


async def migrate_discovery_conversations_schema() -> None:
    """Add missing columns to discovery_conversations and discovery_runs if they don't exist."""
    from shared_core.railway_pg import railway_pg

    pool = await railway_pg._ensure_pool()
    async with pool.acquire() as conn:
        for col_name, col_type in _COLUMNS.items():
            try:
                await conn.execute(
                    f'ALTER TABLE discovery_conversations ADD COLUMN IF NOT EXISTS {col_name} {col_type}'
                )
                logger.info(f"[migration] Added column {col_name} to discovery_conversations")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"[migration] Column {col_name} already exists, skipping")
                else:
                    logger.warning(f"[migration] Could not add column {col_name}: {e}")

        try:
            await conn.execute(
                'ALTER TABLE discovery_runs ADD COLUMN IF NOT EXISTS title TEXT'
            )
            logger.info("[migration] Added column title to discovery_runs")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("[migration] Column title already exists in discovery_runs, skipping")
            else:
                logger.warning(f"[migration] Could not add column title to discovery_runs: {e}")

        try:
            await conn.execute("""
                UPDATE discovery_conversations dc
                SET title = COALESCE(
                    (
                        SELECT title FROM discovery_runs
                        WHERE id = dc.discovery_run_id AND title IS NOT NULL
                    ),
                    'Lens · ' || TO_CHAR(dc.last_message_at, 'DD/MM HH24:MI')
                )
                WHERE dc.title IS NULL AND dc.discovery_run_id IS NOT NULL
            """)
            logger.info("[migration] Backfilled titles for discovery_conversations from runs")
        except Exception as e:
            logger.warning(f"[migration] Could not backfill titles from runs: {e}")

        try:
            await conn.execute("""
                UPDATE discovery_conversations
                SET title = LEFT(
                    (SELECT content FROM discovery_messages WHERE conversation_id = discovery_conversations.id AND role = 'user' ORDER BY created_at ASC LIMIT 1), 60
                )
                WHERE title IS NULL
                  AND EXISTS (
                      SELECT 1 FROM discovery_messages
                      WHERE conversation_id = discovery_conversations.id AND role = 'user'
                  )
            """)
            logger.info("[migration] Backfilled titles for discovery_conversations from first user message")
        except Exception as e:
            logger.warning(f"[migration] Could not backfill titles from messages: {e}")

        try:
            await conn.execute(
                "UPDATE discovery_conversations SET title = 'Lens · ' || TO_CHAR(last_message_at, 'DD/MM HH24:MI') WHERE title IS NULL"
            )
            logger.info("[migration] Set timestamp fallback titles for discovery_conversations")
        except Exception as e:
            logger.warning(f"[migration] Could not backfill timestamp titles: {e}")

        try:
            await conn.execute(
                "UPDATE discovery_runs SET title = 'Búsqueda · ' || TO_CHAR(created_at, 'DD/MM HH24:MI') WHERE title IS NULL"
            )
            logger.info("[migration] Backfilled titles for discovery_runs")
        except Exception as e:
            logger.warning(f"[migration] Could not backfill titles for discovery_runs: {e}")


async def save_conversation(
    conversation_id: UUID,
    user_id: UUID,
    bu_id: UUID | None = None,
    step: str = "start",
    state: dict[str, Any] | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    values = {
        "id": str(conversation_id),
        "user_id": str(user_id),
        "current_step": step,
        "state": state or {},
        "status": "active",
        "started_at": datetime.now(timezone.utc),
        "last_message_at": datetime.now(timezone.utc),
    }
    if bu_id:
        values["bu_id"] = str(bu_id)
    if title:
        values["title"] = title

    return await railway_pg.insert(
        table="discovery_conversations",
        values=values,
        returning="representation",
    )


async def get_conversation(conversation_id: UUID) -> dict[str, Any] | None:
    return await railway_pg.select_one(
        table="discovery_conversations",
        select="id,user_id,bu_id,current_step,state,discovery_run_id,accumulated_brief,parsed_brief_json,pending_refinements,status,started_at,last_message_at,title",
        filters=[f"id=eq.{conversation_id}"],
    )


async def update_conversation(
    conversation_id: UUID,
    updates: dict[str, Any],
) -> None:
    await railway_pg.update(
        table="discovery_conversations",
        filters=[f"id=eq.{conversation_id}"],
        values=updates,
    )


async def save_message(
    conversation_id: UUID,
    role: str,
    content: str,
    tool_calls: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    reasoning: str | None = None,
    cost_usd: float | None = None,
    latency_ms: int | None = None,
) -> dict[str, Any]:
    values = {
        "conversation_id": str(conversation_id),
        "role": role,
        "content": content,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "reasoning": reasoning,
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
        "created_at": datetime.now(timezone.utc),
    }
    return await railway_pg.insert(
        table="discovery_messages",
        values=values,
        returning="representation",
    )


async def launch_discovery_run(
    brief: DiscoverySearchRequest,
    created_by: UUID,
    bu_id: UUID | None = None,
) -> dict[str, Any]:
    import uuid as _uuid

    run_values = {
        "id": str(_uuid.uuid4()),
        "title": _generate_run_title(brief),
        "brief_text": f"Search: {brief.product_name or brief.industry or 'Influencers'}",
        "brief_parsed": brief.model_dump(),
        "product_name": brief.product_name,
        "brand_id": str(brief.brand_id) if brief.brand_id else None,
        "industry": brief.industry,
        "niches": brief.niches,
        "audience_gender": brief.audience_gender.value,
        "audience_age_min": brief.audience_age_min,
        "audience_age_max": brief.audience_age_max,
        "audience_countries": brief.audience_countries,
        "audience_cities": brief.audience_cities,
        "platforms": [p.value for p in brief.platforms],
        "status": "pending",
        "created_by": str(created_by),
        "estimated_cost_usd": 0.0,
    }
    if bu_id:
        run_values["bu_id"] = str(bu_id)

    run = await railway_pg.insert(
        table="discovery_runs",
        values=run_values,
        returning="representation",
    )

    run_record = run[0] if isinstance(run, list) else run
    run_id = run_record["id"]

    return {
        "id": UUID(run_id),
        "created_at": run_record.get("created_at", ""),
    }


conversation_memory = type(
    "ConversationMemory",
    (),
    {
        "save_conversation": staticmethod(save_conversation),
        "get_conversation": staticmethod(get_conversation),
        "update_conversation": staticmethod(update_conversation),
        "save_message": staticmethod(save_message),
        "launch_discovery_run": staticmethod(launch_discovery_run),
    },
)()
