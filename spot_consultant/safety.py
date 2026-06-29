"""The guardrail layer — deterministic, no LLM, no network.

The model can hallucinate; coastline geometry cannot. This module cross-checks
every wind direction the model called "good" against the spot's shoreline
orientation and flags any that are actually OFFSHORE — the dangerous case that
blows a rider out to sea. An offshore direction marked "good" is treated as a
likely model error and forces human review before the spot can be published.

In production, `seaward_bearing_deg` would be *computed* from OpenStreetMap
coastline geometry (authoritative) rather than taken from the model; the
classification math below is identical either way.
"""

from __future__ import annotations

from pydantic import BaseModel

from .schema import Confidence, SpotReport

COMPASS_TO_DEG: dict[str, float] = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5,
    "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
}

ONSHORE = "onshore"
CROSS = "cross-shore"
OFFSHORE = "offshore"
UNKNOWN = "unknown"


def _angular_diff(a: float, b: float) -> float:
    """Smallest absolute difference between two compass bearings, in 0..180."""
    return abs((a - b + 180) % 360 - 180)


def classify_wind(from_bearing: float, seaward_bearing: float) -> str:
    """Classify a wind blowing FROM `from_bearing` against a shore whose
    seaward (beach -> open water) direction is `seaward_bearing`.

    - Onshore  (~0 deg apart): wind comes off the sea onto the beach. Safe, choppy.
    - Offshore (~180 apart):   wind blows off the land out to sea. DANGEROUS.
    - Cross-shore (~90):       parallel to the beach. Usually ideal.
    """
    diff = _angular_diff(from_bearing, seaward_bearing)
    if diff <= 45:
        return ONSHORE
    if diff >= 135:
        return OFFSHORE
    return CROSS


class DirectionAssessment(BaseModel):
    direction: str
    classification: str
    flagged: bool
    note: str | None = None


class SafetyAnalysis(BaseModel):
    assessments: list[DirectionAssessment]
    contradictions: list[str]
    needs_human_review: bool


def analyze(report: SpotReport) -> SafetyAnalysis:
    """Run the deterministic safety pass over a model-produced report."""
    assessments: list[DirectionAssessment] = []
    contradictions: list[str] = []
    seaward = report.seaward_bearing_deg

    for d in report.good_wind_directions:
        name = d.value
        if seaward is None:
            assessments.append(
                DirectionAssessment(
                    direction=name,
                    classification=UNKNOWN,
                    flagged=True,
                    note="No shoreline orientation available — cannot verify safety.",
                )
            )
            continue

        cls = classify_wind(COMPASS_TO_DEG[name], seaward)
        flagged = cls == OFFSHORE
        note = None
        if flagged:
            note = (
                f"Model marked {name} as good, but it is OFFSHORE here "
                f"(blows riders out to sea). Likely error — verify before publishing."
            )
            contradictions.append(note)
        assessments.append(
            DirectionAssessment(direction=name, classification=cls, flagged=flagged, note=note)
        )

    needs_review = bool(contradictions)
    if report.overall_confidence in (Confidence.low, Confidence.unknown):
        needs_review = True
    if report.wind_direction_confidence in (Confidence.low, Confidence.unknown):
        needs_review = True
    if report.shoreline_confidence in (Confidence.low, Confidence.unknown):
        needs_review = True
    if seaward is None:
        needs_review = True

    return SafetyAnalysis(
        assessments=assessments,
        contradictions=contradictions,
        needs_human_review=needs_review,
    )
