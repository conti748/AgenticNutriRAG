## 1. Project Scaffolding

- [x] 1.1 Set up Python project structure (e.g. `src/` with `ingestion/`,
      `agent/`, `eval/`, `app/`, `monitoring/` packages) and dependency
      management with `uv` (`uv init`, `pyproject.toml` + `uv.lock`)
- [x] 1.2 Add `.env.example` listing `OPENAI_API_KEY`, `USDA_API_KEY`,
      `ELASTICSEARCH_URL`, `POSTGRES_*`, `GRAFANA_*`
- [x] 1.3 Add a config module that loads and validates required environment
      variables, failing fast with clear errors when missing
- [x] 1.4 Configure `ruff` (lint + format) in `pyproject.toml`
- [x] 1.5 Configure `mypy` in `pyproject.toml`
- [x] 1.6 Configure `pytest` (test discovery/paths) in `pyproject.toml` and
      add a `tests/` package with a placeholder test
- [x] 1.7 Set up `pre-commit` (`.pre-commit-config.yaml`) with hooks for
      `ruff` (lint + format), `mypy`, and standard hygiene checks
      (trailing whitespace, end-of-file, YAML/TOML syntax)
- [x] 1.8 Add a minimal `.gitlab-ci.yml` with stages for lint (`ruff`,
      `mypy`) and test (`pytest`), running via `uv`
- [x] 1.9 Verify: `pre-commit run --all-files` and the GitLab CI pipeline
      both pass on a clean checkout

## 2. Data Ingestion Pipeline (`nutrition-data-ingestion`)

- [x] 2.1 Write a USDA FoodData Central client (fetch by category/subset,
      handle pagination and the API key)
- [x] 2.2 Document the ingested subset (Foundation Foods only) to bound
      embedding cost/time
- [x] 2.3 Write a transform step that flattens each food record into a
      description string + structured nutrient object (calories, macros,
      key vitamins/minerals)
- [x] 2.4 Write the Elasticsearch index mapping: text field, dense vector
      field, nutrient object field
- [x] 2.5 Write the embedding step (OpenAI embeddings API) for each food's
      description field
- [x] 2.6 Write the indexing step using a stable ID derived from FDC ID
      (idempotent re-runs, no duplicates)
- [x] 2.7 Wire fetch → transform → embed → index into a single runnable
      ingestion script/entrypoint
- [x] 2.8 Verify: run ingestion against an empty index and confirm document
      count matches the configured subset

## 3. Agentic RAG Flow (`nutrition-rag-agent`)

- [ ] 3.1 Implement the query rewriting function (LLM call), with a
      config flag to disable it and pass the raw question through
- [ ] 3.2 Implement text-only, vector-only, and hybrid (RRF) Elasticsearch
      query functions behind a single retrieval interface selected by config
- [ ] 3.3 Implement the `lookup_food_nutrients(fdc_id)` tool function and
      register it with the OpenAI tool-calling API
- [ ] 3.4 Implement the agent loop: rewrite → retrieve → let the model call
      tools as needed → generate a grounded, source-citing answer
- [ ] 3.5 Handle the no-relevant-results case (return a clear "not found"
      response instead of fabricating an answer)
- [ ] 3.6 Add a minimal test/script exercising the full agent loop against
      the real (or a test) Elasticsearch index with a handful of sample
      questions

## 4. Retrieval Evaluation (`retrieval-evaluation`)

- [ ] 4.1 Write the ground-truth generator: sample indexed foods, use an LLM
      to produce plausible questions per food, save (question, FDC ID) pairs
- [ ] 4.2 Spot-check and filter the generated ground-truth set for quality
- [ ] 4.3 Implement hit rate and MRR metrics
- [ ] 4.4 Run the evaluation across text-only / vector-only / hybrid, each
      with rewriting on/off, and produce a comparison report/table
- [ ] 4.5 Pick the best-performing strategy/rewriting combination and set it
      as the agent's default configuration

## 5. Answer Evaluation (`answer-evaluation`)

- [ ] 5.1 Extend the ground-truth set with LLM-generated reference answers
      per question
- [ ] 5.2 Implement embedding cosine-similarity scoring between generated
      and reference answers
- [ ] 5.3 Implement LLM-as-judge scoring (relevance/faithfulness rubric)
- [ ] 5.4 Run both scoring approaches against the agent's answers for the
      evaluation set and produce a comparison report
- [ ] 5.5 Document the selected best-scoring configuration and confirm it
      matches what's shipped as the default

## 6. Streamlit Chat Interface (`chat-interface`)

- [ ] 6.1 Build the question input + submit flow calling the agent
- [ ] 6.2 Display the generated answer with cited source foods
- [ ] 6.3 Add a loading/progress indicator while the agent is processing
- [ ] 6.4 Add thumbs up/down feedback controls per answer, wired to the
      monitoring capability's feedback logging
- [ ] 6.5 Manual pass: run the app locally and verify the golden path
      (ask → answer → feedback) and an edge case (no relevant data found)

## 7. Monitoring (`monitoring`)

- [ ] 7.1 Design and create the Postgres schema (interactions table,
      feedback table)
- [ ] 7.2 Wire interaction logging into the agent/app flow (question,
      rewritten query, strategy, retrieved FDC IDs, answer, latency,
      timestamp)
- [ ] 7.3 Wire feedback logging into the Streamlit feedback controls
- [ ] 7.4 Provision a Grafana datasource pointing at Postgres
- [ ] 7.5 Build the 5+ panel dashboard (query volume, feedback rate,
      latency distribution, retrieval strategy usage, evaluation score
      trend) as a provisioned Grafana dashboard JSON
- [ ] 7.6 Write a synthetic data seeding script and verify the dashboard
      renders populated charts from it

## 8. Containerization (`deployment`)

- [ ] 8.1 Write Dockerfile(s) for the app and ingestion job
- [ ] 8.2 Write `docker-compose.yml` with app, elasticsearch, postgres,
      grafana (+ provisioning mounts), pinning image versions
- [ ] 8.3 Wire the ingestion job as a `docker-compose run`-able service
- [ ] 8.4 Verify: fresh `docker-compose up` from a clean environment brings
      up all services and the app becomes reachable

## 9. Documentation & Reproducibility

- [ ] 9.1 Write the README: problem description, architecture diagram,
      dataset description, setup/reproduction instructions, versions
- [ ] 9.2 Document retrieval and answer evaluation results and the chosen
      defaults
- [ ] 9.3 Document the bonus points implemented (hybrid search, query
      rewriting) and how to verify them
- [ ] 9.4 Add screenshots of the Streamlit app and the Grafana dashboard
- [ ] 9.5 Final end-to-end check: clone-to-running-app following only the
      README, on a clean checkout
