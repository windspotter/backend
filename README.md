# Windspotter — backend

> Turn a watersport spot (a name or coordinates) into a **validated, source-cited,
> safety-checked** report: which winds work, which are dangerous, hazards, season,
> and confidence — with the safety-critical parts verified by deterministic code,
> not just trusted from a model.

This is the AI/serverless **backend** of Windspotter. The iOS, Android, and Telegram
clients live in sibling repos under the same org; this service does the thinking.

*Built by a macOS/iOS engineer deliberately working across unfamiliar areas — so the
goal here is breadth + judgment, not a shippable business.*

---

## What this demonstrates

| Area | In this repo |
|---|---|
| **AI engineering** | agentic tool use, a **custom MCP server**, structured outputs, skill/prompt design, LLM **guardrails**, an eval harness |
| **Backend & serverless** | Python service, AWS Lambda, **SAM** infrastructure-as-code |
| **Cloud / DevOps / security** | IAM least-privilege, secrets in **SSM**, no-VPC reasoning, **keyless OIDC** deploys, cost guardrails |
| **Data & integration** | OpenStreetMap (Overpass + Nominatim), coastline **geometry**, weather APIs |
| **Product & systems thinking** | a validation gate, a 3-tier scaling strategy, honesty + human-in-the-loop |

Design reasoning (the most important part) lives in **[DECISIONS.md](DECISIONS.md)**.

---

## How it works

```
  name / coordinates
        │
        ▼
  ┌──────────────┐   not a spot →
  │  Validate    │──────────────▶ stop (no LLM tokens spent)
  │  OSM (MCP)   │
  └──────┬───────┘
         │ valid                 skill (playbook) ─┐
         ▼                       tools (web search, OSM) ─┐
  ┌──────────────┐  ◀──────────────────────────────────┘
  │   Analyze    │   agentic loop: Claude gathers + reasons
  └──────┬───────┘
         ▼
  ┌──────────────┐   validated SpotReport (Pydantic) — bad/invented
  │  Structured  │   data fails at the boundary, not downstream
  │    output    │
  └──────┬───────┘
         ▼
  ┌──────────────┐   deterministic geometry: flags an "offshore" wind
  │   Safety     │   the model wrongly called "good" (blows riders out to sea)
  │  guardrail   │
  └──────────────┘
```

1. **Validate** ([`validation.py`](spot_consultant/validation.py)) — resolve the input via OSM, confirm it's really a spot, grab authoritative coordinates + shoreline orientation. Non-spots short-circuit *before* any model call.
2. **Analyze** ([`consultant.py`](spot_consultant/consultant.py)) — an agent loop where the **skill** ([`SKILL.md`](spot_consultant/skills/analyze-watersport-spot/SKILL.md)) is the system prompt (the *knowledge*) and web search + OSM are the *tools* (the *capabilities*).
3. **Extract** — force the findings into a validated `SpotReport` ([`schema.py`](spot_consultant/schema.py)) via Anthropic structured outputs.
4. **Verify** ([`safety.py`](spot_consultant/safety.py)) — pure-geometry guardrail: every "good" wind direction is classified against the shore; an offshore one forces human review. *The model proposes; code disposes.*

## The interesting bits

- **Trust-by-field guardrail.** Wind-sport metadata is safety-relevant (offshore wind is dangerous). So the model's output is a *draft*: orientation is computed from OSM coastline geometry, and the guardrail catches any "good" direction that's actually offshore.
- **MCP server for OpenStreetMap** ([`osm_mcp_server.py`](spot_consultant/osm_mcp_server.py)) — exposes `validate_spot`, `geocode`, `find_watersport_features`, `coastline_seaward_bearing` to *any* MCP client (Claude Desktop, the Inspector, or the pipeline). Run it: `mcp dev spot_consultant/osm_mcp_server.py`.
- **Skill ≠ tool.** A skill is *knowledge* (how to analyze a spot well); tools are *capabilities* (reach OSM, search the web). Keeping them separate is what makes the agent legible.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python cli.py "Mellsten, Espoo, Finland"   # mock mode — no API key needed
streamlit run app.py                        # same, with a UI

export ANTHROPIC_API_KEY=sk-ant-...         # live mode
export SPOT_MODEL=claude-haiku-4-5          # optional: cheapest model
python cli.py "Tarifa, Spain"

pytest                                       # geometry + guardrail + validation; live evals with a key
```

## Deploy (AWS)

Serverless MVP — one Lambda behind a Function URL, secrets in SSM, a cost budget, no VPC.
Full runbook in **[DEPLOY.md](DEPLOY.md)**; infra in [`infra/`](infra/) (SAM, Docker-free build).

## Layout

```
spot_consultant/       shared domain core — imported by every Lambda
  validation.py        OSM validation gate
  consultant.py        enrich_spot(): validate → analyze → extract → verify
  schema.py            SpotReport (the output contract)
  safety.py            deterministic geometry guardrail
  geo.py · osm.py      coastline math + OpenStreetMap client (mirror failover)
  osm_mcp_server.py    MCP server exposing the OSM tools
  config.py            shared secrets loader (SSM)
  skills/…/SKILL.md    the analysis playbook
  prompts.py · mock.py
functions/             one thin Lambda handler per function (multi-Lambda ready)
  enrich/              handler.py · requirements.txt · Makefile
infra/template.yaml    SAM stack — declares the functions + cost budget
cli.py · app.py        dev front-ends (import the core)
tests/                 geometry, guardrail, validation; live eval set
```

## License

[MIT](LICENSE) — copy freely.
