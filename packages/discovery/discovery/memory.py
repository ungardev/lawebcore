"""Persistence of conversational state for the Discovery module."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from shared_core.supabase_rest import supabase_rest
from discovery.schemas import ConversationStep, DiscoverySearchRequest


async def save_conversation(
    conversation_id: UUID,
    user_id: UUID,
    bu_id: UUID | None = None,
    step: str = "start",
    state: dict[str, Any] | None = None,
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

    return await supabase_rest.insert(
        table="discovery_conversations",
        values=values,
        returning="representation",
    )


async def get_conversation(conversation_id: UUID) -> dict[str, Any] | None:
    return await supabase_rest.select_one(
        table="discovery_conversations",
        select="id,user_id,bu_id,current_step,state,discovery_run_id,accumulated_brief,status,started_at,last_message_at",
        filters=[f"id=eq.{conversation_id}"],
    )


async def update_conversation(
    conversation_id: UUID,
    updates: dict[str, Any],
) -> None:
    await supabase_rest.update(
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
    return await supabase_rest.insert(
        table="discovery_messages",
        values=values,
        returning="representation",
    )


async def launch_discovery_run(
    brief: DiscoverySearchRequest,
    created_by: UUID,
    bu_id: UUID | None = None,
) -> dict[str, Any]:
    run_values = {
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
        "budget_usd": brief.budget_usd,
        "tone": brief.tone,
        "platforms": [p.value for p in brief.platforms],
        "status": "pending",
        "created_by": str(created_by),
        "estimated_cost_usd": 0.0,
    }
    if bu_id:
        run_values["bu_id"] = str(bu_id)

    run = await supabase_rest.insert(
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
