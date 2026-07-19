## ADDED Requirements

### Requirement: Automated ground-truth question generation
The system SHALL automatically generate a labeled evaluation set of
(question, expected FDC ID(s)) pairs by sampling indexed foods and using an
LLM to produce plausible user questions for each, without manual labeling.

#### Scenario: Ground-truth set generated from index
- **WHEN** the retrieval evaluation harness is run against a populated
  Elasticsearch index
- **THEN** it produces a saved dataset of question/expected-food-ID pairs
  covering a representative sample of the indexed foods

### Requirement: Multi-strategy retrieval comparison
The system SHALL evaluate at least text-only, vector-only, and hybrid
retrieval strategies (each with query rewriting on and off) against the
ground-truth set, computing hit rate and MRR for each combination.

#### Scenario: Comparison table produced
- **WHEN** the retrieval evaluation harness is run to completion
- **THEN** it outputs a table/report listing hit rate and MRR for each
  retrieval strategy and rewriting on/off combination evaluated

### Requirement: Best strategy selected and wired into the app
The system SHALL document which retrieval strategy configuration performed
best on the ground-truth set and SHALL set that configuration as the
default used by the live agent.

#### Scenario: Default matches evaluation winner
- **WHEN** the retrieval evaluation report identifies the best-performing
  strategy/rewriting combination
- **THEN** the agent's default runtime configuration uses that same
  strategy and rewriting setting, and the README documents why
