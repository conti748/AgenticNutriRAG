"""Retrieval evaluation harness.

Compares text-only, vector-only, and hybrid retrieval, each with query rewriting
on and off, against the generated ground-truth set, and reports hit rate/MRR for
every combination.

Run with: uv run python -m eval.retrieval_eval
Requires a populated Elasticsearch index (see ingestion.pipeline).
"""

import itertools
import logging
from dataclasses import dataclass

from elasticsearch import Elasticsearch
from openai import OpenAI

from agent.query_rewriting import rewrite_query
from agent.retrieval import DEFAULT_TOP_K, retrieve
from config import REPO_ROOT, RetrievalStrategy, get_settings
from eval.ground_truth import (
    GroundTruthItem,
    filter_ground_truth,
    generate_ground_truth,
    load_ground_truth,
    save_ground_truth,
)
from eval.metrics import hit_rate, mrr

logger = logging.getLogger(__name__)

STRATEGIES: tuple[RetrievalStrategy, ...] = ("text_only", "vector_only", "hybrid")
REWRITING_OPTIONS: tuple[bool, ...] = (False, True)

GROUND_TRUTH_PATH = REPO_ROOT / "data" / "eval" / "ground_truth.json"
REPORT_PATH = REPO_ROOT / "data" / "eval" / "retrieval_report.md"


@dataclass
class EvaluationResult:
    """Hit rate/MRR for one retrieval strategy + query-rewriting combination."""

    strategy: RetrievalStrategy
    query_rewriting_enabled: bool
    hit_rate: float
    mrr: float


def evaluate_combination(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    ground_truth: list[GroundTruthItem],
    strategy: RetrievalStrategy,
    query_rewriting_enabled: bool,
    top_k: int = DEFAULT_TOP_K,
) -> EvaluationResult:
    """Run retrieval for every ground-truth question and score with hit rate/MRR."""
    relevance: list[list[bool]] = []
    for item in ground_truth:
        query = rewrite_query(openai_client, item.question, enabled=query_rewriting_enabled)
        results = retrieve(es_client, openai_client, query, strategy=strategy, top_k=top_k)
        relevance.append([food.fdc_id == item.fdc_id for food in results])

    return EvaluationResult(
        strategy=strategy,
        query_rewriting_enabled=query_rewriting_enabled,
        hit_rate=hit_rate(relevance),
        mrr=mrr(relevance),
    )


def run_retrieval_evaluation(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    ground_truth: list[GroundTruthItem],
    top_k: int = DEFAULT_TOP_K,
) -> list[EvaluationResult]:
    """Evaluate every strategy x query-rewriting combination against the ground truth."""
    results = []
    for strategy, rewriting_enabled in itertools.product(STRATEGIES, REWRITING_OPTIONS):
        logger.info("Evaluating strategy=%s rewriting=%s", strategy, rewriting_enabled)
        results.append(
            evaluate_combination(
                es_client, openai_client, ground_truth, strategy, rewriting_enabled, top_k
            )
        )
    return results


def best_result(results: list[EvaluationResult]) -> EvaluationResult:
    """Pick the best-performing combination, ranked by MRR then hit rate."""
    return max(results, key=lambda r: (r.mrr, r.hit_rate))


def format_report(results: list[EvaluationResult]) -> str:
    """Render a markdown comparison table, best combination first."""
    ranked = sorted(results, key=lambda r: (r.mrr, r.hit_rate), reverse=True)
    lines = ["| Strategy | Query Rewriting | Hit Rate | MRR |", "|---|---|---|---|"]
    for r in ranked:
        rewriting = "on" if r.query_rewriting_enabled else "off"
        lines.append(f"| {r.strategy} | {rewriting} | {r.hit_rate:.3f} | {r.mrr:.3f} |")
    return "\n".join(lines)


def _load_or_build_ground_truth(
    es_client: Elasticsearch, openai_client: OpenAI
) -> list[GroundTruthItem]:
    if GROUND_TRUTH_PATH.exists():
        ground_truth = load_ground_truth(GROUND_TRUTH_PATH)
        logger.info("Loaded %d ground-truth items from %s", len(ground_truth), GROUND_TRUTH_PATH)
        return ground_truth

    logger.info("No ground-truth set found at %s, generating one", GROUND_TRUTH_PATH)
    ground_truth = filter_ground_truth(generate_ground_truth(es_client, openai_client))
    save_ground_truth(ground_truth, GROUND_TRUTH_PATH)
    logger.info("Saved %d ground-truth items to %s", len(ground_truth), GROUND_TRUTH_PATH)
    return ground_truth


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    es_client = Elasticsearch(settings.elasticsearch_url)
    openai_client = OpenAI(api_key=settings.openai_api_key)

    ground_truth = _load_or_build_ground_truth(es_client, openai_client)
    results = run_retrieval_evaluation(es_client, openai_client, ground_truth)

    report = format_report(results)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report + "\n")
    logger.info("Report saved to %s:\n%s", REPORT_PATH, report)

    winner = best_result(results)
    logger.info(
        "Best combination: strategy=%s query_rewriting=%s (hit_rate=%.3f, mrr=%.3f)",
        winner.strategy,
        winner.query_rewriting_enabled,
        winner.hit_rate,
        winner.mrr,
    )


if __name__ == "__main__":
    main()
