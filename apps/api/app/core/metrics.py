"""Prometheus metrics for the Lens discovery pipeline."""

from prometheus_client import Counter, Gauge, Histogram

lens_pipeline_duration_seconds = Histogram(
    "lens_pipeline_duration_seconds",
    "Duration of discovery pipeline steps",
    ["step"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

lens_candidates_total = Counter(
    "lens_candidates_total",
    "Total candidates by final status",
    ["status"],
)

lens_apify_cost_usd_total = Counter(
    "lens_apify_cost_usd_total",
    "Total Apify cost in USD by actor",
    ["actor_id"],
)

lens_cache_hits_total = Counter(
    "lens_cache_hits_total",
    "Cache hits by layer and result",
    ["layer", "result"],
)

lens_active_runs = Gauge(
    "lens_active_runs",
    "Number of currently running discovery runs",
)

lens_profile_generation_total = Counter(
    "lens_profile_generation_total",
    "Profile generation calls by source",
    ["source"],
)
