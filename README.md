# AgenticNutriRAG

## Dataset

Nutrition data comes from the [USDA FoodData Central](https://fdc.nal.usda.gov/)
API. Ingestion is scoped to the **Foundation Foods** data type only (394
records as of this API snapshot) rather than the full FoodData Central corpus
(300k+ records across Foundation, SR Legacy, Survey (FNDDS), and Branded
types). This bounds embedding cost/time and keeps the dataset's nutrient data
high-quality (Foundation Foods are lab-analyzed, not self-reported or
aggregated).

Run the ingestion pipeline with:

```bash
uv run python -m ingestion.pipeline
```

It fetches every Foundation Foods record via the USDA API (paginated),
flattens each into a description string plus a structured nutrient object,
embeds the description with the OpenAI embeddings API, and indexes it into
Elasticsearch (index `usda_foods`) using the FDC ID as a stable document ID
so re-running the ingestion is idempotent. Verified end-to-end against a live
Elasticsearch 8.15.0 instance: 394/394 Foundation Foods indexed, re-running
produces the same document count (no duplicates).

**Known data gap**: USDA doesn't report an energy/calorie value for every
Foundation Foods record (about 18% in the current snapshot lack one under any
of the numbers checked - `208`, `957`, `958`). Those documents get
`calories_kcal: 0.0` rather than a fabricated estimate.

## Retrieval Evaluation

Retrieval quality is evaluated offline against an LLM-generated ground-truth
set: 30 foods are sampled from the index (seeded, so the sample is
reproducible) and an LLM writes one plausible user question per food, giving
(question, expected FDC ID) pairs with no manual labeling. Degenerate
questions (too short, refusal-like, or duplicate) are dropped automatically
as a stand-in for manual spot-checking, then a sample is read by hand to
confirm quality before use.

Questions are deliberately adversarial to lexical/exact-name matching: the
generator is instructed to never restate a food's exact name or category
string, and to describe it indirectly (a synonym, its preparation/variety, a
common use) while still including enough distinguishing detail to identify
that one food. It also favors less obvious nutrients (a vitamin, mineral,
fiber, sugar) over always asking about calories/protein, so a strategy can't
win purely by echoing the indexed description text back at itself. An
earlier, more literal prompt version produced near-100% hit rate for every
strategy — not because retrieval was that good, but because the questions
paraphrased the indexed text too closely to be a meaningful test.

Run it with:

```bash
uv run python -m eval.retrieval_eval
```

It generates/reuses `data/eval/ground_truth.json`, evaluates every
retrieval-strategy (`text_only` / `vector_only` / `hybrid`) x query-rewriting
(on/off) combination using hit rate and MRR, and writes
`data/eval/retrieval_report.md`. Latest run:

| Strategy | Query Rewriting | Hit Rate | MRR |
|---|---|---|---|
| hybrid | on | 0.867 | 0.711 |
| vector_only | on | 0.867 | 0.672 |
| text_only | on | 0.767 | 0.588 |
| vector_only | off | 0.800 | 0.548 |
| hybrid | off | 0.633 | 0.501 |
| text_only | off | 0.533 | 0.359 |

**Default: hybrid retrieval with query rewriting on**
(`RETRIEVAL_STRATEGY=hybrid`, `QUERY_REWRITING_ENABLED=true`, see
`src/config.py`) — the outright best combination on this harder ground-truth
set, not a tie-break. Two things stand out: query rewriting helps every
single strategy (rewriting-on beats rewriting-off in all three pairs), since
it turns the indirect, paraphrased questions back into keyword-ish search
queries closer to the indexed text; and hybrid only barely edges out
`vector_only` alone, because RRF-fusing in `text_only`'s noisier results
(0.533 hit rate on its own) partially offsets the gain from BM25's real hits.

**Known limitation surfaced by this evaluation**: the indexed `search_text`
field (see `ingestion/transform.py`) only contains the food's name, category,
and the four core macros (calories/protein/fat/carbs) — vitamins and
minerals like iron or vitamin C are stored in the structured `nutrients`
field but are never embedded or indexed for text search. Questions about
those nutrients can only be answered via loose semantic association (e.g.
"orange-colored fruit" implying vitamin C), not any indexed fact. Enriching
`search_text` with the full core nutrient set would likely raise scores
further and is a natural follow-up if retrieval on micro-nutrient questions
matters for this project.

## Answer Evaluation

Generated-answer quality is evaluated with two independent scoring approaches
against the same LLM-generated ground-truth set used for retrieval
evaluation, extended with one LLM-generated reference answer per question
(grounded in that question's expected food's full nutrient data, so the
reference is factually anchored rather than free-form):

- **Embedding cosine similarity** between the agent's generated answer and
  the reference answer (`text-embedding-3-small`) — cheap, purely semantic.
- **LLM-as-judge** — a 1-5 relevance/faithfulness rating of the generated
  answer against the reference, from the same chat model used elsewhere in
  the project.

Query rewriting is held fixed at its already-chosen default (on, see
Retrieval Evaluation above) and only retrieval strategy is swept, since
re-testing rewriting here would duplicate what retrieval evaluation already
settled. Run it with:

```bash
uv run python -m eval.answer_eval
```

It generates/reuses `data/eval/answer_ground_truth.json`, runs the live
agent for every question under each retrieval strategy, scores every answer
both ways, and writes `data/eval/answer_report.md`. Latest run (30
questions):

| Strategy | Cosine Similarity | LLM Judge |
|---|---|---|
| vector_only | 0.824 | 4.367 |
| hybrid | 0.822 | 4.067 |
| text_only | 0.813 | 3.900 |

**Default stays hybrid retrieval** (`RETRIEVAL_STRATEGY=hybrid`, see
`src/config.py`), unchanged from the retrieval-evaluation pick, even though
`vector_only` scores marginally higher here. Two reasons: the gap is small
on a 30-question set (0.824 vs 0.822 cosine; the LLM judge gap is more
visible but the same 30 answers are used across all three rows, so it isn't
an independent confirmation) — and, more importantly, retrieval evaluation
measures whether the *right food is found at all* (hybrid's MRR 0.711 vs
vector_only's 0.672, a larger and more reliable margin), which bounds
answer quality far more than the generation step does: if the wrong food is
retrieved, no amount of answer-generation polish recovers a correct answer.
Answer evaluation here is read as confirming hybrid produces answers that
are competitive with — not worse than — the alternatives, rather than as a
reason to override the retrieval-evaluation pick.
