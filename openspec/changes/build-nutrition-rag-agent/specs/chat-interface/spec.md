## ADDED Requirements

### Requirement: Streamlit question/answer interaction
The system SHALL provide a Streamlit web app where a user can type a
nutrition question, submit it, and see the agent's generated answer
displayed in the page.

#### Scenario: User asks a question and sees an answer
- **WHEN** a user types a nutrition question into the Streamlit input and
  submits it
- **THEN** the app displays the agent's grounded answer, including the
  source food(s) it cites, without requiring a page reload

### Requirement: Feedback capture
The system SHALL let the user submit thumbs up/down feedback on each
displayed answer, and SHALL persist that feedback (linked to the
originating question/answer) for use by the monitoring capability.

#### Scenario: User submits feedback
- **WHEN** a user clicks thumbs up or thumbs down under a displayed answer
- **THEN** the app records that feedback value associated with that specific
  question/answer interaction

### Requirement: Visible latency / in-progress state
The system SHALL show the user a loading indicator while the agent is
processing a question, so the app does not appear unresponsive during
retrieval and generation.

#### Scenario: Long-running query shows progress
- **WHEN** a submitted question is still being processed by the agent
- **THEN** the UI displays a visible loading/progress indicator until the
  answer is ready
