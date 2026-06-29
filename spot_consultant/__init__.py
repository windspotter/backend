"""Spot Consultant — an AI research assistant that enriches new watersport
spots with structured, source-cited, safety-checked metadata."""

from .consultant import enrich_spot, EnrichmentResult

__all__ = ["enrich_spot", "EnrichmentResult"]
