"""Unit tests for the validation gate's pure logic — no network needed."""

from spot_consultant.validation import SpotStatus, _as_coords, _decide


def test_parse_coordinates():
    assert _as_coords("36.0, -5.6") == (36.0, -5.6)
    assert _as_coords("36.0 -5.6") == (36.0, -5.6)
    assert _as_coords("Tarifa, Spain") is None


def test_decision_logic():
    feature = [{"name": "Los Lances", "type": "windsurfing"}]
    assert _decide(feature, 200.0)[0] == SpotStatus.confirmed   # tagged feature wins
    assert _decide([], 200.0)[0] == SpotStatus.plausible         # coast but untagged
    assert _decide([], None)[0] == SpotStatus.rejected           # no water at all
