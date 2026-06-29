"""An MCP server exposing OpenStreetMap lookups as tools.

Run standalone over stdio:
    python -m spot_consultant.osm_mcp_server

Inspect interactively:
    mcp dev spot_consultant/osm_mcp_server.py

Or register it with any MCP client (Claude Desktop config):
    {
      "mcpServers": {
        "osm-watersports": {
          "command": "python",
          "args": ["-m", "spot_consultant.osm_mcp_server"]
        }
      }
    }

FastMCP derives each tool's JSON schema from the type hints and docstring below,
so the function signature *is* the tool contract.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import osm, validation

mcp = FastMCP("osm-watersports")


@mcp.tool()
def validate_spot(query: str) -> dict:
    """Check whether a place name or 'lat, lon' is really a watersport spot, using
    OpenStreetMap. Returns a status (confirmed / plausible / rejected / unknown)
    plus resolved coordinates, nearby tagged features, and the seaward bearing.
    Call this first to avoid analyzing places that aren't spots."""
    return validation.validate_spot(query).model_dump()


@mcp.tool()
def geocode(query: str) -> dict | None:
    """Resolve a place name (e.g. 'Tarifa, Spain') to coordinates.

    Returns {lat, lon, display_name}, or null if the place can't be found.
    """
    return osm.geocode(query)


@mcp.tool()
def find_watersport_features(lat: float, lon: float, radius_m: int = 2000) -> list[dict]:
    """List OSM-tagged watersport features (windsurf/kite/sail spots and
    beaches) within radius_m metres of a coordinate. Use this to confirm a real
    spot exists near a point before treating it as one."""
    return osm.find_watersport_features(lat, lon, radius_m)


@mcp.tool()
def coastline_seaward_bearing(lat: float, lon: float, radius_m: int = 1000) -> dict | None:
    """Compute the authoritative seaward bearing (degrees the shore faces toward
    open water) from the nearest OSM coastline. Returns {seaward_bearing_deg,
    segment} or null if no coastline is within radius_m. Prefer this over any
    model-estimated orientation — it is derived from coastline geometry."""
    return osm.coastline_seaward_bearing(lat, lon, radius_m)


if __name__ == "__main__":
    mcp.run()
