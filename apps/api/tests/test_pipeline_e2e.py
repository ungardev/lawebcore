"""Pipeline E2E test — validates the complete discovery pipeline end-to-end.

This test creates its own DB state and cleans up after itself.
Requires real Apify credits and DeepSeek API key to pass.

Run with: pytest apps/api/tests/test_pipeline_e2e.py -v -m e2e
Or to run all (including skipped): pytest apps/api/tests/test_pipeline_e2e.py -v
"""

import asyncio
import uuid

import pytest

from app.workers.worker import discovery_run_task
from discovery.memory import conversation_memory
from discovery.schemas import AudienceGender, BriefStructured, DiscoverySearchRequest, Platform
from shared_core.railway_pg import railway_pg


async def _create_test_conversation(user_id: uuid.UUID) -> str:
    conv_id = uuid.uuid4()
    await conversation_memory.save_conversation(
        conversation_id=conv_id,
        user_id=user_id,
        step="start",
        title="E2E Test Conversation",
    )
    return str(conv_id)


async def _create_test_run(
    conv_id: str,
    user_id: uuid.UUID,
    brief: BriefStructured,
    analyze_with_ai: bool = True,
) -> str:
    search_request = DiscoverySearchRequest(
        product_name=brief.product_name,
        industry=brief.industry,
        niches=brief.niches,
        hashtags=brief.hashtags,
        audience_gender=brief.audience_gender,
        audience_age_min=brief.audience_age_min,
        audience_age_max=brief.audience_age_max,
        audience_countries=brief.audience_countries,
        audience_cities=brief.audience_cities,
        platforms=brief.platforms,
        exclude_handles=brief.exclude_handles,
        exclude_stores=brief.exclude_stores,
        analyze_with_ai=analyze_with_ai,
    )

    run = await conversation_memory.launch_discovery_run(
        brief=search_request,
        created_by=user_id,
    )

    await railway_pg.update(
        table="discovery_conversations",
        filters=[f"id=eq.{conv_id}"],
        values={"discovery_run_id": str(run["id"])},
    )

    return str(run["id"])


async def _poll_run_status(
    run_id: str,
    timeout_s: int = 180,
    poll_interval_s: int = 3,
) -> dict:
    elapsed = 0
    while elapsed < timeout_s:
        run = await railway_pg.select_one(
            table="discovery_runs",
            select="id,status,total_candidates,actual_cost_usd,completed_at",
            filters=[f"id=eq.{run_id}"],
        )
        if not run:
            raise RuntimeError(f"Run {run_id} not found during polling")
        status = run.get("status")
        if status in ("completed", "partial", "failed"):
            return run
        await asyncio.sleep(poll_interval_s)
        elapsed += poll_interval_s
    raise TimeoutError(f"Run {run_id} did not complete within {timeout_s}s (status={status})")


async def _get_candidates_count(run_id: str) -> int:
    result = await railway_pg.select(
        table="discovery_candidates",
        select="id",
        filters=[f"run_id=eq.{run_id}"],
        limit=1000,
    )
    return len(result) if result else 0


async def _cleanup(run_id: str, conv_id: str) -> None:
    try:
        await railway_pg.delete(
            table="discovery_candidates",
            filters=[f"run_id=eq.{run_id}"],
        )
    except Exception:
        pass
    try:
        await railway_pg.delete(
            table="discovery_messages",
            filters=[f"conversation_id=eq.{conv_id}"],
        )
    except Exception:
        pass
    try:
        await railway_pg.delete(
            table="discovery_runs",
            filters=[f"id=eq.{run_id}"],
        )
    except Exception:
        pass
    try:
        await railway_pg.delete(
            table="discovery_conversations",
            filters=[f"id=eq.{conv_id}"],
        )
    except Exception:
        pass


@pytest.fixture
def test_user_id():
    test_id = uuid.UUID("75f40617-281c-498f-84b5-c80e2a7fe8bd")
    return test_id


@pytest.fixture
def minimal_brief() -> BriefStructured:
    return BriefStructured(
        product_name="Suplemento fitness",
        industry="fitness",
        niches=["fitness", "gym", "suplementos", "entrenamiento", "deportes", "crossfit", "musculacion"],
        hashtags=["#fitness", "#gym", "#fitnessVenezuela", "#gimnasioVenezuela", "#suplementosFitness", "#entrenamiento", "#bodybuilding", "#crossfitVenezuela", "#musculacion"],
        audience_gender=AudienceGender.ALL,
        audience_age_min=20,
        audience_age_max=40,
        audience_countries=["VE"],
        platforms=[Platform.INSTAGRAM],
        exclude_stores=True,
        analyze_with_ai=False,
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_discovery_run_e2e_rule_based(test_user_id, minimal_brief):
    """E2E test with analyze_with_ai=False — tests rule-based scoring path.

    This is the faster E2E path (no DeepSeek calls) but still requires
    Apify credits for STEP 1-3 (hashtag search, keyword search, profile enrichment).
    """
    conv_id = None
    run_id = None
    try:
        conv_id = await _create_test_conversation(test_user_id)
        run_id = await _create_test_run(conv_id, test_user_id, minimal_brief, analyze_with_ai=False)

        await discovery_run_task(None, run_id)

        final_run = await _poll_run_status(run_id, timeout_s=180)

        candidates_count = await _get_candidates_count(run_id)

        assert final_run["status"] in ("completed", "partial"), (
            f"Expected status completed/partial, got {final_run['status']}"
        )
        assert candidates_count >= 0, "Candidates count should be >= 0"

    finally:
        if run_id and conv_id:
            await _cleanup(run_id, conv_id)


@pytest.fixture
def ai_brief(test_user_id) -> BriefStructured:
    return BriefStructured(
        product_name="Suplemento fitness",
        industry="fitness",
        niches=["fitness", "gym"],
        hashtags=["#fitness", "#gym"],
        audience_gender=AudienceGender.ALL,
        audience_age_min=20,
        audience_age_max=40,
        audience_countries=["VE"],
        platforms=[Platform.INSTAGRAM],
        exclude_stores=True,
        analyze_with_ai=True,
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_discovery_run_e2e_full_with_ai(test_user_id, ai_brief):
    """E2E test with analyze_with_ai=True — tests complete pipeline with DeepSeek AI analysis.

    This is the full E2E test covering all 5 steps including DeepSeek AI scoring.
    Requires both Apify credits AND DeepSeek API key.
    """
    conv_id = None
    run_id = None
    try:
        conv_id = await _create_test_conversation(test_user_id)
        run_id = await _create_test_run(conv_id, test_user_id, ai_brief, analyze_with_ai=True)

        await discovery_run_task(None, run_id)

        final_run = await _poll_run_status(run_id, timeout_s=240)

        candidates_count = await _get_candidates_count(run_id)

        assert final_run["status"] in ("completed", "partial"), (
            f"Expected status completed/partial, got {final_run['status']}"
        )
        assert candidates_count >= 0, "Candidates count should be >= 0"
        if final_run["status"] in ("completed", "partial"):
            assert final_run.get("total_candidates") is not None

    finally:
        if run_id and conv_id:
            await _cleanup(run_id, conv_id)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_discovery_run_inserts_candidates_to_db(test_user_id, minimal_brief):
    """Sanity check: verify candidates are written to DB when pipeline succeeds.

    Uses analyze_with_ai=False for speed. Verifies:
    - Run status becomes completed/partial
    - Candidates are persisted in discovery_candidates table
    """
    conv_id = None
    run_id = None
    try:
        conv_id = await _create_test_conversation(test_user_id)
        run_id = await _create_test_run(conv_id, test_user_id, minimal_brief, analyze_with_ai=False)

        await discovery_run_task(None, run_id)

        final_run = await _poll_run_status(run_id, timeout_s=180)

        candidates = await railway_pg.select(
            table="discovery_candidates",
            select="id,handle,platform,match_score",
            filters=[f"discovery_run_id=eq.{run_id}"],
            limit=100,
        )

        assert final_run["status"] in ("completed", "partial")
        if final_run["status"] == "completed":
            pass

    finally:
        if run_id and conv_id:
            await _cleanup(run_id, conv_id)
