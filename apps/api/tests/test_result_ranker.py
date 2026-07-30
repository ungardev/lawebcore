"""Tests for result_ranker — ICA and geo focus scoring."""

import pytest
from discovery.result_ranker import (
    calculate_ica,
    calculate_geo_foco_real,
)


class TestCalculateIca:
    """ICA must use real BUY_INTENT detection."""

    def test_ica_returns_zero_for_empty(self):
        assert calculate_ica([], 0) == 0.0
        assert calculate_ica(None, 1000) == 0.0

    def test_ica_detects_buy_intent(self):
        comments = [
            "donde lo puedo comprar",
            "tiene disponible en tienda",
            "me encanta este reels",
            "cuanto cuesta",
            "envio a provincia?",
            "que bonito",
        ]
        result = calculate_ica(comments, views=1000)
        assert result > 0, "Should detect buy intent in comments with price/link keywords"
        assert result <= 100, "ICA must be 0-100"

    def test_ica_zero_for_no_buy_intent(self):
        comments = ["me encanta", "que lindo", "wow fantastic"]
        result = calculate_ica(comments, views=1000)
        assert result == 0.0


class TestCalculateGeoFoco:
    """Geo-Foco Real for Venezuela validation."""

    def test_geo_foco_ve_signals(self):
        result = calculate_geo_foco_real(
            geotags=["Caracas, Venezuela", "Maracaibo"],
            captions=["Un día en Caracas 🇻🇪", "Probando producto"],
            profile_bio="Venezolano de Caracas",
        )
        assert result > 0.5, "Profile with VE signals should score > 0.5"

    def test_geo_foco_no_signals(self):
        result = calculate_geo_foco_real(
            geotags=[],
            captions=[],
            profile_bio="",
        )
        assert result == 0.5, "No signals should return neutral 0.5"
