"""Cleanup mockup data — removes fake handles and demo discovery runs.

Usage:
    # En Railway shell:
    python -m scripts.cleanup_mockup_data

    # O localmente:
    PYTHONPATH=. python apps/api/scripts/cleanup_mockup_data.py
"""

import asyncio
import sys
from uuid import uuid4

sys.path.insert(0, ".")
sys.path.insert(0, "apps/api")

from shared_core import railway_pg


KNOWN_REAL_HANDLES = {
    "gabrielabriceno",
    "carolinameza",
    "fernandoaguirre",
    "juanmendoza",
    "natgeo",
    "elpais",
}


async def cleanup_discovery_candidates() -> dict:
    """Delete discovery_candidates that are not from known real handles."""
    all_candidates = await railway_pg.select(
        table="discovery_candidates",
        select="id,handle,run_id",
        limit=1000,
    )

    deleted = 0
    kept = 0
    for c in all_candidates:
        handle = (c.get("handle") or "").lstrip("@").lower()
        if handle not in KNOWN_REAL_HANDLES:
            try:
                await railway_pg.delete(
                    table="discovery_candidates",
                    filters=[f"id=eq.{c['id']}"],
                )
                deleted += 1
            except Exception:
                pass
        else:
            kept += 1

    return {"deleted": deleted, "kept": kept}


async def cleanup_mockup_influencers() -> dict:
    """Mark influencers that have not been enriched via Apify as legacy_mockup."""
    all_influencers = await railway_pg.select(
        table="influencers",
        select="id,full_name,primary_handle",
        limit=1000,
    )

    marked = 0
    for inf in all_influencers:
        handle = (inf.get("primary_handle") or "").lstrip("@").lower()
        if handle not in KNOWN_REAL_HANDLES:
            try:
                await railway_pg.update(
                    table="influencers",
                    filters=[f"id=eq.{inf['id']}"],
                    values={"tags": ["legacy_mockup"]},
                )
                marked += 1
            except Exception:
                pass

    return {"marked_legacy": marked}


async def cleanup_discovery_runs() -> dict:
    """Delete mockup discovery_runs (status=completed but mockup=true in metadata)."""
    all_runs = await railway_pg.select(
        table="discovery_runs",
        select="id,status,metadata",
        limit=100,
    )

    deleted = 0
    for run in all_runs:
        metadata = run.get("metadata") or {}
        if metadata.get("mockup") is True:
            try:
                await railway_pg.delete(
                    table="discovery_runs",
                    filters=[f"id=eq.{run['id']}"],
                )
                deleted += 1
            except Exception:
                pass

    return {"deleted_runs": deleted}


async def main() -> dict:
    print("Starting mockup data cleanup...")
    print(f"Known real handles (will be preserved): {KNOWN_REAL_HANDLES}")

    results = {}

    try:
        runs_result = await cleanup_discovery_runs()
        results["discovery_runs"] = runs_result
        print(f"  Deleted {runs_result['deleted_runs']} mockup discovery_runs")
    except Exception as e:
        print(f"  Error cleaning discovery_runs: {e}")
        results["discovery_runs"] = {"error": str(e)}

    try:
        candidates_result = await cleanup_discovery_candidates()
        results["discovery_candidates"] = candidates_result
        print(f"  Deleted {candidates_result['deleted']} mockup candidates, kept {candidates_result['kept']}")
    except Exception as e:
        print(f"  Error cleaning discovery_candidates: {e}")
        results["discovery_candidates"] = {"error": str(e)}

    try:
        influencers_result = await cleanup_mockup_influencers()
        results["influencers"] = influencers_result
        print(f"  Marked {influencers_result['marked_legacy']} influencers as legacy_mockup")
    except Exception as e:
        print(f"  Error marking influencers: {e}")
        results["influencers"] = {"error": str(e)}

    print("\nCleanup complete.")
    print("Real handles preserved:", KNOWN_REAL_HANDLES)
    return results


if __name__ == "__main__":
    results = asyncio.run(main())
    print("\nResults:", results)
