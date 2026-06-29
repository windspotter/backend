"""OpenStreetMap client — geocoding (Nominatim) and feature/coastline queries
(Overpass). Network lives here; the geometry lives in geo.py.

These functions are exposed as MCP tools (osm_mcp_server.py) and also called
directly by the enrichment pipeline to ground the report in authoritative data.
All are best-effort: callers should treat exceptions / None as "unknown" and
degrade gracefully.
"""

from __future__ import annotations

import httpx

from .geo import seaward_bearing_from_segment

NOMINATIM = "https://nominatim.openstreetmap.org/search"
# Public Overpass instances are best-effort and frequently 429/504 under load,
# so we fail over across mirrors rather than trust a single endpoint.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
# Nominatim's usage policy requires a descriptive User-Agent.
HEADERS = {"User-Agent": "spot-consultant/0.1 (watersports spot demo)"}


def geocode(query: str) -> dict | None:
    """Resolve a place name to coordinates. Returns {lat, lon, display_name} or None."""
    resp = httpx.get(
        NOMINATIM,
        params={"q": query, "format": "json", "limit": 1},
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None
    top = data[0]
    return {
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top.get("display_name"),
    }


def _overpass(query: str) -> dict:
    """POST an Overpass query, trying each mirror until one answers."""
    last_exc: Exception | None = None
    for url in OVERPASS_ENDPOINTS:
        try:
            resp = httpx.post(url, data={"data": query}, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:  # status error, timeout, or transport error
            last_exc = exc
            continue
    raise last_exc  # all mirrors failed; caller degrades to "unknown"


def find_watersport_features(lat: float, lon: float, radius_m: int = 2000) -> list[dict]:
    """Tagged watersport features (windsurf/kite/sail spots, beaches) near a point."""
    query = f"""[out:json][timeout:25];
(
  nwr(around:{radius_m},{lat},{lon})[sport~"windsurfing|kitesurfing|sailing"];
  nwr(around:{radius_m},{lat},{lon})[natural=beach];
);
out center tags;"""
    elements = _overpass(query).get("elements", [])
    features: list[dict] = []
    for el in elements:
        tags = el.get("tags", {})
        center = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        features.append(
            {
                "name": tags.get("name"),
                "type": tags.get("sport") or tags.get("natural"),
                "lat": center.get("lat"),
                "lon": center.get("lon"),
            }
        )
    return features[:30]


def coastline_seaward_bearing(lat: float, lon: float, radius_m: int = 1000) -> dict | None:
    """Authoritative seaward bearing from the nearest OSM coastline segment.

    Returns {seaward_bearing_deg, segment} or None if no coastline is nearby.
    """
    query = f"""[out:json][timeout:25];
way(around:{radius_m},{lat},{lon})[natural=coastline];
out geom;"""
    elements = _overpass(query).get("elements", [])

    best: tuple[float, dict, dict] | None = None  # (sq_dist, node_a, node_b)
    for way in elements:
        geom = way.get("geometry") or []
        for a, b in zip(geom, geom[1:]):
            mid_lat = (a["lat"] + b["lat"]) / 2
            mid_lon = (a["lon"] + b["lon"]) / 2
            sq_dist = (mid_lat - lat) ** 2 + (mid_lon - lon) ** 2
            if best is None or sq_dist < best[0]:
                best = (sq_dist, a, b)

    if best is None:
        return None

    _, a, b = best
    seaward = seaward_bearing_from_segment((a["lat"], a["lon"]), (b["lat"], b["lon"]))
    return {
        "seaward_bearing_deg": round(seaward, 1),
        "segment": [[a["lat"], a["lon"]], [b["lat"], b["lon"]]],
    }
