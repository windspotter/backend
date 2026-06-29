"""Prompts for the pipeline.

The analysis *system* prompt is the SKILL (see skills/analyze-watersport-spot/),
loaded at call time — so this module only builds the user-turn messages and the
extraction system prompt.
"""

EXTRACTION_SYSTEM = """You convert research notes into a strict JSON report. \
Only include facts supported by the notes. Use null or the "unknown" confidence \
for anything the notes do not establish — never guess, especially for wind \
directions, shoreline orientation, and hazards (these are safety-critical). \
Copy source URLs from the notes into the sources list."""


def validation_context(v) -> str:
    """Render the OSM validation result as grounding for the analyze step."""
    lines = [f"OpenStreetMap validation: {v.status.value} ({v.reason})"]
    if v.latitude is not None and v.longitude is not None:
        lines.append(f"Coordinates: {v.latitude}, {v.longitude}")
    if v.display_name:
        lines.append(f"Resolved place: {v.display_name}")
    if v.seaward_bearing_deg is not None:
        lines.append(
            f"Shoreline-orientation hint (seaward bearing, rough — cross-check): {v.seaward_bearing_deg} deg"
        )
    named = [f["name"] for f in v.nearby_features if f.get("name")][:8]
    if named:
        lines.append("Nearby tagged features: " + ", ".join(named))
    return (
        "Grounding from OpenStreetMap — coordinates are reliable, but the shoreline "
        "orientation is only a rough hint to cross-check:\n" + "\n".join(lines)
    )


def analyze_prompt(query: str, context: str) -> str:
    return (
        f"Analyze this watersport spot and report everything you can establish: {query}\n\n"
        f"{context}"
    )


def extraction_prompt(query: str, research: str) -> str:
    return (
        f"Spot queried: {query}\n\n"
        f"Research notes:\n\"\"\"\n{research}\n\"\"\"\n\n"
        "Extract the structured report from the notes above."
    )
