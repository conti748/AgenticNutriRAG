## ADDED Requirements

### Requirement: Automated USDA data fetch
The system SHALL fetch food and nutrient data from the USDA FoodData Central
API (or bulk download) via a script that requires no manual/GUI steps,
authenticated with an API key supplied through environment configuration.

#### Scenario: Fresh ingestion run
- **WHEN** the ingestion script is run with a valid `USDA_API_KEY` and no
  existing local cache
- **THEN** it downloads the configured subset of food records (the
  Foundation Foods category) and stores them locally before indexing

#### Scenario: Missing API key
- **WHEN** the ingestion script is run without `USDA_API_KEY` set
- **THEN** it fails fast with a clear error message naming the missing
  environment variable, rather than proceeding or hanging

### Requirement: Elasticsearch index with hybrid fields
The system SHALL index each ingested food as one Elasticsearch document
containing: a natural-language description field for BM25 search, a dense
vector field (OpenAI embedding of that description) for kNN search, and a
structured nutrient object usable by the agent's lookup tool.

#### Scenario: Successful indexing
- **WHEN** ingestion completes for a food record
- **THEN** the corresponding Elasticsearch document contains a non-empty
  description field, a vector field of the expected embedding dimension, and
  a nutrients object with at least calories, protein, fat, and carbohydrate
  values

#### Scenario: Re-running ingestion is idempotent
- **WHEN** the ingestion script is run a second time against the same source
  data and target index
- **THEN** the index ends up with the same set of documents (no duplicates),
  identified by a stable ID derived from the USDA FDC ID

### Requirement: One-command ingestion pipeline
The system SHALL provide a single command (script or `docker-compose run`
job) that performs fetch, transform, embed, and index end-to-end without
requiring manual intervention between steps.

#### Scenario: End-to-end run
- **WHEN** an operator runs the documented ingestion command against an
  empty Elasticsearch instance
- **THEN** the target index exists afterward and its document count matches
  the number of foods in the configured USDA subset, with no manual steps
  required in between
