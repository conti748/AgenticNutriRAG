## ADDED Requirements

### Requirement: Automated answer ground-truth generation
The system SHALL reuse or extend the retrieval evaluation's generated
question set with reference answers (LLM-generated from the source food
data) suitable for scoring generated answers against.

#### Scenario: Reference answers available for scoring
- **WHEN** the answer evaluation harness is run
- **THEN** each evaluation question has an associated reference answer
  derived from the underlying USDA data

### Requirement: Multi-approach answer scoring
The system SHALL score generated answers using at least two distinct
approaches — embedding cosine-similarity between generated and reference
answers, and LLM-as-judge scoring — and report results for each.

#### Scenario: Both scoring approaches run
- **WHEN** the answer evaluation harness is run against the agent's
  generated answers for the evaluation question set
- **THEN** it reports both a cosine-similarity score and an LLM-as-judge
  score (e.g. relevance/faithfulness rating) per answer, plus aggregate
  statistics across the set

### Requirement: Best approach selected and documented
The system SHALL document which answer-generation configuration (e.g.
retrieval strategy, prompt variant) scored best under the evaluation, and
that configuration SHALL be the one used by default in the live app.

#### Scenario: Evaluation informs default configuration
- **WHEN** the answer evaluation report identifies the best-scoring
  configuration
- **THEN** the README documents the comparison and states that this
  configuration is the one shipped as the default
