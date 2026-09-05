"""Tests FIX B-NEW-3 (04-sep-2026): coerción de tipos en niche_benchmarks.

El LLM puede devolver los números como strings ("5000"). Un tipo incorrecto
revienta el prefilter del worker (`TypeError: '<' not supported between
instances of 'int' and 'str'`) y tumba el run completo. La validación debe
coercionar o conservar el fallback — nunca propagar el tipo del LLM.
"""

from discovery.profile_generator import _validate_niche_benchmarks

_FALLBACK = {
    "min_followers": 5000,
    "min_er": 0.035,
    "target_er": 0.055,
    "max_fake_ratio": 0.15,
    "min_posts": 30,
    "ideal_follower_range": "5k-150k",
}


def test_string_numbers_are_coerced_to_int():
    out = _validate_niche_benchmarks(
        {"min_followers": "8000", "min_posts": "25"}, _FALLBACK
    )
    assert out["min_followers"] == 8000
    assert isinstance(out["min_followers"], int)
    assert out["min_posts"] == 25


def test_float_strings_are_coerced():
    out = _validate_niche_benchmarks(
        {"min_er": "0.04", "target_er": 0.06, "max_fake_ratio": "0.2"}, _FALLBACK
    )
    assert out["min_er"] == 0.04
    assert out["target_er"] == 0.06
    assert out["max_fake_ratio"] == 0.2


def test_garbage_values_preserve_fallback():
    out = _validate_niche_benchmarks(
        {"min_followers": "miles", "min_er": None}, _FALLBACK
    )
    assert out["min_followers"] == _FALLBACK["min_followers"]
    assert out["min_er"] == _FALLBACK["min_er"]


def test_none_or_empty_returns_fallback_untouched():
    assert _validate_niche_benchmarks(None, _FALLBACK) == _FALLBACK
    assert _validate_niche_benchmarks({}, _FALLBACK) == _FALLBACK
    assert _validate_niche_benchmarks("corrupt", _FALLBACK) == _FALLBACK


def test_valid_dict_passthrough_coerced():
    out = _validate_niche_benchmarks(
        {
            "min_followers": 10000,
            "min_er": 0.05,
            "target_er": 0.07,
            "max_fake_ratio": 0.1,
            "min_posts": 50,
            "ideal_follower_range": "10k-200k",
        },
        _FALLBACK,
    )
    assert out == {
        "min_followers": 10000,
        "min_er": 0.05,
        "target_er": 0.07,
        "max_fake_ratio": 0.1,
        "min_posts": 50,
        "ideal_follower_range": "10k-200k",
    }


def test_result_is_never_string_for_min_followers():
    """Guard de regresión: cualquier valor que llegue al prefilter debe ser
    comparable con int — el TypeError int < str es lo que tumba el run."""
    for raw in ("1000", 1000, 1000.7, [1000], {"v": 1000}):
        out = _validate_niche_benchmarks({"min_followers": raw}, _FALLBACK)
        assert isinstance(out["min_followers"], int), f"failed for raw={raw!r}"
