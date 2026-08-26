"""Parity test: RunStatus (worker) ⊆ DiscoveryRunStatus (API).

Si el worker emite un estado que el API no conoce, el GET /runs/{id} devuelve
HTTP 500 porque Pydantic no puede deserializar el valor del enum de Postgres.

Este test falla en CI antes de que llegue a producción, protegiendo contra
regresiones como la de C-0/C-1 (fixes 35.9-35.10 del Hito 35).

Ref: docs/FIXES_FRONTEND_LENS_C0-C2_27-08-26.md (Issue C-1)
"""

from discovery.schemas import DiscoveryRunStatus
from shared_core.observability import RunStatus


def test_run_status_is_subset_of_api_enum():
    """RunStatus (worker) ⊆ DiscoveryRunStatus (API)."""
    worker_states = {s.value for s in RunStatus}
    api_states = {s.value for s in DiscoveryRunStatus}

    missing = worker_states - api_states
    assert not missing, (
        f"Estados del worker sin cobertura en DiscoveryRunStatus (API): {missing}. "
        f"Worker: {worker_states} | API: {api_states}"
    )
