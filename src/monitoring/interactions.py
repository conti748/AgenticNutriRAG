"""Interaction logging hook for the chat interface.

Records every question/answer interaction (question, rewritten query, retrieval
strategy, retrieved FDC IDs, answer, latency, timestamp) to Postgres so the Grafana
dashboard has data to chart.
"""

import logging

from agent.models import AgentAnswer
from monitoring.db import get_connection, log_interaction

logger = logging.getLogger(__name__)


def record_interaction(
    interaction_id: str, question: str, answer: AgentAnswer, latency_ms: float
) -> None:
    """Persist one question/answer interaction to Postgres."""
    log_interaction(
        get_connection(),
        interaction_id,
        question,
        answer.rewritten_query,
        answer.retrieval_strategy,
        [source.fdc_id for source in answer.sources],
        answer.answer,
        latency_ms,
    )
    logger.info(
        "interaction recorded: id=%s strategy=%s latency_ms=%.1f",
        interaction_id,
        answer.retrieval_strategy,
        latency_ms,
    )
