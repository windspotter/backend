"""The output contract.

Claude is *forced* to emit exactly this shape via Anthropic structured outputs
(`client.messages.parse(output_format=SpotReport)`), so the model's free-text
research is validated into typed, enumerated fields before anything downstream
touches it. Bad types, invented enum values, and missing required fields fail
at the API boundary, not three layers deep.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    unknown = "unknown"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class WindDirection(str, Enum):
    """16-point compass. Values are the direction the wind blows *from*."""

    N = "N"
    NNE = "NNE"
    NE = "NE"
    ENE = "ENE"
    E = "E"
    ESE = "ESE"
    SE = "SE"
    SSE = "SSE"
    S = "S"
    SSW = "SSW"
    SW = "SW"
    WSW = "WSW"
    W = "W"
    WNW = "WNW"
    NW = "NW"
    NNW = "NNW"


class Sport(str, Enum):
    windsurfing = "windsurfing"
    kitesurfing = "kitesurfing"
    wingfoiling = "wingfoiling"


class Hazard(BaseModel):
    description: str = Field(description="The hazard, e.g. 'submerged rocks on the north end'.")
    severity: Severity = Field(description="How dangerous the hazard is.")
    source_url: str | None = Field(default=None, description="URL backing this claim, if any.")


class SpotReport(BaseModel):
    """Structured metadata for one watersport spot.

    Every field is model-emitted and must be backed by the research. Unknowns
    are explicit (null / Confidence.unknown), never guessed — the prompt makes
    this a hard rule because the data is safety-relevant.
    """

    name: str = Field(description="Canonical spot name.")
    latitude: float | None = Field(default=None, description="Decimal degrees, null if unknown.")
    longitude: float | None = Field(default=None, description="Decimal degrees, null if unknown.")
    sports: list[Sport] = Field(default_factory=list, description="Sports the spot is suited to.")

    seaward_bearing_deg: float | None = Field(
        default=None,
        description=(
            "Compass bearing 0-360 (0=N, 90=E, 180=S, 270=W) pointing FROM the beach/launch "
            "toward open water. Anchors the onshore/offshore safety analysis. Null if unknown."
        ),
    )
    shoreline_confidence: Confidence = Field(description="Confidence in seaward_bearing_deg.")

    good_wind_directions: list[WindDirection] = Field(
        default_factory=list,
        description="Wind directions (the direction the wind blows FROM) that make this spot work.",
    )
    wind_direction_confidence: Confidence = Field(description="Confidence in good_wind_directions.")

    typical_season: str | None = Field(default=None, description="Best months / season, null if unknown.")
    skill_level: str | None = Field(default=None, description="e.g. 'beginner-friendly', 'advanced only'.")
    hazards: list[Hazard] = Field(default_factory=list, description="Known safety hazards.")
    summary: str = Field(description="2-3 sentence plain-language summary for a rider.")
    sources: list[str] = Field(default_factory=list, description="Source URLs actually used.")
    overall_confidence: Confidence = Field(description="Overall confidence in this report.")
