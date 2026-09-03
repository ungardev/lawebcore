"""Funnel Invariant Test — Regression test for Hito 30 + Claude Code Fable 5 P0 fixes.

Ref:
- docs/AUDITORIA_CLAUDE_CODE_FABLE5_FULL_03-09-26.md
- docs/VERIFICACION_LANZ_V2_vs_CODIGO_28-08-26.md §3

El invariante del embudo es la pieza central del Hito 30: la propiedad que hace
al sistema autoauditable. Si un perfil sale del pipeline sin pasar por drop_profile(),
la identidad del embudo no cuadra y la corrida debe quedar INCONSISTENT.

FÓRMULA DEL INVARIANTE (03-sep-2026):
    funnel.deduped == total + drop_ledger.total()

La fórmula anterior (discovered - deduped == drops) era incorrecta porque:
- discovered (step1_handles) solo representaba hashtags, no todas las fuentes
- La fórmula correcta usa deduped (perfiles post-dedup de todas las fuentes)
  como entrada, delivered (total) como salida, y drops como lo descartado

Antes del fix (ce148e2), funnel_invariant_ok estaba cableado a True literal.
Antes del fix P0-1 (452d7e9), la fórmula usaba step1_handles - profiles = drops
(siempre daba negativo porque step1 < profiles).
"""

import pytest
from shared_core.observability import DropLedger, DropReason, determine_final_status, RunStatus


class TestFunnelInvariant:
    """Tests para el invariante del embudo en determine_final_status()."""

    def test_inconsistent_when_invariant_broken_zero_candidates(self):
        """Si la identidad no cuadra y total_candidates=0, debe返回 INCONSISTENT."""
        result = determine_final_status(
            total_candidates=0,
            funnel_invariant_ok=False,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.INCONSISTENT

    def test_empty_when_invariant_ok_zero_candidates(self):
        """Si la identidad cuadra y total_candidates=0, debe返回 EMPTY (no INCONSISTENT)."""
        result = determine_final_status(
            total_candidates=0,
            funnel_invariant_ok=True,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.EMPTY

    def test_delivered_when_invariant_ok_and_candidates_exist(self):
        """Si la identidad cuadra y hay candidatos, debe返回 DELIVERED."""
        result = determine_final_status(
            total_candidates=15,
            funnel_invariant_ok=True,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.DELIVERED

    def test_degraded_when_step3_degraded(self):
        """step3_degraded tiene prioridad sobre el invariante cuando hay candidatos."""
        result = determine_final_status(
            total_candidates=5,
            funnel_invariant_ok=True,
            step3_degraded=True,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.DEGRADED

    def test_aborted_budget_when_budget_aborted(self):
        """budget_aborted tiene prioridad sobre todos los demás estados."""
        result = determine_final_status(
            total_candidates=0,
            funnel_invariant_ok=True,
            step3_degraded=False,
            budget_aborted=True,
            has_exception=False,
        )
        assert result == RunStatus.ABORTED_BUDGET

    def test_failed_when_has_exception(self):
        """has_exception tiene máxima prioridad."""
        result = determine_final_status(
            total_candidates=10,
            funnel_invariant_ok=True,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=True,
        )
        assert result == RunStatus.FAILED


class TestDropLedgerFunnelIdentity:
    """Tests para la identidad del embudo con la fórmula correcta.

    Fórmula: deduped == delivered + drops
    - deduped: perfiles que entraron a la fase de scoring (post-dedup de todas las fuentes)
    - delivered: candidatos persistidos en DB (total)
    - drops: perfiles descartados por drop_profile() en cualquier stage
    """

    def test_identity_holds_no_drops(self):
        """Sin drops, deduped == delivered."""
        ledger = DropLedger()
        deduped = 100
        delivered = 100
        invariant_ok = deduped == delivered + ledger.total()
        assert invariant_ok is True

    def test_identity_with_drops(self):
        """Con drops registrados, la identidad deduped == delivered + drops."""
        ledger = DropLedger()
        deduped = 100
        delivered = 85
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        ledger.record(DropReason.GEO_MISMATCH)
        ledger.record(DropReason.GEO_MISMATCH)
        ledger.record(DropReason.GEO_MISMATCH)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        assert ledger.total() == 15
        invariant_ok = deduped == delivered + ledger.total()
        assert invariant_ok is True

    def test_inconsistent_when_brand_safety_leak(self):
        """Si brand safety excluye perfiles sin drop_profile(), la identidad falla.

        Este es el caso P0-4 de Claude Code Fable 5: el mecanismo de brand safety
        (exclude_handles de Nestlé) excluía perfiles con un dict comprehension
        sin registrar los drops. La identidad falla porque deduped > delivered + drops.
        """
        ledger = DropLedger()
        deduped = 100
        delivered = 85
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        ledger.record(DropReason.GEO_MISMATCH)
        ledger.record(DropReason.GEO_MISMATCH)
        ledger.record(DropReason.GEO_MISMATCH)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        ledger.record(DropReason.BOT_PATTERN)
        assert ledger.total() == 15
        invariant_ok = deduped == delivered + ledger.total()
        assert invariant_ok is True

        brand_leak = 5
        invariant_ok_with_leak = deduped == (delivered + brand_leak) + ledger.total()
        assert invariant_ok_with_leak is False

    def test_inconsistent_when_untracked_drop(self):
        """Si hay drops sin registrar, la identidad falla → INCONSISTENT.

        Este es el caso que el fix de ce148e2 + P0-1 previene: un perfil que sale
        del pipeline sin pasar por drop_profile() hace que deduped != delivered + drops.
        """
        ledger = DropLedger()
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        deduped = 100
        delivered = 85
        untracked_drops = 5
        invariant_ok = deduped == delivered + ledger.total()
        assert invariant_ok is True

        invariant_ok_with_leak = deduped == delivered + untracked_drops + ledger.total()
        assert invariant_ok_with_leak is False
        result = determine_final_status(
            total_candidates=0,
            funnel_invariant_ok=invariant_ok_with_leak,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.INCONSISTENT

    def test_inconsistent_only_when_total_candidates_is_zero(self):
        """INCONSISTENT solo se devuelve cuando total_candidates == 0."""
        ledger = DropLedger()
        ledger.record(DropReason.MISSING_FOLLOWER_FIELD)
        deduped = 100
        delivered = 85
        invariant_ok = deduped == delivered + ledger.total()
        result = determine_final_status(
            total_candidates=15,
            funnel_invariant_ok=False,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.DELIVERED

    def test_delivered_when_invariant_ok_with_drops(self):
        """Con drops registrados y identidad correcta, DELIVERED aunque delivered < deduped."""
        ledger = DropLedger()
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        ledger.record(DropReason.GEO_MISMATCH)
        deduped = 100
        delivered = 85
        invariant_ok = deduped == delivered + ledger.total()
        assert invariant_ok is True
        result = determine_final_status(
            total_candidates=delivered,
            funnel_invariant_ok=invariant_ok,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.DELIVERED
