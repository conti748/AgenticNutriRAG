## ADDED Requirements

### Requirement: Query rewriting
The system SHALL rewrite the user's natural-language question into a
search-optimized query string via an LLM call before retrieval, and SHALL
support running with rewriting disabled (raw user question used directly)
for comparison/evaluation purposes.

#### Scenario: Conversational question rewritten for search
- **WHEN** a user asks "what should I eat if I want more protein but not a
  ton of calories?"
- **THEN** the system produces a rewritten query string better suited to
  retrieval (e.g. naming protein-dense, lower-calorie food terms) before
  passing it to the retrieval step

#### Scenario: Rewriting can be disabled
- **WHEN** the agent is configured with query rewriting turned off
- **THEN** the original user question is passed directly to the retrieval
  step unmodified

### Requirement: Hybrid retrieval
The system SHALL retrieve candidate food documents from Elasticsearch using
a hybrid query that combines BM25 text matching and kNN dense-vector
similarity (reciprocal rank fusion), and SHALL also support text-only and
vector-only retrieval modes for evaluation comparison.

#### Scenario: Hybrid retrieval returns ranked candidates
- **WHEN** the agent issues a retrieval request for a rewritten query
- **THEN** it receives an ordered list of candidate foods produced by
  combining BM25 and kNN results, each with an FDC ID and score

#### Scenario: Retrieval mode is switchable
- **WHEN** the retrieval strategy is configured as `text_only`,
  `vector_only`, or `hybrid`
- **THEN** the system executes the corresponding Elasticsearch query type
  and returns results without requiring code changes elsewhere in the agent

### Requirement: Tool-calling for nutrient detail
The system SHALL expose a tool to the LLM (e.g. `lookup_food_nutrients`)
that the model can call with an FDC ID to retrieve full structured nutrient
data beyond what's in the retrieved summary, before composing its final
answer.

#### Scenario: Model calls the lookup tool
- **WHEN** the LLM determines it needs detailed nutrient values (e.g. a
  specific vitamin) for a food returned by retrieval
- **THEN** it calls the `lookup_food_nutrients` tool with that food's FDC ID
  and receives the structured nutrient object in response before continuing

### Requirement: Grounded answer generation
The system SHALL generate the final answer using only the retrieved and
tool-fetched context (not the model's unaided prior knowledge), and SHALL
cite the specific food(s) used to answer the question.

#### Scenario: Answer cites sources
- **WHEN** the agent produces a final answer to a nutrition question
- **THEN** the answer text references the specific food name(s)/FDC ID(s)
  retrieved and used, so a user can trace the claim back to source data

#### Scenario: No relevant data found
- **WHEN** retrieval returns no candidates above a minimum relevance
  threshold for the user's question
- **THEN** the agent responds that it could not find relevant nutrition data
  rather than fabricating an answer
