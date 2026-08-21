"""Hito 29 — E2E Anti-Regression Tests: extra="forbid" solo en frontera de entrada.

Run: pytest apps/api/tests/test_hito29_e2e_regression.py -v

OPUS 5 IDENTIFICÓ ESTA REGRESIÓN:
worker.py:324 hacía BriefStructured(**brief_parsed) donde brief_parsed
venía de DiscoverySearchRequest.model_dump() que incluye max_candidates.
BriefStructured NO tenía max_candidates y tenía extra="forbid" → ValidationError.
El run moría antes de la primera llamada HTTP.

REGLA (de Opus 5):
- "forbid" va en la FRONTERA DE ENTRADA (DiscoverySearchRequest)
- "ignore" va en deserialización de datos persistidos (BriefStructured)
"""

import uuid

import pytest
from pydantic import ValidationError

from discovery.schemas import BriefStructured, DiscoverySearchRequest


class TestH29SchemaRegression:
    """HITO 29: La regresión del Hito 28 была introduzcada por aplicar
    extra="forbid" a BriefStructured, que lee JSON persistido.

    La regla correcta: forbid en frontera de entrada, ignore en persistencia.
    """

    @pytest.mark.asyncio
    def test_full_round_trip_discovery_request_to_brief_structured(self):
        """HITO 29 FIX: DiscoverySearchRequest → model_dump() → BriefStructured.

        Este era el bug: model_dump() incluye max_candidates, pero
        BriefStructured no lo tenía → ValidationError.
        Ahora BriefStructured tiene max_candidates y extra="ignore" → funciona.
        """
        request = DiscoverySearchRequest(
            product_name="Purina Dog Chow",
            brand_id=uuid.uuid4(),
            industry="pet_care",
            niches=["perros", "mascotas"],
            hashtags=["#perros", "#mascotas"],
            max_candidates=20,
            discovery_mode="explore",
            handles_to_analyze=[],
            parent_run_id=None,
        )
        dumped = request.model_dump()
        brief = BriefStructured(**dumped)
        assert brief.product_name == "Purina Dog Chow"
        assert brief.max_candidates == 20
        assert brief.discovery_mode == "explore"

    @pytest.mark.asyncio
    def test_briefstructured_ignores_extra_fields_from_persistence(self):
        """HITO 29: BriefStructured con extra="ignore" ignora campos unknown.

        Esto simula un JSON guardado con campos que ya no existen en el schema.
        No debe fallar.
        """
        old_style_json = {
            "product_name": "Old Product",
            "brand_id": str(uuid.uuid4()),
            "max_candidates": 15,
            "obsolete_field": "this should be ignored",
            "another_old_field": 12345,
            "discovery_mode": "auto",
        }
        brief = BriefStructured(**old_style_json)
        assert brief.product_name == "Old Product"
        assert brief.max_candidates == 15

    @pytest.mark.asyncio
    def test_briefstructured_max_candidates_default_20(self):
        """HITO 29: max_candidates tiene default=20 si no está en el JSON."""
        minimal_json = {
            "product_name": "Test Product",
        }
        brief = BriefStructured(**minimal_json)
        assert brief.max_candidates == 20

    @pytest.mark.asyncio
    def test_briefstructured_max_candidates_respected_when_provided(self):
        """HITO 29: max_candidates se respeta si está en el JSON."""
        json_with_max = {
            "product_name": "Test Product",
            "max_candidates": 50,
        }
        brief = BriefStructured(**json_with_max)
        assert brief.max_candidates == 50

    @pytest.mark.asyncio
    def test_discovery_search_request_still_forbids_extra_fields(self):
        """HITO 28/29: DiscoverySearchRequest SÍ rechaza campos unknown.

        Esto verifica que extra="forbid" sigue funcionando en la frontera
        de entrada — donde debe estar.
        """
        with pytest.raises(ValidationError) as exc_info:
            DiscoverySearchRequest(
                product_name="Test",
                discovery_mode="explore",
                typo_field="this should fail",  # noqa: F841
            )
        errors = exc_info.value.errors()
        assert any("extra_forbidden" in str(e.get("type", "")) for e in errors)

    @pytest.mark.asyncio
    def test_briefstructured_all_valid_fields_work(self):
        """HITO 29: Todos los campos de BriefStructured funcionan."""
        brief = BriefStructured(
            product_name="Test Product",
            brand_id=uuid.uuid4(),
            max_candidates=30,
            brand_name="Test Brand",
            industry="test",
            niches=["niche1", "niche2"],
            hashtags=["#test"],
            discovery_mode="analyze",
            handles_to_analyze=["@handle1", "@handle2"],
            parent_run_id="run-123",
            analyze_with_ai=True,
            exclude_stores=True,
        )
        assert brief.max_candidates == 30
        assert brief.discovery_mode == "analyze"
        assert len(brief.handles_to_analyze) == 2
        assert brief.parent_run_id == "run-123"


class TestH29BackwardCompatibility:
    """HITO 29: Backward compat con los 48 runs históricos guardados.

    Cada run histórico tiene brief_parsed con campos que cambiaron entre versiones.
    BriefStructured con extra="ignore" debe aceptar todos sin fallar.
    """

    @pytest.mark.asyncio
    def test_historical_run_sample_1(self):
        """Simula un brief_parsed de un run histórico (formato antiguo)."""
        historical_brief = {
            "product_name": "Protector Solar",
            "brand_id": str(uuid.uuid4()),
            "max_candidates": 20,
            "discovery_mode": "auto",
            "analyze_with_ai": True,
            "parent_run_id": None,
            "handles_to_analyze": [],
        }
        brief = BriefStructured(**historical_brief)
        assert brief.product_name == "Protector Solar"

    @pytest.mark.asyncio
    def test_historical_run_sample_2_with_old_fields(self):
        """Simula brief_parsed con campos que ya no existen en el schema."""
        historical_with_old = {
            "product_name": "Shampoo Orgánico",
            "max_candidates": 15,
            "discovery_mode": "explore",
            "old_niche_field": "removed in v2",
            "legacy_param": 999,
        }
        brief = BriefStructured(**historical_with_old)
        assert brief.product_name == "Shampoo Orgánico"
        assert brief.max_candidates == 15
