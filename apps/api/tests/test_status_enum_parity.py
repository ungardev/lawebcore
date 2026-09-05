"""Parity test: RunStatus (worker) ⊆ DiscoveryRunStatus (API) y FE ≡ BE.

Dos contratos protegidos aquí:

1. Worker → API: si el worker emite un estado que el API no conoce, el
   GET /runs/{id} devuelve HTTP 500 porque Pydantic no puede deserializar el
   valor del enum de Postgres.
   Ref: docs/FIXES_FRONTEND_LENS_C0-C2_27-08-26.md (Issue C-1)

2. Backend → Frontend: useRunPolling.ts decide cuándo detener el polling y
   cuándo fetchar candidatos con sets de estados hardcodeados. En el
   03-sep-2026 esos sets usaban estados legacy ('completed', 'partial',
   'explored', 'cancelled') que el backend JAMÁS emite — un run exitoso
   terminaba en 'delivered', el polling giraba infinito y la UI nunca
   mostraba candidatos (bugs B-FE-7/B-FE-15).
   Ref: docs/FIXES_HIKERAPI_CONTRACT_PRE_E2E_04-09-26.md
"""

import re
from pathlib import Path

from discovery.schemas import DiscoveryRunStatus
from shared_core.observability import RunStatus

_REPO_ROOT = Path(__file__).resolve().parents[3]
_POLLING_HOOK = _REPO_ROOT / "apps/web/src/features/lens/hooks/useRunPolling.ts"
_CONVERSATION_HOOK = (
    _REPO_ROOT / "apps/web/src/features/lens/hooks/useDiscoveryConversation.ts"
)


def test_run_status_is_subset_of_api_enum():
    """RunStatus (worker) ⊆ DiscoveryRunStatus (API)."""
    worker_states = {s.value for s in RunStatus}
    api_states = {s.value for s in DiscoveryRunStatus}

    missing = worker_states - api_states
    assert not missing, (
        f"Estados del worker sin cobertura en DiscoveryRunStatus (API): {missing}. "
        f"Worker: {worker_states} | API: {api_states}"
    )


def _extract_status_array(hook_src: str, constant_name: str) -> set[str]:
    m = re.search(rf"{constant_name}: DiscoveryRunStatus\[\] = \[([^\]]+)\]", hook_src)
    assert m, f"{constant_name} no encontrado en useRunPolling.ts"
    return set(re.findall(r"'([a-z_]+)'", m.group(1)))


def test_frontend_terminal_statuses_match_backend():
    """Los estados en que useRunPolling DETIENE el polling deben ser
    exactamente los estados terminales que RunStatus puede emitir."""
    hook_src = _POLLING_HOOK.read_text(encoding="utf-8")
    fe_terminal = _extract_status_array(hook_src, "TERMINAL_RUN_STATUSES")

    non_terminal = {"queued", "running"}
    be_terminal = {s.value for s in RunStatus} - non_terminal

    missing = be_terminal - fe_terminal
    extra = fe_terminal - be_terminal
    assert not missing and not extra, (
        f"Desalineación FE↔BE en estados terminales. "
        f"Backend emite y FE no detiene: {missing} | "
        f"FE detiene pero backend jamás emite: {extra}. "
        f"Source of truth: shared_core/observability.py::RunStatus"
    )


def test_frontend_candidate_fetch_statuses_are_valid():
    """Los estados en que useRunPolling fetchea candidatos deben existir en
    RunStatus (un estado inexistente = candidatos que jamás se muestran)."""
    hook_src = _POLLING_HOOK.read_text(encoding="utf-8")
    fe_fetch = _extract_status_array(hook_src, "CANDIDATE_RUN_STATUSES")

    be_all = {s.value for s in RunStatus}
    unknown = fe_fetch - be_all
    assert not unknown, (
        f"useRunPolling fetchea candidatos en estados que el backend jamás "
        f"emite: {unknown}. Estados válidos: {sorted(be_all)}"
    )
    assert "delivered" in fe_fetch, (
        "'delivered' es el estado de éxito del pipeline — sin él, un run "
        "exitoso nunca muestra candidatos en la UI."
    )


def test_conversation_hook_reuses_polling_constants():
    """loadConversation (recarga de página) debe usar las MISMASAS constantes
    de useRunPolling — duplicar literales es cómo nació el bug B-FE-7."""
    conv_src = _CONVERSATION_HOOK.read_text(encoding="utf-8")
    assert "CANDIDATE_RUN_STATUSES" in conv_src, (
        "useDiscoveryConversation.ts debe importar CANDIDATE_RUN_STATUSES de "
        "useRunPolling en lugar de comparar literales de estado a mano."
    )
    # Sin comparaciones legacy hardcodeadas
    for legacy in ("'completed'", "'partial'", "'explored'", "'cancelled'"):
        assert legacy not in conv_src, (
            f"Estado legacy {legacy} detectado en useDiscoveryConversation.ts — "
            f"el backend jamás lo emite. Usar las constantes de useRunPolling."
        )
