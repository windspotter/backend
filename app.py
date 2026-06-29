"""Streamlit demo UI.

    streamlit run app.py

Runs in mock mode automatically when ANTHROPIC_API_KEY is unset.
"""

from __future__ import annotations

import streamlit as st

from spot_consultant import enrich_spot

st.set_page_config(page_title="Spot Consultant", page_icon="🌊")

st.title("🌊 Spot Consultant")
st.caption(
    "Validate a spot via OpenStreetMap, analyze it with a skill-guided agent, "
    "return schema-validated output, and run a deterministic safety guardrail."
)

query = st.text_input("Spot name or coordinates", "Tarifa, Spain")

if st.button("Research spot", type="primary"):
    with st.spinner("Validating and researching the spot…"):
        result = enrich_spot(query)

    if result.mode == "rejected":
        reason = result.validation.reason if result.validation else ""
        st.error(f"'{query}' doesn't look like a watersport spot. {reason}")
        st.stop()

    r = result.report
    if result.mode == "mock":
        st.info("Running in **mock mode** (no `ANTHROPIC_API_KEY` set) — showing a canned report.")

    if result.validation:
        st.caption(f"OpenStreetMap validation: **{result.validation.status.value}** — {result.validation.reason}")

    st.subheader(r.name)
    st.write(r.summary)

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall confidence", r.overall_confidence.value)
    c2.metric("Sports", ", ".join(s.value for s in r.sports) or "—")
    c3.metric("Needs review", "Yes" if result.safety.needs_human_review else "No")

    st.markdown("#### Wind-direction safety check")
    st.caption(
        f"Shore faces **{r.seaward_bearing_deg}°** seaward. Each direction the model "
        "called 'good' is classified by geometry — not by the model — so an offshore "
        "(dangerous) direction can't slip through."
    )
    st.table(
        [
            {
                "direction": a.direction,
                "classification": a.classification,
                "flag": "⚠️" if a.flagged else "",
                "note": a.note or "",
            }
            for a in result.safety.assessments
        ]
    )
    for c in result.safety.contradictions:
        st.warning(c)

    if r.hazards:
        st.markdown("#### Hazards")
        for h in r.hazards:
            st.write(f"- **[{h.severity.value}]** {h.description}")

    if result.sources:
        st.markdown("#### Sources")
        for s in result.sources:
            st.write(f"- {s}")

    with st.expander("Raw validated JSON"):
        st.json(result.model_dump(mode="json"))
