"""Seed Postgres with synthetic interactions, feedback, and evaluation runs.

Populates the monitoring tables with plausible-looking data so the Grafana
dashboard (monitoring/grafana/dashboards/nutrirag-overview.json) has something to
chart without requiring real end users. Safe to run repeatedly against a fresh
environment.

Usage:
    uv run python scripts/seed_monitoring_data.py
    uv run python scripts/seed_monitoring_data.py --days 14 --interactions-per-day 40
"""

import argparse
import logging
import random
import uuid
from datetime import UTC, datetime, timedelta

import psycopg

from config import RetrievalStrategy
from monitoring.db import get_connection, log_evaluation_run, log_feedback, log_interaction

logger = logging.getLogger(__name__)

STRATEGIES: list[RetrievalStrategy] = ["text_only", "vector_only", "hybrid"]

QUESTIONS_AND_ANSWERS = [
    ("How much protein is in an egg?", "A large egg contains about 6 grams of protein."),
    (
        "What's a good low-calorie source of fiber?",
        "Raspberries are a good low-calorie source of fiber, at about 6.5g per 100g.",
    ),
    (
        "What foods are high in iron?",
        "Beef liver and spinach are both notably high in iron.",
    ),
    (
        "How many calories are in a banana?",
        "A medium banana has roughly 105 calories.",
    ),
    (
        "Which foods are rich in vitamin C?",
        "Bell peppers and citrus fruits are rich sources of vitamin C.",
    ),
]

EVALUATION_METRICS = ["hit_rate", "mrr", "cosine_similarity", "llm_judge_score"]
# Rough baseline per strategy so the seeded trend reflects hybrid being the best
# performer, matching the retrieval/answer evaluation reports (data/eval/*_report.md).
STRATEGY_METRIC_BASELINE: dict[str, dict[str, float]] = {
    "text_only": {
        "hit_rate": 0.65,
        "mrr": 0.55,
        "cosine_similarity": 0.75,
        "llm_judge_score": 0.6,
    },
    "vector_only": {
        "hit_rate": 0.72,
        "mrr": 0.6,
        "cosine_similarity": 0.8,
        "llm_judge_score": 0.68,
    },
    "hybrid": {
        "hit_rate": 0.85,
        "mrr": 0.74,
        "cosine_similarity": 0.87,
        "llm_judge_score": 0.8,
    },
}


def _random_timestamp(now: datetime, days: int) -> datetime:
    offset = timedelta(days=random.uniform(0, days), hours=random.uniform(0, 24))
    return now - offset


def seed_interactions_and_feedback(
    conn: psycopg.Connection, now: datetime, days: int, interactions_per_day: int
) -> int:
    """Insert synthetic interactions, each with a chance of thumbs up/down feedback."""
    count = 0
    for _ in range(days * interactions_per_day):
        question, answer_text = random.choice(QUESTIONS_AND_ANSWERS)
        strategy = random.choice(STRATEGIES)
        created_at = _random_timestamp(now, days)
        interaction_id = str(uuid.uuid4())

        log_interaction(
            conn,
            interaction_id,
            question,
            question,
            strategy,
            random.sample(range(1_000_000, 2_000_000), k=random.randint(1, 5)),
            answer_text,
            latency_ms=random.gauss(1200, 300),
            created_at=created_at,
        )
        count += 1

        if random.random() < 0.6:
            feedback_value = "up" if random.random() < 0.8 else "down"
            log_feedback(
                conn,
                interaction_id,
                feedback_value,
                created_at=created_at + timedelta(seconds=random.uniform(1, 30)),
            )
    return count


def seed_evaluation_runs(conn: psycopg.Connection, now: datetime, days: int) -> int:
    """Insert one evaluation run per strategy/metric/day, trending toward the baseline."""
    count = 0
    for day_offset in range(days, 0, -1):
        created_at = now - timedelta(days=day_offset)
        # Earlier runs score a bit lower, so the trend line shows improvement over time.
        progress = 1.0 - (day_offset / days) * 0.15
        for strategy, metrics in STRATEGY_METRIC_BASELINE.items():
            for metric_name, baseline in metrics.items():
                value = max(0.0, min(1.0, baseline * progress + random.uniform(-0.02, 0.02)))
                log_evaluation_run(
                    conn,
                    strategy,
                    metric_name,
                    value,
                    created_at=created_at,
                )
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Number of days of history to seed")
    parser.add_argument(
        "--interactions-per-day", type=int, default=30, help="Synthetic interactions per day"
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.seed is not None:
        random.seed(args.seed)

    conn = get_connection()
    now = datetime.now(UTC)

    interaction_count = seed_interactions_and_feedback(
        conn, now, args.days, args.interactions_per_day
    )
    logger.info("Seeded %d interactions (with feedback) over %d days", interaction_count, args.days)

    evaluation_count = seed_evaluation_runs(conn, now, args.days)
    logger.info("Seeded %d evaluation run rows over %d days", evaluation_count, args.days)


if __name__ == "__main__":
    main()
