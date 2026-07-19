## Why

This is the final project for the DataTalksClub LLM Zoomcamp course, graded
against `project.md`'s rubric. The course covers agentic RAG, evaluation, and
monitoring; the project must demonstrate all three end-to-end on a dataset
other than the course FAQ. AgenticNutriRAG targets nutrition questions over
the USDA FoodData Central dataset — a domain with structured, factual data
well-suited to tool-calling and hybrid retrieval, and rich enough to support
meaningful retrieval/answer evaluation.

## What Changes

- Build a fully automated ingestion pipeline that pulls food/nutrient records
  from USDA FoodData Central and indexes them into Elasticsearch with both a
  BM25 text field and a dense vector field (OpenAI embeddings).
- Build an agentic RAG flow: query rewriting, hybrid (text + vector) retrieval
  against Elasticsearch, tool-calling (e.g. structured nutrient lookups/
  comparisons), and answer generation with an OpenAI chat model.
- Build an offline retrieval evaluation harness comparing multiple retrieval
  strategies (text-only, vector-only, hybrid) with metrics like hit rate and
  MRR, and select the best-performing one.
- Build an offline + online LLM answer evaluation harness comparing multiple
  approaches (e.g. embedding-similarity scoring and LLM-as-judge) and select
  the best-performing one.
- Build a Streamlit chat interface for end users to ask nutrition questions
  and see grounded answers with sources.
- Build a monitoring stack: log every query/answer/feedback event to
  Postgres, expose a thumbs up/down feedback control in the UI, and ship a
  Grafana dashboard with 5+ charts (e.g. query volume, feedback rate,
  latency, retrieval strategy usage, evaluation scores over time).
- Containerize everything (app, Elasticsearch, Postgres, Grafana) with a
  single `docker-compose` so the whole stack is reproducible with one
  command.

## Capabilities

### New Capabilities
- `nutrition-data-ingestion`: fully automated pipeline that fetches USDA
  FoodData Central data and indexes it into Elasticsearch (BM25 + vector
  fields).
- `nutrition-rag-agent`: the core agentic flow — query rewriting, hybrid
  retrieval, tool-calling, and grounded answer generation via OpenAI.
- `retrieval-evaluation`: offline evaluation comparing multiple retrieval
  strategies and selecting the best one.
- `answer-evaluation`: evaluation of generated answers using multiple
  approaches, with the best one selected and documented.
- `chat-interface`: the Streamlit web app end users interact with, including
  feedback controls.
- `monitoring`: event/feedback logging to Postgres and a Grafana dashboard
  with 5+ charts.
- `deployment`: docker-compose packaging of the full stack for one-command
  reproducibility.

### Modified Capabilities
(none — this is a greenfield project, no existing specs)

## Impact

- New Python codebase: ingestion scripts, agent/RAG pipeline, evaluation
  scripts/notebooks, Streamlit app, monitoring/logging integration.
- New infrastructure: Elasticsearch (knowledge base), Postgres (logs/
  feedback), Grafana (dashboards), all defined in `docker-compose.yml`.
- External dependency: OpenAI API (chat + embeddings) — requires an API key
  and incurs usage cost. USDA FoodData Central API — requires a (free) API
  key for ingestion.
- New documentation: README with setup/reproduction instructions, dataset
  description, architecture diagram, and evaluation results — required for
  the "Reproducibility" and "Problem Description" rubric criteria.
