"""Canned response for offline / no-key runs.

Lets the CLI, the Streamlit app, and CI run with zero credentials — so a live
demo never depends on the network or an API key being present. The values model
a believable side-shore spot; the safety pass classifies every direction as
cross-shore (the ideal), so nothing is flagged in the happy path. See
tests/test_safety.py for the guardrail catching a planted offshore direction.
"""

from __future__ import annotations

from .schema import Confidence, Hazard, Severity, SpotReport, Sport, WindDirection


def mock_report(query: str) -> SpotReport:
    return SpotReport(
        name=query,
        latitude=36.02,
        longitude=-5.61,
        sports=[Sport.windsurfing, Sport.kitesurfing, Sport.wingfoiling],
        seaward_bearing_deg=200.0,  # beach faces SSW toward open water
        shoreline_confidence=Confidence.high,
        good_wind_directions=[
            WindDirection.E,
            WindDirection.ENE,
            WindDirection.W,
            WindDirection.WSW,
        ],
        wind_direction_confidence=Confidence.high,
        typical_season="Spring to autumn; strongest, most reliable wind in summer.",
        skill_level="All levels in light wind; strong-wind days suit intermediate and up.",
        hazards=[
            Hazard(
                description="Strong currents and gusty acceleration zones on the strongest wind days.",
                severity=Severity.medium,
                source_url="https://example.com/spot-guide",
            ),
        ],
        summary=(
            "A wide sandy bay that works on both the easterly and westerly winds, "
            "mostly cross-shore. Reliable in season and friendly for progression, "
            "though the strongest days get gusty."
        ),
        sources=[
            "https://example.com/spot-guide",
            "https://example.com/wind-statistics",
        ],
        overall_confidence=Confidence.medium,
    )
