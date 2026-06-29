"""The validation gate.

Before we spend any LLM tokens, we cheaply confirm the input is really a
watersport spot using authoritative OpenStreetMap data:
  - resolve a name to coordinates (or accept coordinates directly),
  - look for tagged watersport features and/or a coastline nearby,
  - decide: confirmed / plausible / rejected.

This is also exposed as an MCP tool (osm_mcp_server.py), so any agent or client
can call `validate_spot` directly. All OSM access is best-effort — if the data
source is unreachable we return `unknown` rather than crashing the pipeline.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field


class SpotStatus(str, Enum):
    confirmed = "confirmed"   # a tagged watersport feature is nearby
    plausible = "plausible"   # on the coast, but nothing explicitly tagged
    rejected = "rejected"     # no water / couldn't be located
    unknown = "unknown"       # validation source was unavailable


class Validation(BaseModel):
    status: SpotStatus
    query: str
    latitude: float | None = None
    longitude: float | None = None
    display_name: str | None = None
    nearby_features: list[dict] = Field(default_factory=list)
    seaward_bearing_deg: float | None = None
    reason: str = ""


_COORD = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*$")


def _as_coords(query: str) -> tuple[float, float] | None:
    """Parse 'lat, lon' or 'lat lon'. Returns None for anything else (a name)."""
    m = _COORD.match(query)
    return (float(m.group(1)), float(m.group(2))) if m else None


def _decide(features: list[dict], seaward: float | None) -> tuple[SpotStatus, str]:
    """Pure decision logic — separated out so it can be unit-tested without network."""
    if features:
        return SpotStatus.confirmed, f"Found {len(features)} tagged watersport feature(s) nearby."
    if seaward is not None:
        return SpotStatus.plausible, "On the coast, but no tagged watersport feature nearby."
    return SpotStatus.rejected, "No coastline or watersport features nearby — unlikely to be a spot."


def validate_spot(query: str) -> Validation:
    """Confirm (via OSM) whether `query` is a real watersport spot."""
    try:
        from . import osm  # lazy: keeps this module import-light for tests

        coords = _as_coords(query)
        display = None
        if coords is None:
            place = osm.geocode(query)
            if not place:
                return Validation(status=SpotStatus.rejected, query=query,
                                  reason="Could not locate this place.")
            coords = (place["lat"], place["lon"])
            display = place["display_name"]

        lat, lon = coords
        features = osm.find_watersport_features(lat, lon)
        bearing = osm.coastline_seaward_bearing(lat, lon)
        seaward = bearing["seaward_bearing_deg"] if bearing else None

        status, reason = _decide(features, seaward)
        return Validation(
            status=status, query=query, latitude=lat, longitude=lon,
            display_name=display, nearby_features=features,
            seaward_bearing_deg=seaward, reason=reason,
        )
    except Exception as exc:  # OSM unreachable, etc. — don't crash enrichment
        return Validation(status=SpotStatus.unknown, query=query,
                          reason=f"Validation source unavailable: {type(exc).__name__}")
