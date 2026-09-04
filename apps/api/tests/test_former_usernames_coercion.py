import pytest
from discovery.tools.hikerapi_client import _coerce_former_usernames


@pytest.mark.parametrize(
    "raw,expected_count",
    [
        (None, 0),
        ([], 0),
        ("", 0),
        ("eli", 1),
        ("viejo1,viejo2", 2),
        ("un_handle_bastante_largo", 1),
        (["viejo1", "viejo2"], 2),
        (["viejo1", "", "  ", "viejo2"], 2),
        ([{"username": "viejo1"}, {"username": "viejo2"}], 2),
        ([{"name": "viejo1"}], 1),
        (12345, 0),
        ({"username": "x"}, 0),
    ],
)
def test_coerce_never_counts_characters(raw, expected_count):
    assert len(_coerce_former_usernames(raw)) == expected_count


def test_coerce_always_returns_list_of_str():
    for raw in [None, "a,b", ["a"], [{"username": "b"}], 99]:
        out = _coerce_former_usernames(raw)
        assert isinstance(out, list)
        assert all(isinstance(x, str) for x in out)


def test_single_username_string_does_not_trigger_penalty():
    count = len(_coerce_former_usernames("eli"))
    fraud_penalty = 0.80 if count >= 3 else (0.90 if count == 2 else 1.0)
    assert fraud_penalty == 1.0
