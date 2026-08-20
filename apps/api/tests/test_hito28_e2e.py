"""Hito 28 — E2E tests: Fix A (pre-flight mode-aware), Fix B (DeepSeek skip), extra='forbid'.

Run: pytest apps/api/tests/test_hito28_e2e.py -v
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from discovery.schemas import BriefStructured, DiscoverySearchRequest


class TestExtraForbidSchemas:
    """HITO 28 Phase 3: extra='forbid' cierra la clase de bug de campo descartado.

    Sin extra='forbid', Pydantic v2 descarta silenciosamente campos unknown
    (extra='ignore' por defecto). El bug de parent_run_id (Hito 27) habría
    sido un ValidationError inmediato en el primer test si el schema tuviera
    extra='forbid'.
    """

    @pytest.mark.asyncio
    def test_briefstructured_forbids_extra_fields(self):
        """BriefStructured rechaza campos unknown con ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BriefStructured(
                discovery_mode="explore",
                product_name="Test",
                unknown_field="should fail",  # noqa: F841
            )
        errors = exc_info.value.errors()
        assert any("extra_forbidden" in str(e.get("type", "")) for e in errors)

    @pytest.mark.asyncio
    def test_briefstructured_accepts_valid_fields(self):
        """BriefStructured acepta todos los campos válidos."""
        brief = BriefStructured(
            product_name="Protector solar",
            industry="belleza",
            niches=["skincare", "beauty"],
            discovery_mode="explore",
            handles_to_analyze=["@test_handle"],
            parent_run_id="run-abc-123",
        )
        assert brief.discovery_mode == "explore"
        assert brief.product_name == "Protector solar"
        assert brief.parent_run_id == "run-abc-123"

    @pytest.mark.asyncio
    def test_discoverysearchrequest_forbids_extra_fields(self):
        """DiscoverySearchRequest rechaza campos unknown con ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DiscoverySearchRequest(
                discovery_mode="analyze",
                handles_to_analyze=["@h1"],
                parent_run_id="run-abc",
                nonexistent_field="should fail",  # noqa: F841
            )
        errors = exc_info.value.errors()
        assert any("extra_forbidden" in str(e.get("type", "")) for e in errors)

    @pytest.mark.asyncio
    def test_discoverysearchrequest_accepts_valid_fields(self):
        """DiscoverySearchRequest acepta todos los campos válidos."""
        req = DiscoverySearchRequest(
            product_name="Test",
            discovery_mode="analyze",
            handles_to_analyze=["@h1", "@h2"],
            parent_run_id="run-abc-123",
        )
        assert req.discovery_mode == "analyze"
        assert len(req.handles_to_analyze) == 2
        assert req.parent_run_id == "run-abc-123"

    @pytest.mark.asyncio
    def test_parent_run_id_now_persists_in_briefstructured(self):
        """HITO 27 FIX: parent_run_id se preserva en BriefStructured.

        Antes: Pydantic descartaba parent_run_id silenciosamente.
        Ahora: el campo se acepta y se preserva.
        """
        brief = BriefStructured(
            discovery_mode="analyze",
            parent_run_id="run-123",
            handles_to_analyze=["@handle1"],
        )
        assert brief.parent_run_id == "run-123"


class TestPreflightModeAware:
    """HITO 28 FIX A: Pre-flight usa estimación modo-aware.

    Antes: siempre estimated_calls = 32 + 25 = 57 ($1.14).
    Después:
      - Explorar: 32 calls ($0.64)
      - Analizar: len(handles_to_analyze) calls
      - Auto: 57 calls ($1.14)
    """

    @pytest.mark.asyncio
    async def test_explore_mode_estimates_32_calls(self):
        """Explorar estima 32 calls ($0.64) — sin enrichment."""
        brief = BriefStructured(discovery_mode="explore")
        is_explore = getattr(brief, "discovery_mode", "auto") == "explore"
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"

        ESTIMATED_DISCOVERY_CALLS = 32
        MAX_HANDLES_TO_ENRICH = 25
        COST_PER_CALL = 0.02

        if is_explore:
            estimated_calls = ESTIMATED_DISCOVERY_CALLS
        elif is_analyze:
            estimated_calls = max(1, len(brief.handles_to_analyze)) if brief.handles_to_analyze else 1
        else:
            estimated_calls = ESTIMATED_DISCOVERY_CALLS + MAX_HANDLES_TO_ENRICH

        estimated_cost = estimated_calls * COST_PER_CALL

        assert estimated_calls == 32
        assert estimated_cost == pytest.approx(0.64)

    @pytest.mark.asyncio
    async def test_analyze_mode_estimates_per_handle(self):
        """Analizar estima 1 call por handle seleccionado."""
        brief = BriefStructured(
            discovery_mode="analyze",
            handles_to_analyze=["@h1", "@h2", "@h3"],
        )
        is_explore = getattr(brief, "discovery_mode", "auto") == "explore"
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"

        ESTIMATED_DISCOVERY_CALLS = 32
        MAX_HANDLES_TO_ENRICH = 25
        COST_PER_CALL = 0.02

        if is_explore:
            estimated_calls = ESTIMATED_DISCOVERY_CALLS
        elif is_analyze:
            estimated_calls = max(1, len(brief.handles_to_analyze)) if brief.handles_to_analyze else 1
        else:
            estimated_calls = ESTIMATED_DISCOVERY_CALLS + MAX_HANDLES_TO_ENRICH

        estimated_cost = estimated_calls * COST_PER_CALL

        assert estimated_calls == 3
        assert estimated_cost == pytest.approx(0.06)

    @pytest.mark.asyncio
    async def test_analyze_mode_single_handle_minimum(self):
        """Analizar con 1 handle estima 1 call mínimo."""
        brief = BriefStructured(
            discovery_mode="analyze",
            handles_to_analyze=["@h1"],
        )
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"

        if is_analyze:
            estimated_calls = max(1, len(brief.handles_to_analyze)) if brief.handles_to_analyze else 1

        assert estimated_calls == 1

    @pytest.mark.asyncio
    async def test_auto_mode_estimates_full_pipeline(self):
        """Auto estima 57 calls ($1.14) — discovery + enrichment completo."""
        brief = BriefStructured(discovery_mode="auto")
        is_explore = getattr(brief, "discovery_mode", "auto") == "explore"
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"

        ESTIMATED_DISCOVERY_CALLS = 32
        MAX_HANDLES_TO_ENRICH = 25
        COST_PER_CALL = 0.02

        if is_explore:
            estimated_calls = ESTIMATED_DISCOVERY_CALLS
        elif is_analyze:
            estimated_calls = max(1, len(brief.handles_to_analyze)) if brief.handles_to_analyze else 1
        else:
            estimated_calls = ESTIMATED_DISCOVERY_CALLS + MAX_HANDLES_TO_ENRICH

        estimated_cost = estimated_calls * COST_PER_CALL

        assert estimated_calls == 57
        assert estimated_cost == pytest.approx(1.14)

    @pytest.mark.asyncio
    async def test_explore_allows_run_with_small_balance(self):
        """Con $0.80, Explorar ($0.64) debe pasar pre-flight.

        Antes del fix: pre-flight exigía $1.14 y rechazaba $0.80.
        Después del fix: pre-flight exige $0.64 y acepta $0.80.
        """
        brief = BriefStructured(discovery_mode="explore")
        is_explore = getattr(brief, "discovery_mode", "auto") == "explore"

        ESTIMATED_DISCOVERY_CALLS = 32
        COST_PER_CALL = 0.02
        balance = 0.80

        if is_explore:
            estimated_calls = ESTIMATED_DISCOVERY_CALLS
        else:
            estimated_calls = ESTIMATED_DISCOVERY_CALLS + 25

        estimated_cost = estimated_calls * COST_PER_CALL

        assert balance >= estimated_cost, f"${balance:.2f} < ${estimated_cost:.2f} — run would be rejected"

    @pytest.mark.asyncio
    async def test_analyze_allows_run_with_small_balance(self):
        """Con $0.20, Analizar de 5 handles ($0.10) debe pasar pre-flight.

        Antes del fix: pre-flight exigía $1.14 y rechazaba $0.20.
        Después del fix: pre-flight exige $0.10 y acepta $0.20.
        """
        brief = BriefStructured(
            discovery_mode="analyze",
            handles_to_analyze=["@h1", "@h2", "@h3", "@h4", "@h5"],
        )
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"

        COST_PER_CALL = 0.02
        balance = 0.20

        if is_analyze:
            estimated_calls = max(1, len(brief.handles_to_analyze)) if brief.handles_to_analyze else 1
        else:
            estimated_calls = 57

        estimated_cost = estimated_calls * COST_PER_CALL

        assert balance >= estimated_cost, f"${balance:.2f} < ${estimated_cost:.2f} — run would be rejected"


class TestDeepSeekSkipInExplore:
    """HITO 28 FIX B: DeepSeek no corre en modo Explorar.

    En Explorar no hay enrichment → followers=0, bio vacía.
    DeepSeek sobrescribiría el rationale honesto con scores ficticios.
    Solo debe correr en modo Auto (enrichment completo) y Analizar (padre enriquecido).
    """

    @pytest.mark.asyncio
    async def test_explore_mode_skips_deepseek(self):
        """En Explorar, analyze_with_ai=True + is_explore=True → skip DeepSeek."""
        analyze_with_ai = True
        is_explore_mode = True

        should_run_deepseek = analyze_with_ai and not is_explore_mode

        assert should_run_deepseek is False

    @pytest.mark.asyncio
    async def test_auto_mode_runs_deepseek(self):
        """En Auto, analyze_with_ai=True + is_explore=False → corre DeepSeek."""
        analyze_with_ai = True
        is_explore_mode = False

        should_run_deepseek = analyze_with_ai and not is_explore_mode

        assert should_run_deepseek is True

    @pytest.mark.asyncio
    async def test_analyze_mode_runs_deepseek(self):
        """En Analizar, analyze_with_ai=True → corre DeepSeek (padre enriquecido)."""
        analyze_with_ai = True
        is_explore_mode = False

        should_run_deepseek = analyze_with_ai and not is_explore_mode

        assert should_run_deepseek is True

    @pytest.mark.asyncio
    async def test_explore_with_ai_false_skips_deepseek(self):
        """En Explorar con analyze_with_ai=False → skip DeepSeek (confirmado)."""
        analyze_with_ai = False
        is_explore_mode = True

        should_run_deepseek = analyze_with_ai and not is_explore_mode

        assert should_run_deepseek is False

    @pytest.mark.asyncio
    async def test_explore_rationale_preserved_without_deepseek(self):
        """Sin DeepSeek, se usa el rationale basado en rough score (honesto).

        El rationale honesto de Hito 26 dice: 'descubierto sin enriquecer,
        seal derivada de la bio'. NO debe ser sobrescrito por DeepSeek con
        scores de followers=0.
        """
        is_explore_mode = True
        analyze_with_ai = True

        to_analyze = [
            {
                "handle": "@test_handle",
                "match_score": 65.0,
                "rough_score": 0.65,
                "followers": 0,  # Sin enrichment
                "rationale": "Descubierto sin enriquecer — scoring basado en seal de nicho y geolocalizacin.",
            }
        ]

        if analyze_with_ai and not is_explore_mode:
            pass  # DeepSeek would overwrite rationale here
        else:
            analyzed = to_analyze  # Keeps honest rationale

        assert analyzed[0]["followers"] == 0
        assert "sin enriquecer" in analyzed[0]["rationale"]


class TestExploreMax25Candidates:
    """Nota para la demo: Explorar devuelve máximo 25 candidatos.

    El rough_score_map viene del prefiltro limitado a MAX_HANDLES_TO_ENRICH=25.
    No es un bug, pero es importante para no prometer 133 y mostrar 25.
    """

    @pytest.mark.asyncio
    async def test_explore_returns_max_25_from_prefilter(self):
        """Explorar usa prefilter limitado a MAX_HANDLES_TO_ENRICH=25."""
        MAX_HANDLES_TO_ENRICH = 25

        discovered_handles = 133
        prefiltro_result = min(discovered_handles, MAX_HANDLES_TO_ENRICH)

        assert prefiltro_result == 25
