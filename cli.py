"""CLI front-end.

    python cli.py "Tarifa, Spain"
    python cli.py "36.45, -5.0"          # coordinates work too

Runs in mock mode automatically when ANTHROPIC_API_KEY is unset.
"""

from __future__ import annotations

import sys

from spot_consultant import enrich_spot


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print('Usage: python cli.py "Spot name or coordinates"')
        raise SystemExit(1)

    query = " ".join(args)
    result = enrich_spot(query)

    # The validation gate can reject a non-spot before any analysis runs.
    if result.mode == "rejected":
        print(f"\n[rejected] '{query}' doesn't look like a watersport spot.")
        if result.validation:
            print(f"Reason: {result.validation.reason}")
        return

    r = result.report
    print(f"\n=== {r.name}   [{result.mode} mode] ===")
    print(r.summary)
    print(f"\nSports: {', '.join(s.value for s in r.sports) or 'unknown'}")
    if r.latitude is not None and r.longitude is not None:
        print(f"Location: {r.latitude}, {r.longitude}")
    print(
        f"Shore faces {r.seaward_bearing_deg}° seaward "
        f"(confidence: {r.shoreline_confidence.value})"
    )

    print(f"\nWind-direction safety check (confidence: {r.wind_direction_confidence.value}):")
    for a in result.safety.assessments:
        mark = "[FLAG]" if a.flagged else "  ok  "
        line = f"  {mark} {a.direction:<4} {a.classification}"
        if a.note:
            line += f"  -- {a.note}"
        print(line)

    if r.hazards:
        print("\nHazards:")
        for h in r.hazards:
            print(f"  - [{h.severity.value}] {h.description}")

    print(f"\nOverall confidence: {r.overall_confidence.value}")
    print(f"Needs human review: {result.safety.needs_human_review}")

    if result.sources:
        print("\nSources:")
        for s in result.sources:
            print(f"  - {s}")


if __name__ == "__main__":
    main()
