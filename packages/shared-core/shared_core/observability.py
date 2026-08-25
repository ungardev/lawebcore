"""Taxonomía cerrada de eventos y sistema de observabilidad para LENS Discovery.

Arquitectura de observabilidad de 7 capas:
1. Taxonomy: enums cerrados (RunEvent, DropReason, RunStatus)
2. Drop book: DropLedger + drop_profile() como único punto de salida
3. Invariant funnel: FunnelTracker con verificación contable
4. State machine: RunStatus con transiciones definidas
5. Events table: discovery_run_events para auditoría
6. Alerts: budget thresholds con logging
7. Context: structlog.contextvars para trazabilidad
"""
from enum import Enum
from typing import Any


class RunEvent(str, Enum):
    """Taxonomía cerrada de eventos de corrida."""

    RUN_STARTED = "run.started"
    RUN_FINISHED = "run.finished"
    RUN_ABORTED = "run.aborted"

    PLAN_BUILT = "plan.built"
    PLAN_EXECUTED = "plan.executed"

    SOURCE_CALLED = "source.called"
    SOURCE_SUCCEEDED = "source.succeeded"
    SOURCE_FAILED = "source.failed"

    PROFILE_DISCOVERED = "profile.discovered"
    PROFILE_DEDUPED = "profile.deduped"
    PROFILE_DROPPED = "profile.dropped"

    ENRICH_REQUESTED = "enrich.requested"
    ENRICH_SUCCEEDED = "enrich.succeeded"
    ENRICH_FAILED = "enrich.failed"

    SCORE_COMPUTED = "score.computed"
    SCORE_FALLBACK_USED = "score.fallback_used"

    CANDIDATE_PERSISTED = "candidate.persisted"
    CANDIDATE_SAVED_AS_INFLUENCER = "candidate.saved_as_influencer"

    BUDGET_RESERVED = "budget.reserved"
    BUDGET_EXHAUSTED = "budget.exhausted"
    BUDGET_THRESHOLD_HIT = "budget.threshold_hit"

    CONTRACT_VIOLATION = "contract.violation"


class DropReason(str, Enum):
    """Razones cerradas para descarte de perfiles."""

    MISSING_FOLLOWER_FIELD = "MISSING_FOLLOWER_FIELD"
    ENRICHMENT_FAILED = "ENRICHMENT_FAILED"
    ENRICHMENT_SKIPPED_BUDGET = "ENRICHMENT_SKIPPED_BUDGET"
    BELOW_MIN_FOLLOWERS = "BELOW_MIN_FOLLOWERS"
    ABOVE_MAX_FOLLOWERS = "ABOVE_MAX_FOLLOWERS"
    GEO_MISMATCH = "GEO_MISMATCH"
    NICHE_MISMATCH = "NICHE_MISMATCH"
    EXCLUDED_STORE = "EXCLUDED_STORE"
    EXCLUDED_FOUNDATION = "EXCLUDED_FOUNDATION"
    EXCLUDED_BRAND_OWN = "EXCLUDED_BRAND_OWN"
    FRAUD_SIGNAL = "FRAUD_SIGNAL"
    DUPLICATE_HANDLE = "DUPLICATE_HANDLE"
    PRIVATE_ACCOUNT = "PRIVATE_ACCOUNT"
    SCORE_BELOW_THRESHOLD = "SCORE_BELOW_THRESHOLD"
    BOT_PATTERN = "BOT_PATTERN"
    POLITICAL_CONTENT = "POLITICAL_CONTENT"


class RunStatus(str, Enum):
    """Estados de corrida con semántica precisa."""

    QUEUED = "queued"
    RUNNING = "running"
    DELIVERED = "delivered"
    DEGRADED = "degraded"
    EMPTY = "empty"
    INCONSISTENT = "inconsistent"
    ABORTED_BUDGET = "aborted_budget"
    FAILED = "failed"


class DropLedger:
    """Libro de descarte con contador por razón."""

    def __init__(self):
        self._counts: dict[DropReason, int] = {r: 0 for r in DropReason}

    def record(self, reason: DropReason) -> None:
        self._counts[reason] += 1

    def dominant(self) -> DropReason | None:
        if not any(self._counts.values()):
            return None
        return max(self._counts.items(), key=lambda x: x[1])[0]

    def get_count(self, reason: DropReason) -> int:
        return self._counts[reason]

    def total(self) -> int:
        return sum(self._counts.values())

    def as_dict(self) -> dict[str, int]:
        return {r.value: c for r, c in self._counts.items() if c > 0}


def drop_profile(
    username: str,
    reason: DropReason,
    stage: str,
    detail: dict[str, Any] | None = None,
    ledger: DropLedger | None = None,
) -> None:
    """Único punto de salida de un perfil del pipeline.

    Registra en ledger, emite evento estructurado, y retorna.
    """
    import structlog

    logger = structlog.get_logger()
    if ledger is not None:
        ledger.record(reason)
    logger.info(
        RunEvent.PROFILE_DROPPED.value,
        username=username,
        reason=reason.value,
        stage=stage,
        **(detail or {}),
    )


class FunnelTracker:
    """Embudo monótono con invariante contable."""

    def __init__(self):
        self.discovered = 0
        self.deduped = 0
        self.prefiltered = 0
        self.enriched = 0
        self.scored = 0
        self.delivered = 0
        self.drops: dict[str, int] = {}

    def record_drop(self, stage: str, count: int = 1) -> None:
        self.drops[stage] = self.drops.get(stage, 0) + count

    def assert_invariant(
        self, stage: str, before: int, after: int, ledger: DropLedger | None = None
    ) -> None:
        drops_in_stage = self.drops.get(stage, 0)
        expected_after = before - drops_in_stage
        if after != expected_after:
            raise InconsistentFunnelError(
                f"Funnel invariant violated at stage '{stage}': "
                f"in={before}, out={after}, drops={drops_in_stage}, expected_out={expected_after}"
            )

    def summary(self) -> dict[str, Any]:
        return {
            "discovered": self.discovered,
            "deduped": self.deduped,
            "prefiltered": self.prefiltered,
            "enriched": self.enriched,
            "scored": self.scored,
            "delivered": self.delivered,
            "drops": dict(self.drops),
        }


class InconsistentFunnelError(Exception):
    """El embudo no cuadra: la suma de salidas + drops no coincide con entradas."""

    pass


def determine_final_status(
    total_candidates: int,
    funnel_invariant_ok: bool,
    step3_degraded: bool,
    budget_aborted: bool,
    has_exception: bool,
) -> RunStatus:
    """Máquina de transición de estados de corrida."""
    if has_exception:
        return RunStatus.FAILED
    if budget_aborted:
        return RunStatus.ABORTED_BUDGET
    if total_candidates == 0 and not funnel_invariant_ok:
        return RunStatus.INCONSISTENT
    if total_candidates == 0:
        return RunStatus.EMPTY
    if step3_degraded:
        return RunStatus.DEGRADED
    return RunStatus.DELIVERED


def build_user_message(ledger: DropLedger, total_profiles: int) -> str:
    """Deriva mensaje al usuario desde el libro de descarte."""
    dominant = ledger.dominant()
    if dominant is None:
        return "No se encontraron candidatos."

    count = ledger.get_count(dominant)
    pct = (count / total_profiles * 100) if total_profiles > 0 else 0

    messages: dict[DropReason, str] = {
        DropReason.MISSING_FOLLOWER_FIELD: (
            f"El {pct:.0f}% de los perfiles llegó sin campo de seguidores. "
            "El proveedor devolvió datos incompletos. NO es saldo insuficiente."
        ),
        DropReason.ENRICHMENT_FAILED: (
            f"El {pct:.0f}% de los perfiles falló al enriquecer. "
            "Probablemente saldo agotado. Recargar y reintentar."
        ),
        DropReason.ENRICHMENT_SKIPPED_BUDGET: (
            f"El {pct:.0f}% de los perfiles se saltó por presupuesto. "
            "Saldo agotado durante enrichment."
        ),
        DropReason.BELOW_MIN_FOLLOWERS: (
            f"El {pct:.0f}% de los perfiles no alcanzó el mínimo de seguidores."
        ),
        DropReason.ABOVE_MAX_FOLLOWERS: (
            f"El {pct:.0f}% de los perfiles superó el máximo de seguidores."
        ),
        DropReason.GEO_MISMATCH: (
            f"El {pct:.0f}% de los perfiles no cumplió el criterio geográfico."
        ),
        DropReason.NICHE_MISMATCH: (
            f"El {pct:.0f}% de los perfiles no matcheó con el nicho."
        ),
        DropReason.EXCLUDED_STORE: (
            f"El {pct:.0f}% de los perfiles fue excluido por ser tienda."
        ),
        DropReason.EXCLUDED_FOUNDATION: (
            f"El {pct:.0f}% de los perfiles fue excluido por ser fundación."
        ),
        DropReason.EXCLUDED_BRAND_OWN: (
            f"El {pct:.0f}% de los perfiles fue excluido por ser cuenta propia de la marca."
        ),
        DropReason.FRAUD_SIGNAL: (
            f"El {pct:.0f}% de los perfiles fue excluido por señal de fraude."
        ),
        DropReason.BOT_PATTERN: (
            f"El {pct:.0f}% de los perfiles fue excluido por patrón de bot."
        ),
        DropReason.PRIVATE_ACCOUNT: (
            f"El {pct:.0f}% de los perfiles era de cuenta privada."
        ),
        DropReason.SCORE_BELOW_THRESHOLD: (
            f"El {pct:.0f}% de los perfiles no alcanzó el score mínimo."
        ),
        DropReason.POLITICAL_CONTENT: (
            f"El {pct:.0f}% de los perfiles fue excluido por contenido político."
        ),
        DropReason.DUPLICATE_HANDLE: (
            f"El {pct:.0f}% de los perfiles era duplicado."
        ),
    }

    return messages.get(
        dominant, f"No se encontraron candidatos. Causa principal: {dominant.value}."
    )
