"""Live eval set — runs only when ANTHROPIC_API_KEY is present.

These are *behavioral* assertions on the real pipeline, not unit tests: for a
set of well-known spots, the output must be well-formed, cite sources, and —
crucially — never publish an offshore direction as 'good' without flagging it.
This is the kind of harness that turns "looks plausible" into "verified".
"""

import os

import pytest

from spot_consultant import enrich_spot
from spot_consultant.schema import SpotReport

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live eval requires ANTHROPIC_API_KEY",
)

KNOWN_SPOTS = ["Tarifa, Spain", "Leucate, France", "Hookipa, Maui"]


@pytest.mark.parametrize("query", KNOWN_SPOTS)
def test_enrichment_is_well_formed(query):
    result = enrich_spot(query, mock=False)
    r = result.report

    assert isinstance(r, SpotReport)
    assert r.name
    assert r.summary
    assert r.sources, "a well-known spot should yield at least one cited source"

    # the safety pass must cover every direction the model claimed
    assert len(result.safety.assessments) == len(r.good_wind_directions)

    # the core safety invariant: no offshore 'good' direction goes unflagged
    for a in result.safety.assessments:
        if a.classification == "offshore":
            assert a.flagged, "an offshore 'good' direction must be flagged for review"
