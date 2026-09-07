"""Tests de resiliencia de infraestructura (04-sep-2026).

Dos incidentes reales de Railway:

1. `is_active=eq.true` llegaba a asyncpg como STRING 'true' → DataError
   "a boolean is required" → el cron diario fallaba a las 9 AM
   (j_failed=1 en el health del worker).
2. Un blip de Redis ("Connection reset by peer" del proxy de Railway)
   mató el proceso arq-worker completo: el loop de polling de arq no
   captura ConnectionError. La API seguía sirviendo /health → 200, así
   que Railway nunca reiniciaba el contenedor → discovery runs enqueued
   para siempre con cero workers vivos.
"""


import pytest
import redis.exceptions
from shared_core.railway_pg import RailwayPg


class TestFilterCoercion:
    """FIX 1: literales PostgREST true/false → bool real para asyncpg."""

    def setup_method(self):
        self.pg = RailwayPg()

    def test_eq_true_coerced_to_bool(self):
        where, params = self.pg._parse_filters(["is_active=eq.true"])
        assert "is_active = $1" in where
        assert params == [True]

    def test_eq_false_coerced_to_bool(self):
        where, params = self.pg._parse_filters(["is_active=eq.false"])
        assert params == [False]

    def test_in_with_bools_coerced(self):
        where, params = self.pg._parse_filters(["status.in.(true,false)"])
        assert "IN ($1,$2)" in where
        assert params == [True, False]

    def test_in_with_equals_form_coerced(self):
        """La forma `col=in.(...)` CON '=' (la que usa el modo Analizar)
        antes se trataba como igualdad contra el string "('a','b')" → 0 filas."""
        where, params = self.pg._parse_filters(["handle=in.('petfood_ve','vet_caracas')"])
        assert "handle IN ($1,$2)" in where
        assert params == ["petfood_ve", "vet_caracas"]

    def test_plain_string_values_untouched(self):
        where, params = self.pg._parse_filters(["role=eq.assistant", "status=eq.saved"])
        assert params == ["assistant", "saved"]

    def test_datetime_still_parsed(self):
        from datetime import datetime

        where, params = self.pg._parse_filters(["created_at=gte.2026-09-01T00:00:00Z"])
        assert isinstance(params[0], datetime)
        assert params[0].year == 2026 and params[0].month == 9 and params[0].day == 1

    def test_uuid_string_untouched(self):
        where, params = self.pg._parse_filters(["id=eq.550e8400-e29b-41d4-a716-446655440000"])
        assert params == ["550e8400-e29b-41d4-a716-446655440000"]

    def test_true_prefix_not_confused(self):
        """'true-story' como valor de texto NO debe coercerse a bool."""
        _, params = self.pg._parse_filters(["slug=eq.true-story"])
        assert params == ["true-story"]


class TestScheduledReportsCronHardening:
    """FIX 2: un fallo en el select no debe tumbar el health del worker."""

    async def test_db_error_swallowed(self, monkeypatch):
        from app.workers import worker as worker_mod

        async def _boom(**kwargs):
            raise RuntimeError("db down")

        monkeypatch.setattr(worker_mod.railway_pg, "select", _boom)
        await worker_mod.scheduled_reports_cron({})  # no raise

    async def test_happy_path_iterates(self, monkeypatch):
        from app.workers import worker as worker_mod

        async def _rows(**kwargs):
            return [{"id": "r1", "name": "Reporte Semanal"}]

        monkeypatch.setattr(worker_mod.railway_pg, "select", _rows)
        await worker_mod.scheduled_reports_cron({})  # no raise


class TestArqWorkerSupervisor:
    """FIX 3: un blip de Redis NO debe matar al worker para siempre.

    IMPORTANTE (lección de la v1): run_worker de arq es SYNC y maneja su
    propio event loop (worker.run() → loop.run_until_complete). El supervisor
    debe ser sync puro — la v1 lo envolvió en asyncio.run + await y reventó
    con "RuntimeError: This event loop is already running" AL ARRANCAR en
    Railway. Estos tests validan el contrato REAL: fake SYNC de run_worker.
    """

    def test_restarts_after_connection_blip(self, monkeypatch):
        import time as time_mod

        import arq.worker

        from app import main as app_main

        calls = {"n": 0}

        def fake_run_worker(settings):
            calls["n"] += 1
            if calls["n"] == 1:
                raise redis.exceptions.ConnectionError("Connection reset by peer")
            return None  # salida limpia en el segundo intento

        monkeypatch.setattr(arq.worker, "run_worker", fake_run_worker)
        monkeypatch.setattr(time_mod, "sleep", lambda s: None)
        app_main.arq_worker_supervised()
        assert calls["n"] == 2, "el supervisor debe relanzar tras el blip"

    def test_fatal_error_propagates(self, monkeypatch):
        import arq.worker

        from app import main as app_main

        def fake_run_worker(settings):
            raise ValueError("bug de código")

        monkeypatch.setattr(arq.worker, "run_worker", fake_run_worker)
        with pytest.raises(ValueError):
            app_main.arq_worker_supervised()

    def test_clean_exit_returns(self, monkeypatch):
        import arq.worker

        from app import main as app_main

        calls = {"n": 0}

        def fake_run_worker(settings):
            calls["n"] += 1
            return None

        monkeypatch.setattr(arq.worker, "run_worker", fake_run_worker)
        app_main.arq_worker_supervised()
        assert calls["n"] == 1

    def test_oserror_also_retried(self, monkeypatch):
        """OSError crudo (104 Connection reset by peer) también es transitorio."""
        import time as time_mod

        import arq.worker

        from app import main as app_main

        calls = {"n": 0}

        def fake_run_worker(settings):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError(104, "Connection reset by peer")
            return None

        monkeypatch.setattr(arq.worker, "run_worker", fake_run_worker)
        monkeypatch.setattr(time_mod, "sleep", lambda s: None)
        app_main.arq_worker_supervised()
        assert calls["n"] == 2
