"""
ARQ worker for La Web Core async jobs.
Handles:
- AI embedding generation
- AI generation tasks (brief, post-mortem, etc.)
- Campaign automation triggers
- Scheduled report generation
- Integration syncs (HypeAuditor, etc.)
"""

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings


async def startup(ctx):
    """Initialize worker context (DB, AI clients)."""
    print("[workers] starting up")


async def shutdown(ctx):
    """Cleanup on shutdown."""
    print("[workers] shutting down")


async def embed_document_task(ctx, document_id: str):
    """Chunk a document, embed it, store in pgvector."""
    print(f"[workers] embedding document {document_id}")
    # TODO: implement


async def generate_insight_task(ctx, campaign_id: str, prompt_code: str):
    """Generate an AI insight for a campaign."""
    print(f"[workers] generating insight for campaign {campaign_id} with {prompt_code}")
    # TODO: implement


async def sync_hypeauditor_task(ctx, influencer_id: str):
    """Pull fresh metrics from HypeAuditor for an influencer."""
    print(f"[workers] syncing HypeAuditor data for {influencer_id}")
    # TODO: implement


async def scheduled_reports_cron(ctx):
    """Run scheduled reports."""
    print("[workers] running scheduled reports")
    # TODO: query scheduled_reports where is_active=true and next_run_at <= now


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)
    functions = [
        embed_document_task,
        generate_insight_task,
        sync_hypeauditor_task,
    ]
    cron_jobs = [
        cron(scheduled_reports_cron, hour=9, minute=0),  # daily 9 AM
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 600  # 10 minutes