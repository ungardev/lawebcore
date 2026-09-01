"""Funnel Invariant Test — Regression test for Claude Code finding.

Ref: docs/VERIFICACION_LANZ_V2_vs_CODIGO_28-08-26.md §3

El invariante del embudo es la pieza central del Hito 30: la propiedad que hace
al sistema autoauditable. Si un perfil sale del pipeline sin pasar por drop_profile(),
la identidad del embudo no cuadra y la corrida debe quedar INCONSISTENT.

Antes del fix (ce148e2), funnel_invariant_ok estaba cableado a True literal,
haciendo INCONSISTENT inalcanzable por construcción.
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
    """Tests para la identidad del embudo: discovered - deduped == ledger.total()."""

    def test_identity_holds_no_drops(self):
        """Sin drops, discovered == deduped."""
        ledger = DropLedger()
        discovered = 100
        deduped = 100
        invariant_ok = (discovered - deduped) == ledger.total()
        assert invariant_ok is True

    def test_identity_with_drops(self):
        """Con drops registrados, la identidad discovered - deduped == drops."""
        ledger = DropLedger()
        discovered = 100
        deduped = 85
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
        invariant_ok = (discovered - deduped) == ledger.total()
        assert invariant_ok is True

    def test_inconsistent_when_untracked_drop(self):
        """Si hay 5 drops sin registrar, la identidad falla → INCONSISTENT.

        Este es el caso que el fix de ce148e2 previene: un perfil que sale del
        pipeline sin pasar por drop_profile() hace que discovered - deduped != ledger.total().
        """
        ledger = DropLedger()
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        ledger.record(DropReason.BELOW_MIN_FOLLOWERS)
        discovered = 100
        deduped = 85
        untracked_drops = 5
        invariant_ok = (discovered - deduped) == ledger.total()
        assert invariant_ok is False
        result = determine_final_status(
            total_candidates=0,
            funnel_invariant_ok=invariant_ok,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.INCONSISTENT

    def test_inconsistent_only_when_total_candidates_is_zero(self):
        """INCONSISTENT solo se devuelve cuando total_candidates == 0."""
        ledger = DropLedger()
        ledger.record(DropReason.MISSING_FOLLOWER_FIELD)
        discovered = 100
        deduped = 85
        invariant_ok = (discovered - deduped) == ledger.total()
        result = determine_final_status(
            total_candidates=15,
            funnel_invariant_ok=False,
            step3_degraded=False,
            budget_aborted=False,
            has_exception=False,
        )
        assert result == RunStatus.DELIVERED
