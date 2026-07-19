## Context

Greenfield project, no existing code or specs. This is the LLM Zoomcamp final
project and will be graded against `project.md`'s rubric (0-2 points per
criterion across problem description, retrieval flow, retrieval evaluation,
LLM evaluation, interface, ingestion, monitoring, containerization,
reproducibility, plus bonus points). The design below is chosen to hit 2/2 on
every core criterion with the least incidental complexity, while leaving room
for the two targeted bonus points (hybrid search, query rewriting).

## Goals / Non-Goals

**Goals:**
- A single, coherent pipeline: USDA FoodData Central → Elasticsearch (hybrid
  index) → agentic retrieval/generation → Streamlit UI → logged to
  Postgres → visualized in Grafana.
- Fully automated, one-command ingestion and one-command deployment
  (`docker-compose up`).
- Retrieval and answer evaluation that produce a comparison table with a
  clearly justified "best" choice, wired into the default app config.
- Enough monitoring data (from real or synthetic usage) to populate a 5+
  chart Grafana dashboard.

**Non-Goals (for this change; may become follow-up changes):**
- Re-ranking models, cloud deployment, and other bonus items beyond hybrid
  search + query rewriting.
- Multi-turn conversational memory beyond what's needed for a single Q&A
  turn with optional follow-up tool calls.
- Support for arbitrary/custom food databases beyond USDA FoodData Central.
- Authentication/multi-user support in the Streamlit app.

## Decisions

### 1. Data model: index USDA foods as one document per food item
Each Elasticsearch document represents one food (FDC ID) with a flattened
set of core nutrients (calories, macros, key vitamins/minerals) plus a
generated natural-language description field used for both BM25 and
embedding. Full nutrient detail (all ~150 nutrients USDA tracks) is stored as
a nested/object field for tool-calling lookups, not crammed into the
embedded text.
- **Alternative considered**: one document per (food, nutrient) pair —
  rejected, it multiplies document count ~150x and makes "compare food A vs
  B" queries harder to retrieve as a single hit.

### 2. Retrieval: Elasticsearch hybrid (BM25 + kNN dense vector), combined via RRF
Elasticsearch's native `rank` hybrid query (reciprocal rank fusion of a BM25
query and a kNN query) is used instead of a separate vector DB. This
directly implements the "hybrid search" bonus point without adding another
moving part to the stack.
- **Alternative considered**: separate vector DB (Qdrant/Chroma) + BM25 via
  Postgres full-text — rejected, doubles infra for no benefit given
  Elasticsearch supports both natively.

### 3. Agent flow: single OpenAI chat model with one tool, not a multi-agent framework
The agent loop is: (1) optionally rewrite the user's query for retrieval,
(2) run hybrid retrieval to get candidate foods, (3) expose a
`lookup_food_nutrients(fdc_id)` tool for the model to pull full nutrient
detail on demand, (4) generate a grounded answer citing the foods used.
Implemented directly with the OpenAI SDK's tool-calling, no LangChain/
LlamaIndex/agent-framework dependency.
- **Why**: the course's rubric rewards "retrieve context, optionally call
  tools, build the prompt, send to LLM" — a thin, explicit implementation is
  easier to evaluate and debug than a framework's black-box agent loop.
- **Alternative considered**: LangChain agent executor — rejected for this
  project's scope; adds an abstraction layer without clear benefit for a
  single-tool flow.
- **Decision**: `lookup_food_nutrients` is the only tool exposed to the
  model. No `compare_foods` or other additional tools — comparisons are
  handled by the model reasoning over multiple `lookup_food_nutrients` calls
  and the retrieved candidates, keeping the tool surface minimal.

### 4. Query rewriting as a separate, evaluable step
Query rewriting is implemented as its own function (LLM call that turns a
conversational question into a search-optimized query string), evaluated
independently in the retrieval-evaluation harness (with rewriting on vs
off) rather than folded invisibly into the agent. This makes the bonus point
demonstrable and measurable.

### 5. Evaluation: offline ground-truth generation, not manual labeling
Retrieval and answer evaluation both start from an LLM-generated set of
question/expected-food(s) pairs (sampled from the ingested USDA data),
following the standard LLM Zoomcamp evaluation pattern. This keeps
evaluation fully automated and reproducible without manual annotation.
- Retrieval evaluation compares: text-only, vector-only, hybrid (with and
  without query rewriting) using hit rate and MRR.
- Answer evaluation compares: embedding cosine-similarity scoring vs
  LLM-as-judge scoring, on the same generated question set.

### 6. Monitoring stack: Postgres for events, Grafana for dashboards
Every request (question, rewritten query, retrieved food IDs, retrieval
strategy, answer, latency, user feedback) is written to a Postgres table.
Grafana connects to Postgres directly (no separate metrics pipeline) and
renders 5+ panels: query volume over time, feedback (thumbs up/down) rate,
latency distribution, retrieval strategy usage, and evaluation score trend.
- **Alternative considered**: Prometheus + Grafana — rejected, Postgres is
  simpler for this scale and the course's own monitoring module uses this
  same pattern.

### 7. Containerization: docker-compose with 5 services
`app` (Streamlit), `elasticsearch`, `postgres`, `grafana`, and an `ingestion`
service/job that populates Elasticsearch on first run. All configuration
(OpenAI key, USDA API key, DB credentials) via `.env`, documented in the
README.

## Risks / Trade-offs

- [OpenAI API cost/rate limits during embedding of the full USDA dataset] →
  Mitigation: ingest only the "Foundation Foods" category (~2,000 items)
  rather than the entire FoodData Central corpus (300k+ items), documented
  as a deliberate scope choice.
- [Elasticsearch hybrid/RRF query syntax varies by ES version] → Mitigation:
  pin the Elasticsearch Docker image version in docker-compose and document
  it; write an integration smoke test for the hybrid query at that version.
- [LLM-generated ground truth for evaluation may contain low-quality or
  ambiguous question/answer pairs] → Mitigation: spot-check a sample
  manually and filter out degenerate cases before using it as the eval set.
- [Grafana dashboard has little data without real users] → Mitigation:
  include a small script to replay/generate synthetic queries so the
  dashboard is populated for demo/screenshot purposes.

## Open Questions

None — the ingestion scope (Foundation Foods only, see Risks / Trade-offs)
and the agent's tool surface (`lookup_food_nutrients` only, see Decision 3)
have been finalized.
