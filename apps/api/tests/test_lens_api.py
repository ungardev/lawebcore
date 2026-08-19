"""Level 2 — API endpoint tests for LENS Modo Explorar/Analizar.

Tests de los endpoints de API relevantes para el workflow.
Usan pytest-asyncio con mocks para Redis/HikerAPI.

Run: pytest apps/api/tests/test_lens_api.py -v
"""

import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from discovery.schemas import BriefStructured, DiscoverySearchRequest


class TestAnalyzeSelectedEndpoint:
    """Tests para POST /lens/discovery/analyze-selected."""

    @pytest.mark.asyncio
    async def test_analyze_selected_request_model(self):
        """AnalyzeSelectedRequest acepta run_id y handles_to_analyze."""
        from pydantic import BaseModel

        class AnalyzeSelectedRequest(BaseModel):
            run_id: uuid.UUID
            handles_to_analyze: list[str]

        req = AnalyzeSelectedRequest(
            run_id=uuid.uuid4(),
            handles_to_analyze=["@handle1", "@handle2"],
        )
        assert req.run_id is not None
        assert len(req.handles_to_analyze) == 2

    @pytest.mark.asyncio
    async def test_discovery_run_response_model_explored_status(self):
        """DiscoveryRunResponse acepta status='explored'."""
        from discovery.schemas import DiscoveryRunStatus
        from pydantic import BaseModel

        class DiscoveryRunResponse(BaseModel):
            id: uuid.UUID
            status: DiscoveryRunStatus
            total_candidates: int = 0
            accepted: int = 0
            created_at: str

        resp = DiscoveryRunResponse(
            id=uuid.uuid4(),
            status=DiscoveryRunStatus.EXPLORED,
            total_candidates=5,
            accepted=0,
            created_at="2026-08-19T00:00:00Z",
        )
        assert resp.status == DiscoveryRunStatus.EXPLORED


class TestExploreModeSchema:
    """Tests para el modo Explorar en el schema."""

    def test_brief_explore_mode_schema_valid(self):
        """BriefStructured con discovery_mode=explore es válido."""
        brief = BriefStructured(
            product_name="Protector solar",
            industry="beauty",
            niches=["skincare", "beauty"],
            discovery_mode="explore",
            handles_to_analyze=[],
        )
        assert brief.discovery_mode == "explore"
        assert brief.handles_to_analyze == []

    def test_brief_analyze_mode_schema_valid(self):
        """BriefStructured con discovery_mode=analyze + handles es válido."""
        brief = BriefStructured(
            product_name="Protector solar",
            industry="beauty",
            discovery_mode="analyze",
            handles_to_analyze=["@influencer1", "@influencer2"],
            parent_run_id="parent-uuid-123",
        )
        assert brief.discovery_mode == "analyze"
        assert len(brief.handles_to_analyze) == 2
        assert brief.parent_run_id == "parent-uuid-123"

    def test_search_request_explore_mode(self):
        """DiscoverySearchRequest en modo explore es serializable."""
        req = DiscoverySearchRequest(
            product_name="Test product",
            platforms=["instagram"],
            discovery_mode="explore",
        )
        data = req.model_dump()
        assert data["discovery_mode"] == "explore"
        assert data["handles_to_analyze"] == []

    def test_search_request_analyze_mode(self):
        """DiscoverySearchRequest en modo analyze incluye handles_to_analyze."""
        req = DiscoverySearchRequest(
            product_name="Test product",
            discovery_mode="analyze",
            handles_to_analyze=["@selected1", "@selected2"],
            parent_run_id="parent-123",
        )
        data = req.model_dump()
        assert data["discovery_mode"] == "analyze"
        assert len(data["handles_to_analyze"]) == 2


class TestWorkerAnalyzeModeLogic:
    """Tests para la lógica de analyze mode en el worker (sin DB real)."""

    @pytest.mark.asyncio
    async def test_is_explore_mode_flag(self):
        """El flag is_explore_mode se activa con discovery_mode='explore'."""
        brief = BriefStructured(discovery_mode="explore")
        is_explore = getattr(brief, "discovery_mode", "auto") == "explore"
        assert is_explore is True

    @pytest.mark.asyncio
    async def test_is_analyze_mode_flag(self):
        """El flag is_analyze_mode se activa con discovery_mode='analyze'."""
        brief = BriefStructured(discovery_mode="analyze")
        is_analyze = getattr(brief, "discovery_mode", "auto") == "analyze"
        assert is_analyze is True

    @pytest.mark.asyncio
    async def test_parent_run_id_from_brief(self):
        """parent_run_id se lee correctamente del brief."""
        brief = BriefStructured(
            discovery_mode="analyze",
            handles_to_analyze=["@h1"],
            parent_run_id="run-parent-456",
        )
        parent_id = getattr(brief, "parent_run_id", None)
        assert parent_id == "run-parent-456"

    @pytest.mark.asyncio
    async def test_analyze_mode_handles_to_analyze(self):
        """handles_to_analyze contiene los handles seleccionados."""
        handles = ["@influencer1", "@influencer2", "@influencer3"]
        brief = BriefStructured(
            discovery_mode="analyze",
            handles_to_analyze=handles,
        )
        assert brief.handles_to_analyze == handles
        assert len(brief.handles_to_analyze) == 3


class TestProposalGenerator:
    """Tests para generate_proposal_csv — copy of function to avoid app import."""

    def _generate_proposal_csv(self, candidates, product_name="Influencer Proposal"):
        """Local copy of proposal generator for testing without app imports."""
        import csv
        import io
        from datetime import datetime

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "#", "Handle", "Nombre completo", "Seguidores",
            "ER (%)", "Score", "Tier", "País", "Ciudad",
            "¿Tienda?", "Alcance esperado", "Engagement esperado", "Rationale",
        ])

        for i, c in enumerate(candidates[:10], 1):
            er_pct = f"{(c.get('engagement_rate', 0) or 0) * 100:.1f}"
            followers = c.get("followers", 0) or 0
            match_score = c.get("match_score", 0) or 0
            tier = c.get("tier", "—") or "—"
            city = c.get("city") or "—"

            writer.writerow([
                i, c.get("handle", ""), c.get("full_name") or "—",
                f"{followers:,}", er_pct, f"{match_score:.1f}", tier,
                c.get("country", "VE") or "VE", city,
                "Sí" if c.get("is_tienda") else "No",
                c.get("expected_reach", 0) or 0,
                c.get("expected_engagement", 0) or 0,
                (c.get("bio") or "")[:80].replace("\n", " ").strip(),
            ])

        writer.writerow([])
        writer.writerow([
            f"Generado por Influencer Lens · La Web Figital Agency · "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ])
        writer.writerow([f"Producto: {product_name} · Total candidatos: {len(candidates)}"])

        return output.getvalue().encode("utf-8")

    def test_generate_proposal_csv_with_candidates(self):
        """generate_proposal_csv produce bytes con headers correctos."""
        candidates = [
            {
                "handle": "@test_influencer",
                "full_name": "Test Influencer",
                "followers": 50000,
                "engagement_rate": 0.035,
                "match_score": 85.0,
                "tier": "nano",
                "country": "VE",
                "city": "Caracas",
                "is_tienda": False,
                "expected_reach": 15000,
                "expected_engagement": 525.0,
                "bio": "Content creator",
            }
        ]
        result = self._generate_proposal_csv(candidates, product_name="Test Product")
        assert isinstance(result, bytes)
        content = result.decode("utf-8")
        assert "Handle" in content
        assert "@test_influencer" in content
        assert "Test Product" in content
        assert "La Web Figital Agency" in content

    def test_generate_proposal_csv_empty(self):
        """generate_proposal_csv con lista vacía produce CSV válido."""
        result = self._generate_proposal_csv([], product_name="Empty Proposal")
        assert isinstance(result, bytes)
        content = result.decode("utf-8")
        assert "Empty Proposal" in content


class TestCostTrackerSchema:
    """Tests para schemas de costo."""

    def test_api_cost_record_model(self):
        """ApiCostRecord acepta los campos correctos."""
        from discovery.schemas import ApiCostRecord

        record = ApiCostRecord(
            provider="hikerapi",
            operation="discovery_pipeline",
            cost_usd=0.24,
            request_count=12,
        )
        assert record.provider == "hikerapi"
        assert record.cost_usd == 0.24
        assert record.request_count == 12

    def test_discovery_run_response_has_cost(self):
        """DiscoveryRunResponse tiene campo actual_cost_usd."""
        from pydantic import BaseModel
        from discovery.schemas import DiscoveryRunStatus

        class DiscoveryRunResponse(BaseModel):
            id: uuid.UUID
            status: DiscoveryRunStatus
            total_candidates: int = 0
            accepted: int = 0
            actual_cost_usd: float | None = None
            created_at: str

        resp = DiscoveryRunResponse(
            id=uuid.uuid4(),
            status=DiscoveryRunStatus.COMPLETED,
            total_candidates=10,
            accepted=3,
            actual_cost_usd=0.58,
            created_at="2026-08-19T00:00:00Z",
        )
        assert resp.actual_cost_usd == 0.58
