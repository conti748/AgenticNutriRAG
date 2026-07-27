"""Postgres connection and schema for interaction/feedback/evaluation logging.

Three tables back the Grafana dashboard (see monitoring/grafana/): ``interactions``
(one row per question answered), ``feedback`` (thumbs up/down, linked to an
interaction), and ``evaluation_runs`` (retrieval/answer evaluation metric results,
so the dashboard can chart evaluation score trends over time).
"""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from functools import lru_cache

import psycopg

from config import get_settings

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS interactions (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    rewritten_query TEXT NOT NULL,
    retrieval_strategy TEXT NOT NULL,
    retrieved_fdc_ids INTEGER[] NOT NULL,
    answer TEXT NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    interaction_id UUID NOT NULL REFERENCES interactions(id),
    value TEXT NOT NULL CHECK (value IN ('up', 'down')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id SERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def connect() -> psycopg.Connection:
    """Open a new Postgres connection using settings from the environment."""
    settings = get_settings()
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )


def init_schema(conn: psycopg.Connection) -> None:
    """Create the monitoring tables if they don't already exist."""
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()


@lru_cache
def get_connection() -> psycopg.Connection:
    """Return a process-wide Postgres connection, creating the schema on first use."""
    conn = connect()
    init_schema(conn)
    return conn


def log_interaction(
    conn: psycopg.Connection,
    interaction_id: str,
    question: str,
    rewritten_query: str,
    retrieval_strategy: str,
    retrieved_fdc_ids: Sequence[int],
    answer: str,
    latency_ms: float,
    created_at: datetime | None = None,
) -> None:
    """Persist one question/answer interaction."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO interactions
                (id, question, rewritten_query, retrieval_strategy, retrieved_fdc_ids,
                 answer, latency_ms, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                interaction_id,
                question,
                rewritten_query,
                retrieval_strategy,
                list(retrieved_fdc_ids),
                answer,
                latency_ms,
                created_at or datetime.now(UTC),
            ),
        )
    conn.commit()


def log_feedback(
    conn: psycopg.Connection,
    interaction_id: str,
    value: str,
    created_at: datetime | None = None,
) -> None:
    """Persist thumbs up/down feedback for an interaction."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO feedback (interaction_id, value, created_at) VALUES (%s, %s, %s)",
            (interaction_id, value, created_at or datetime.now(UTC)),
        )
    conn.commit()


def log_evaluation_run(
    conn: psycopg.Connection,
    strategy: str,
    metric_name: str,
    metric_value: float,
    created_at: datetime | None = None,
) -> None:
    """Persist one evaluation metric result, for the dashboard's score trend panel."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO evaluation_runs (strategy, metric_name, metric_value, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (strategy, metric_name, metric_value, created_at or datetime.now(UTC)),
        )
    conn.commit()
