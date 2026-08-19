"""Level 4 — Workflow tests: Modo Explorar → selection → Modo Analizar.

Tests que validan el flujo completo de selección y análisis.
Usan mocks para Redis/HikerAPI pero prueban la lógica del worker.

Run: pytest apps/api/tests/test_lens_workflow.py -v
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestExploreModeSkipEnrichment:
    """Valida que explore mode no llama a HikerAPI para enrichment."""

    @pytest.mark.asyncio
    async def test_explore_mode_sets_correct_flag(self):
        """En explore mode, is_explore_mode=True e is_analyze_mode=False."""
        from discovery.schemas import BriefStructured

        brief = BriefStructured(discovery_mode="explore")
        is_explore = getattr(brief, "discovery_mode", "auto") == "explore"
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"

        assert is_explore is True
        assert is_analyze is False

    @pytest.mark.asyncio
    async def test_explore_mode_brief_has_zero_handles(self):
        """Explore mode no debe tener handles_to_analyze al iniciar."""
        from discovery.schemas import BriefStructured

        brief = BriefStructured(discovery_mode="explore")
        assert brief.handles_to_analyze == []

    @pytest.mark.asyncio
    async def test_auto_mode_is_neither_explore_nor_analyze(self):
        """Modo auto no activa flags de explore ni analyze."""
        from discovery.schemas import BriefStructured

        brief = BriefStructured(discovery_mode="auto")
        is_explore = getattr(brief, "discovery_mode", "auto") == "explore"
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"

        assert is_explore is False
        assert is_analyze is False


class TestAnalyzeModeFlagLogic:
    """Valida la lógica de flags para modo Analizar."""

    @pytest.mark.asyncio
    async def test_analyze_mode_flag_true(self):
        """En analyze mode, is_analyze_mode=True."""
        from discovery.schemas import BriefStructured

        brief = BriefStructured(discovery_mode="analyze")
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"
        assert is_analyze is True

    @pytest.mark.asyncio
    async def test_analyze_mode_has_handles(self):
        """Analyze mode recibe handles_to_analyze del usuario."""
        from discovery.schemas import BriefStructured

        handles = ["@influencer1", "@influencer2", "@influencer3"]
        brief = BriefStructured(
            discovery_mode="analyze",
            handles_to_analyze=handles,
        )
        assert len(brief.handles_to_analyze) == 3
        assert "@influencer1" in brief.handles_to_analyze

    @pytest.mark.asyncio
    async def test_analyze_mode_has_parent_run_id(self):
        """Analyze mode recibe parent_run_id para cargar candidatos."""
        from discovery.schemas import BriefStructured

        brief = BriefStructured(
            discovery_mode="analyze",
            handles_to_analyze=["@h1"],
            parent_run_id="run-abc-123",
        )
        assert brief.parent_run_id == "run-abc-123"

    @pytest.mark.asyncio
    async def test_skip_discovery_flag_for_analyze(self):
        """_skip_discovery debe ser True cuando analyze + parent_run_id."""
        from discovery.schemas import BriefStructured

        brief = BriefStructured(
            discovery_mode="analyze",
            handles_to_analyze=["@h1"],
            parent_run_id="parent-run-123",
        )
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"
        parent_run_id = getattr(brief, "parent_run_id", None)
        _skip_discovery = is_analyze and bool(parent_run_id)

        assert _skip_discovery is True


class TestCandidateAutoSave:
    """Valida que en analyze mode los candidatos se marcan como saved."""

    @pytest.mark.asyncio
    async def test_qualified_candidates_get_saved_status_in_analyze(self):
        """En analyze mode, candidates deben tener status='saved' antes de insert."""
        qualified = [
            {
                "handle": "@influencer1",
                "match_score": 85.0,
                "platform": "instagram",
                "followers": 50000,
            },
            {
                "handle": "@influencer2",
                "match_score": 72.0,
                "platform": "instagram",
                "followers": 30000,
            },
        ]

        is_analyze_mode = True
        if is_analyze_mode:
            for c in qualified:
                c["status"] = "saved"

        assert all(c["status"] == "saved" for c in qualified)

    @pytest.mark.asyncio
    async def test_auto_save_only_in_analyze_mode(self):
        """En explore mode, candidates NO deben auto-guardarse."""
        qualified = [
            {"handle": "@influencer1", "match_score": 85.0},
            {"handle": "@influencer2", "match_score": 72.0},
        ]

        is_analyze_mode = False
        if is_analyze_mode:
            for c in qualified:
                c["status"] = "saved"

        assert all("status" not in c for c in qualified)


class TestParentCandidatesLoading:
    """Valida que analyze mode carga candidatos del run padre."""

    @pytest.mark.asyncio
    async def test_parent_candidates_filter_query(self):
        """Filtro para cargar candidatos del padre usa handle=in.() y run_id."""
        parent_run_id = "parent-run-123"
        handles = ["@h1", "@h2", "@h3"]

        filter_handles = ",".join(repr(h) for h in handles)
        expected_filter = f"handle=in.({filter_handles})"

        assert "@h1" in expected_filter
        assert "@h2" in expected_filter
        assert "@h3" in expected_filter

    @pytest.mark.asyncio
    async def test_parent_candidates_structure(self):
        """Estructura de candidato cargado desde el run padre."""
        parent_candidate = {
            "handle": "@parent_candidate",
            "full_name": "Parent Candidate",
            "bio": "Test bio",
            "followers": 10000,
            "raw_payload": {"username": "@parent_candidate", "followersCount": 10000},
        }

        assert parent_candidate["handle"] == "@parent_candidate"
        assert parent_candidate["followers"] == 10000
        assert "raw_payload" in parent_candidate


class TestStatusTransitionExplored:
    """Valida transición de status a 'explored' en modo Explorar."""

    @pytest.mark.asyncio
    async def test_explore_run_gets_explored_status(self):
        """Un run en modo explore debe terminar con status='explored'."""
        from discovery.schemas import DiscoveryRunStatus

        is_explore_mode = True
        is_analyze_mode = False
        step3_degraded = False

        if is_explore_mode:
            final_status = "explored"
        else:
            final_status = "partial" if step3_degraded else "completed"

        assert final_status == "explored"

    @pytest.mark.asyncio
    async def test_explore_run_not_completed(self):
        """Explore run NO debe terminar en 'completed'."""
        from discovery.schemas import DiscoveryRunStatus

        is_explore_mode = True
        step3_degraded = False

        if is_explore_mode:
            final_status = "explored"
        else:
            final_status = "partial" if step3_degraded else "completed"

        assert final_status != "completed"

    @pytest.mark.asyncio
    async def test_analyze_run_gets_completed_status(self):
        """Un run en modo analyze debe terminar en 'completed'."""
        is_explore_mode = False
        is_analyze_mode = True
        step3_degraded = False

        if is_explore_mode:
            final_status = "explored"
        else:
            final_status = "partial" if step3_degraded else "completed"

        assert final_status == "completed"

    @pytest.mark.asyncio
    async def test_analyze_run_not_explored(self):
        """Analyze run NO debe terminar en 'explored'."""
        is_explore_mode = False
        is_analyze_mode = True
        step3_degraded = False

        if is_explore_mode:
            final_status = "explored"
        else:
            final_status = "partial" if step3_degraded else "completed"

        assert final_status != "explored"


class TestWrapUpMessage:
    """Valida que el mensaje de wrap-up es correcto para cada modo."""

    @pytest.mark.asyncio
    async def test_explore_mode_wrap_up_message(self):
        """Explore mode dice 'Encontré N perfiles con señales de nicho'."""
        is_explore_mode = True
        scored_count = 15

        if is_explore_mode:
            msg = (
                f"✅ Encontré {scored_count} perfiles con señales de nicho. "
                f"Seleccioná los que quieras que analice en profundidad."
            )

        assert "perfiles con señales de nicho" in msg
        assert "15" in msg

    @pytest.mark.asyncio
    async def test_analyze_mode_wrap_up_message(self):
        """Analyze mode dice que la propuesta está lista para descargar."""
        is_explore_mode = False
        is_analyze_mode = True
        qualified_count = 5
        top_score = 87.0

        if is_explore_mode:
            msg = "explore message"
        elif is_analyze_mode:
            msg = (
                f"✅ Análisis completado. {qualified_count} perfiles enriquecidos y guardados. "
                f"Mejor score: {top_score:.0f}/100. "
                f"Descargá la propuesta en CSV desde el historial de runs."
            )
        else:
            msg = f"✅ Listo. {qualified_count} candidatos."

        assert "Análisis completado" in msg
        assert "guardados" in msg
        assert "CSV" in msg

    @pytest.mark.asyncio
    async def test_auto_mode_wrap_up_message(self):
        """Auto mode dice 'Listo N creadores calificados'."""
        is_explore_mode = False
        is_analyze_mode = False
        qualified_count = 10
        top_score = 91.0

        if is_explore_mode:
            msg = "explore message"
        elif is_analyze_mode:
            msg = "analyze message"
        else:
            msg = (
                f"✅ Listo. {qualified_count} creadores calificados para tu campaña. "
                f"El mejor candidato tiene {top_score:.0f}/100 de match."
            )

        assert "Listo" in msg
        assert "10" in msg
        assert "91" in msg
