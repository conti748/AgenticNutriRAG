## ADDED Requirements

### Requirement: Interaction logging to Postgres
The system SHALL log every question/answer interaction to Postgres,
including the original question, rewritten query, retrieval strategy used,
retrieved FDC IDs, generated answer, latency, and timestamp.

#### Scenario: Interaction persisted
- **WHEN** the agent completes answering a user's question via the chat
  interface
- **THEN** a corresponding row is written to the interactions table in
  Postgres containing the question, answer, retrieval metadata, latency, and
  timestamp

### Requirement: Feedback logging
The system SHALL log user feedback (thumbs up/down) to Postgres, linked to
the interaction it applies to.

#### Scenario: Feedback persisted
- **WHEN** a user submits thumbs up or thumbs down in the chat interface
- **THEN** a corresponding row is written to Postgres referencing the
  original interaction's ID and the feedback value

### Requirement: Grafana dashboard with 5+ charts
The system SHALL provide a provisioned Grafana dashboard, connected to the
Postgres logging tables, containing at least 5 charts covering query volume
over time, feedback rate (thumbs up vs down), latency distribution,
retrieval strategy usage breakdown, and evaluation score trend over time.

#### Scenario: Dashboard loads with data
- **WHEN** Grafana is started against a Postgres instance containing logged
  interactions and feedback
- **THEN** the provisioned dashboard displays at least 5 populated charts
  covering the areas listed above, without manual panel configuration

### Requirement: Synthetic data seeding for demo purposes
The system SHALL provide a script that generates synthetic
question/answer/feedback interactions so the dashboard can be populated and
screenshotted without requiring real end users.

#### Scenario: Seed script populates dashboard
- **WHEN** the synthetic data seeding script is run against a fresh
  environment
- **THEN** the Grafana dashboard subsequently shows non-empty charts based
  on the seeded interactions
