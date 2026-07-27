"""Feedback capture hook for the chat interface.

Records thumbs up/down feedback on an agent answer, linked to the interaction it
applies to, in Postgres.
"""

import logging
from typing import Literal

from monitoring.db import get_connection, log_feedback

logger = logging.getLogger(__name__)

FeedbackValue = Literal["up", "down"]


def record_feedback(interaction_id: str, question: str, feedback: FeedbackValue) -> None:
    """Record a user's thumbs up/down feedback for a question/answer interaction."""
    log_feedback(get_connection(), interaction_id, feedback)
    logger.info(
        "feedback recorded: interaction_id=%s feedback=%s question=%r",
        interaction_id,
        feedback,
        question,
    )
