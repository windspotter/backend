"""Pure coastline geometry — no network, no dependencies, fully unit-testable.

The load-bearing fact: OpenStreetMap `natural=coastline` ways are oriented so
that **land is on the left and water is on the right** in the direction the way
is drawn. So the seaward direction at a coastline segment is just the segment's
heading rotated 90 degrees clockwise (to the right). That turns "which way does
the shore face" — the value our safety guardrail depends on — into deterministic
geometry rather than a model guess.
"""

from __future__ import annotations

import math


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing (0-360, 0=N, 90=E) from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def seaward_bearing_from_segment(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Seaward bearing for an OSM coastline segment a -> b (each (lat, lon)).

    Water is on the right of the way, so seaward = segment heading + 90 deg.
    """
    return (bearing(a[0], a[1], b[0], b[1]) + 90) % 360
