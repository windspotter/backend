"""Unit tests for the deterministic safety guardrail.

No API key or network required — these prove the guardrail logic in isolation,
including that it catches a model error (an offshore direction marked 'good').
"""

from spot_consultant.safety import CROSS, OFFSHORE, ONSHORE, analyze, classify_wind
from spot_consultant.schema import Confidence, SpotReport, WindDirection


def test_classify_wind_basic():
    # Shore faces south (180 deg) toward the sea.
    assert classify_wind(180, 180) == ONSHORE   # wind off the sea
    assert classify_wind(0, 180) == OFFSHORE    # wind off the land -> dangerous
    assert classify_wind(90, 180) == CROSS      # side-shore -> ideal


def test_offshore_good_direction_is_flagged():
    # Shore faces south; the model wrongly lists N (offshore here) as 'good'.
    report = SpotReport(
        name="Test Spot",
        seaward_bearing_deg=180.0,
        shoreline_confidence=Confidence.high,
        good_wind_directions=[WindDirection.N, WindDirection.E],
        wind_direction_confidence=Confidence.high,
        summary="test",
        overall_confidence=Confidence.high,
    )
    res = analyze(report)
    flagged = {a.direction: a.flagged for a in res.assessments}

    assert flagged["N"] is True       # offshore -> flagged
    assert flagged["E"] is False      # cross-shore -> fine
    assert res.needs_human_review is True
    assert res.contradictions         # a human-readable contradiction was recorded


def test_missing_orientation_forces_review():
    report = SpotReport(
        name="Test Spot",
        seaward_bearing_deg=None,
        shoreline_confidence=Confidence.unknown,
        good_wind_directions=[WindDirection.W],
        wind_direction_confidence=Confidence.medium,
        summary="test",
        overall_confidence=Confidence.medium,
    )
    res = analyze(report)
    assert res.needs_human_review is True
    assert res.assessments[0].classification == "unknown"


def test_clean_report_passes():
    # Shore faces SSW (200); all listed directions are cross-shore -> no flags.
    report = SpotReport(
        name="Test Spot",
        seaward_bearing_deg=200.0,
        shoreline_confidence=Confidence.high,
        good_wind_directions=[WindDirection.E, WindDirection.W],
        wind_direction_confidence=Confidence.high,
        summary="test",
        overall_confidence=Confidence.high,
    )
    res = analyze(report)
    assert not res.contradictions
    assert res.needs_human_review is False
