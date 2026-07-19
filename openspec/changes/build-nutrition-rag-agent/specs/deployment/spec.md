## ADDED Requirements

### Requirement: Single-command full-stack startup
The system SHALL provide a `docker-compose.yml` that starts the Streamlit
app, Elasticsearch, Postgres, and Grafana together with a single
`docker-compose up` command, after environment variables are configured.

#### Scenario: Fresh environment startup
- **WHEN** an operator with Docker installed clones the repository, sets the
  required environment variables, and runs `docker-compose up`
- **THEN** all services (app, Elasticsearch, Postgres, Grafana) start
  successfully and the Streamlit app becomes reachable in a browser

### Requirement: One-command ingestion within the containerized stack
The system SHALL provide a way to run the ingestion pipeline as part of (or
alongside) the docker-compose stack, without requiring the operator to
install Python dependencies on their host machine.

#### Scenario: Ingestion via compose
- **WHEN** an operator runs the documented ingestion command (e.g.
  `docker-compose run ingestion`) against the running Elasticsearch service
- **THEN** the target Elasticsearch index is populated without any
  host-installed Python dependencies beyond Docker itself

### Requirement: Documented configuration and versions
The system SHALL document all required environment variables (API keys,
credentials) in a `.env.example` file, and SHALL pin service image versions
in `docker-compose.yml` so the stack is reproducible.

#### Scenario: New operator reproduces the stack
- **WHEN** a new operator copies `.env.example` to `.env`, fills in their own
  API keys, and follows the README
- **THEN** they can bring up the exact same stack (same service versions) as
  described, with no undocumented manual steps
