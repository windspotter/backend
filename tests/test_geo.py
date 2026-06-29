"""Geometry unit tests — no network, no extra deps.

These prove the coastline-orientation math that the safety guardrail relies on.
"""

import math

from spot_consultant.geo import bearing, seaward_bearing_from_segment


def _close(a: float, b: float, tol: float = 1.0) -> bool:
    return abs((a - b + 180) % 360 - 180) <= tol


def test_bearing_cardinal_directions():
    assert _close(bearing(0, 0, 1, 0), 0)     # due north
    assert _close(bearing(0, 0, 0, 1), 90)    # due east
    assert _close(bearing(0, 0, -1, 0), 180)  # due south
    assert _close(bearing(0, 0, 0, -1), 270)  # due west


def test_seaward_is_90deg_right_of_segment():
    # Coastline drawn west->east (heading 90). Water is on the right -> seaward south (180).
    assert _close(seaward_bearing_from_segment((0, 0), (0, 1)), 180)
    # Coastline drawn south->north (heading 0). Water on the right -> seaward east (90).
    assert _close(seaward_bearing_from_segment((0, 0), (1, 0)), 90)
