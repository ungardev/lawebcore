"""
P.I.A.R Projection Engine — System Constants

All constants are named and centralized per the methodology spec.
Zero magic numbers dispersed in the codebase.
"""

from typing import Final

MESES_RECIENTE: Final[int] = 6
PESO_RECIENTE: Final[float] = 1.5
PESO_ANTIGUO: Final[float] = 1.0

MIN_CAMPANAS_POR_MARCA: Final[int] = 3
MAX_CAMPANAS_CONSIDERADAS: Final[int] = 5

ESCENARIOS: Final[dict[str, float]] = {
    "conservador": 0.75,
    "base": 1.0,
    "optimista": 1.30,
}

ESCENARIOS_OPTIMISTA_AJUSTADO: Final[dict[str, float]] = {
    "conservador": 0.85,
    "base": 1.0,
    "optimista": 1.40,
}

ESCENARIOS_CONSERVADOR_AJUSTADO: Final[dict[str, float]] = {
    "conservador": 0.60,
    "base": 0.85,
    "optimista": 1.15,
}

FACTOR_ALCANCE: Final[float] = 0.70

TASA_VIRAL_ESPERADA: Final[float] = 0.10

MIN_POSTS_PARA_SCORE: Final[int] = 3
UMBRAL_ESCALAR_PARA_AJUSTE: Final[float] = 0.70
UMBRAL_DESCARTAR_PARA_AJUSTE: Final[float] = 0.70

TIERS_VALIDOS: Final[list[str]] = ["NANO", "MICRO", "MID", "MACRO", "MEGA"]

POSTGREST_NULL: Final[str] = "N/A"
