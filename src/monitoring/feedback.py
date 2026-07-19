"""Feedback capture hook for the chat interface.

Records thumbs up/down feedback on an agent answer. This currently logs only;
task 7.3 (Postgres feedback logging) replaces the body with a real write,
keeping this call site in the app unchanged.
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

FeedbackValue = Literal["up", "down"]


def record_feedback(interaction_id: str, question: str, feedback: FeedbackValue) -> None:
    """Record a user's thumbs up/down feedback for a question/answer interaction."""
    logger.info(
        "feedback recorded: interaction_id=%s feedback=%s question=%r",
        interaction_id,
        feedback,
        question,
    )
