# Design decisions

The reasoning behind Windspotter's backend — written to show *judgment*, not just
code. Each entry is **Context → Decision → Why / trade-offs.** Several were driven by
things that actually went wrong while building, which are noted honestly.

---

### 1. Validate before you analyze
**Context:** the analysis step (an agentic web-research loop) costs real tokens and seconds.
**Decision:** a cheap OpenStreetMap **validation gate** runs first; inputs that aren't real spots short-circuit before any model call.
**Why:** cost control + quality. It also yields authoritative coordinates and shoreline orientation as a side effect. Rejected → stop; unknown (OSM down) → proceed without the grounding bonus rather than block.

### 2. Two phases: agentic research, then structured extraction
**Context:** I needed both open-ended web research *and* a strict typed result.
**Decision:** phase 1 is a tool-using agent (web search) that produces grounded findings; phase 2 forces those findings into a Pydantic schema via structured outputs.
**Why:** separation keeps each step independently testable and avoids mixing free-form tool use with strict output constraints in one call.

### 3. Structured outputs as the contract
**Decision:** the model must emit exactly `SpotReport` (Pydantic + Anthropic structured outputs).
**Why:** bad types and invented enum values fail at the API boundary, not three layers downstream. The schema *is* the interface.

### 4. A deterministic guardrail over model output ("trust by field")
**Context:** wind-sport metadata is safety-relevant — an offshore wind blows a rider out to sea.
**Decision:** treat the model's output as a draft. Compute shoreline orientation from OSM coastline geometry, and run a pure-geometry check that flags any "good" wind direction that's actually offshore. The model proposes; code disposes.
**Why:** an LLM can hallucinate a dangerous recommendation; compass geometry can't. Safety-critical fields earn verification or human review, not blind trust.

### 5. Verify the *authoritative* source too
**Context:** I assumed OSM-computed orientation should always override the model. Then a real test (Mellsten, Tarifa) showed OSM's *nearest-coastline-segment* heuristic picking the wrong shore in fragmented archipelagos — while the model's researched orientation was correct.
**Decision:** **cross-check** OSM vs. the model instead of blindly overriding. Agreement → high confidence; disagreement → keep lower confidence and flag for review.
**Why:** "authoritative" data has failure modes too. Found by testing on a real spot — exactly why the eval/observation loop matters.

### 6. Skill (knowledge) vs. tools (capabilities)
**Decision:** the analysis expertise lives in a `SKILL.md` *playbook* (loaded as the system prompt); OSM and web search are *tools*. The agent loop composes them.
**Why:** keeping "how to think like a spot analyst" separate from "what the agent can do" makes the system legible and each part independently improvable. The same `SKILL.md` could graduate to a formal Anthropic Agent Skill with no rewrite.

### 7. Discovery as a heuristic, not a hardcoded source list
**Context:** local clubs (e.g. surfing.fi) have the best spot data, but you can't hand-integrate a club per spot.
**Decision:** teach the agent the *heuristic* a human would use — "find the local club's spot guide, search in the local language, trust club > aggregator > blog" — and let it apply that per spot.
**Why:** encode the expert's instinct, not a database of URLs. It scales to any spot with O(1) human effort.

### 8. A 3-tier data strategy for scale
**Decision:** combine (1) **structured global** sources (OSM + weather APIs — every coordinate on Earth, automatic), (2) **agentic web synthesis** (high quality where the web is rich), and (3) **crowdsource/confirm** (the user, a local, confirms or corrects the long tail).
**Why:** no single source covers everything. For obscure spots the system is *honest* (low confidence + flag) and leans on the human. Each spot is analyzed **once and cached**, so cost scales with distinct spots, not requests.

### 9. Serverless on AWS, no VPC
**Decision:** Lambda + SSM + a budget, deployed with SAM, **no VPC**.
**Why:** in serverless the security boundary is *identity (IAM)*, not the *network*. Lambda has no inbound port; SSM/the Anthropic API are reached over HTTPS + IAM — there's nothing to put in a private subnet, and no VPC means no NAT-gateway cost. The one public surface (the Function URL) is hardened with an app-layer token + reserved concurrency.

### 10. Cost guardrails on day one
**Decision:** model defaults to **Haiku** (cents/call), web searches are capped (`max_uses`), Lambda reserved concurrency = 2, and an AWS Budget emails at 80% of $10.
**Why:** a public endpoint backed by a paid API needs a wallet fuse before it's live, not after.

### 11. Security hygiene throughout
**Decisions:** API key in SSM (never in code/env files); planned **keyless OIDC** for CI deploys (no long-lived AWS keys in GitHub); app-layer shared-secret on the public Function URL; and operationally — no personal credentials left on a corporate laptop being returned.
**Why:** the cheapest time to get secrets handling right is the first commit.

### 12. Designed, not built (on purpose)
For a portfolio, some things are worth *designing* but not *building*:
- **Payments** — App Store / Play Billing / Telegram Stars each mandate their own rail; a unified entitlement reconciles them server-side. Real, but store-billing plumbing isn't what a reviewer clicks.
- **Async scale** — the production shape is API Gateway → SQS → worker Lambda → DynamoDB + a poll endpoint (the sync Function URL MVP dodges API Gateway's 29 s cap for now).
- **Mobile clients & multi-region** — separate repos / later.

Documenting the design demonstrates understanding without sinking days into plumbing.

### 13. Model choice
**Decision:** default to the strongest model (`claude-opus-4-8`) for quality; switch to `claude-haiku-4-5` via `SPOT_MODEL` for cost-sensitive or demo runs.
**Why:** make the cost/quality lever explicit and configurable rather than hardcoding a compromise.
