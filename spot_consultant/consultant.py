"""Core pipeline: validate -> analyze -> extract -> verify.

  1. validate  — confirm via OpenStreetMap that the input is really a spot, and
                 pick up authoritative coordinates + shoreline orientation.
                 Rejected inputs short-circuit here, before any LLM tokens.
  2. analyze   — an agent loop: Claude, guided by the analysis SKILL playbook
                 (the system prompt), uses web search/fetch to gather info.
  3. extract   — force the findings into the validated SpotReport schema.
  4. verify    — deterministic safety guardrail (safety.py).

The Anthropic SDK is imported lazily so mock mode / unit tests need only pydantic.
"""

from __future__ import annotations

import os

from pydantic import BaseModel

from . import prompts, skills, validation
from .mock import mock_report
from .safety import SafetyAnalysis
from .safety import analyze as run_safety
from .schema import Confidence, SpotReport
from .validation import SpotStatus, Validation

# Default to Opus; override with e.g. SPOT_MODEL=claude-haiku-4-5 to run cheaply.
MODEL = os.environ.get("SPOT_MODEL", "claude-opus-4-8")
ANALYSIS_SKILL = "analyze-watersport-spot"

# 4.6+ models support adaptive thinking and the dynamic-filtering web tools;
# Haiku 4.5 / Sonnet 4.5 reject adaptive thinking and need the basic web-search tool.
_MODERN_MODEL = MODEL.startswith(
    ("claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8", "claude-sonnet-4-6", "claude-fable-5")
)
_WEB_TOOLS = (
    [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 4},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 3},
    ]
    if _MODERN_MODEL
    else [{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}]
)
_THINKING = {"thinking": {"type": "adaptive"}} if _MODERN_MODEL else {}


class EnrichmentResult(BaseModel):
    query: str
    mode: str  # "mock" | "live" | "rejected"
    validation: Validation | None = None
    report: SpotReport | None = None
    safety: SafetyAnalysis | None = None
    sources: list[str] = []


def _analyze(client, query: str, context: str) -> str:
    """Agent loop: the SKILL is the system prompt (knowledge); web search/fetch
    are the tools (capability). Handle `pause_turn` to resume the server-side
    tool loop."""
    system = skills.load_skill(ANALYSIS_SKILL)
    messages = [{"role": "user", "content": prompts.analyze_prompt(query, context)}]
    resp = None
    for _ in range(6):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=system,
            tools=_WEB_TOOLS,        # max_uses on each caps web-search cost
            messages=messages,
            **_THINKING,
        )
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break
    return "".join(block.text for block in resp.content if block.type == "text")


def _extract(client, query: str, research: str) -> SpotReport:
    parsed = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=prompts.EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": prompts.extraction_prompt(query, research)}],
        output_format=SpotReport,
    )
    return parsed.parsed_output


def enrich_spot(query: str, *, client=None, mock: bool | None = None) -> EnrichmentResult:
    """Validate, research, and safety-check a watersport spot.

    Leave `ANTHROPIC_API_KEY` unset (or pass `mock=True`) to run offline against
    a canned report.
    """
    if mock is None:
        mock = not os.environ.get("ANTHROPIC_API_KEY")

    if mock:
        report = mock_report(query)
        return EnrichmentResult(
            query=query, mode="mock", report=report,
            safety=run_safety(report), sources=report.sources,
        )

    # 1. Validation gate — reject non-spots before spending tokens.
    v = validation.validate_spot(query)
    if v.status == SpotStatus.rejected:
        return EnrichmentResult(query=query, mode="rejected", validation=v)

    if client is None:
        import anthropic  # lazy: only needed for live calls

        client = anthropic.Anthropic()

    # 2-3. Analyze (skill-guided) then extract into the schema.
    research = _analyze(client, query, prompts.validation_context(v))
    report = _extract(client, query, research)

    # Coordinates from OSM/geocoding are reliable; fill them if the model didn't.
    report.latitude = report.latitude or v.latitude
    report.longitude = report.longitude or v.longitude

    # Orientation: cross-check OSM against the model rather than blindly trusting it.
    # OSM's nearest-coastline guess can pick the wrong shore (bays / archipelagos):
    #   agree    -> OSM confirms the model: use it, high confidence
    #   disagree -> trust the research, keep the model's value, low confidence + flag
    #   only one -> use whichever exists, at medium confidence
    osm_bearing = v.seaward_bearing_deg
    model_bearing = report.seaward_bearing_deg
    if osm_bearing is not None and model_bearing is not None:
        diff = abs((osm_bearing - model_bearing + 180) % 360 - 180)  # 0..180
        if diff <= 45:
            report.seaward_bearing_deg = osm_bearing
            report.shoreline_confidence = Confidence.high
            report.sources.append("OpenStreetMap coastline geometry (Overpass)")
        else:
            report.shoreline_confidence = Confidence.low
    elif osm_bearing is not None:
        report.seaward_bearing_deg = osm_bearing
        report.shoreline_confidence = Confidence.medium
        report.sources.append("OpenStreetMap coastline geometry (Overpass)")
    # else: only the model (or neither) — keep what the model produced

    # 4. Verify.
    return EnrichmentResult(
        query=query, mode="live", validation=v, report=report,
        safety=run_safety(report), sources=report.sources,
    )
