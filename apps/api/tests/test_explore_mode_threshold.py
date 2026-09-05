"""Tests FIX N-2 (04-sep-2026): umbral de match_score por modo.

En modo Explorar los candidatos no pasan por enrichment: llegan con
followers=0 y en su mayoría sin bio (son UserShort de hashtags/reels), así
que rough score = 0 y el umbral fijo de 5 los eliminaba a TODOS — el modo
entregaba 0 candidatos siempre. Regla de oro: "mostrar candidatos > rechazar
candidatos".
"""

from app.workers.worker import _min_match_score_for_mode


def test_explore_mode_threshold_is_zero():
    assert _min_match_score_for_mode(True) == 0


def test_auto_and_analyze_mode_threshold_is_five():
    assert _min_match_score_for_mode(False) == 5
