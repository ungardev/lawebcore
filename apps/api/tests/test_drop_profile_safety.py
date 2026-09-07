"""Tests FIX 07-sep-2026: crash de drop_profile por colisión de kwargs.

Incidente E2E real (run e2efd17b, 07-sep 14:57 UTC): un
detail={'reason': ...} colisionaba con el kwarg explícito
reason=reason.value dentro de drop_profile → TypeError "got multiple
values for keyword argument 'reason'" → el run COMPLETO moría en scoring
DESPUÉS de gastar discovery + enrichment (~$1.4). Había 8 call sites con
ese patrón (prefilter, rerank, 4 geo, bots very_low_er, political).
"""

import structlog.testing
from shared_core.observability import DropLedger, DropReason, drop_profile


def test_detail_with_reason_key_does_not_crash():
    """Regresión EXACTA del incidente e2efd17b: no debe raise."""
    ledger = DropLedger()
    drop_profile(
        "some_handle",
        DropReason.SCORE_BELOW_THRESHOLD,
        "prefilter",
        {"reason": "not_selected_for_enrichment"},
        ledger=ledger,
    )
    assert ledger.get_count(DropReason.SCORE_BELOW_THRESHOLD) == 1


def test_colliding_keys_renamed_not_dropped():
    """La info del detail se preserva bajo detail_<clave> — no se pierde."""
    with structlog.testing.capture_logs() as logs:
        drop_profile(
            "handle_x",
            DropReason.GEO_MISMATCH,
            "scoring",
            {"reason": "tld_mismatch", "username": "handle_x", "stage": "scoring"},
        )
    entries = [e for e in logs if e.get("event") == "profile.dropped"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["reason"] == "GEO_MISMATCH"  # el DropReason real, intacto
    assert entry["detail_reason"] == "tld_mismatch"  # info del detail, preservada
    assert entry["detail_username"] == "handle_x"
    assert entry["detail_stage"] == "scoring"


def test_normal_detail_untouched():
    """Details sin colisión pasan tal cual."""
    with structlog.testing.capture_logs() as logs:
        drop_profile(
            "handle_y",
            DropReason.BOT_PATTERN,
            "scoring",
            {"er": 0.4, "threshold": 0.30},
        )
    entry = [e for e in logs if e.get("event") == "profile.dropped"][0]
    assert entry["er"] == 0.4
    assert entry["threshold"] == 0.30
    assert "detail_reason" not in entry
    assert entry["username"] == "handle_y"


def test_worker_geo_variant_dedupe_guard():
    """Guard de fuente: la variante geo se salta si el kw ya contiene el
    sufijo (evita quemar una llamada con 'dog chow venezuela venezuela')."""
    from pathlib import Path

    src = Path("apps/api/app/workers/worker.py").read_text(encoding="utf-8")
    start = src.index("async def _fetch_step2(")
    end = src.index("return results", start)
    section = src[start:end]
    assert "if geo in kw.lower():" in section, (
        "_fetch_step2 debe saltar la variante geo cuando el kw ya contiene "
        "el sufijo — sin este guard se quemaba una llamada API por keyword "
        "que ya terminaba en 'venezuela'."
    )
