"""Backwards-compatibility alias module.

This module is DEPRECATED. All code should import from railway_pg instead:

    from shared_core.railway_pg import RailwayPg, get_railway_pg

This module exists only to avoid breaking existing imports during the transition.
The "SupabaseRest" name was always a misnomer — this is asyncpg against Railway PostgreSQL.
"""

from shared_core.railway_pg import (
    RailwayPg,
    get_railway_pg,
    _pg_to_json,
    _row_to_dict,
    _strip_postgrest_op,
    _normalize_order,
)

SupabaseRest = RailwayPg


_legacy_supabase_rest: RailwayPg | None = None


def supabase_rest_factory() -> RailwayPg:
    global _legacy_supabase_rest
    if _legacy_supabase_rest is None:
        _legacy_supabase_rest = RailwayPg()
    return _legacy_supabase_rest


supabase_rest: RailwayPg = get_railway_pg()
