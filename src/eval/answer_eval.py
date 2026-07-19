"""Answer evaluation harness.

Generates the agent's answer for every question in the answer ground-truth set under
each retrieval strategy (query rewriting held fixed at the already-selected default
from retrieval evaluation, tasks.md 4.5 - re-sweeping it here would be redundant),
scores each generated answer against its reference answer with both cosine similarity
and an LLM judge, and reports aggregate results per strategy.

Run with: uv run python -m eval.answer_eval
Requires a populated Elasticsearch index and a saved retrieval ground-truth set
(see eval.retrieval_eval / eval.ground_truth).
"""

import logging
from dataclasses import dataclass

from elasticsearch import Elasticsearch
from openai import OpenAI

from agent.rag import answer_question
from config import REPO_ROOT, RetrievalStrategy, get_settings
from eval.answer_ground_truth import (
    AnswerGroundTruthItem,
    build_answer_ground_truth,
    load_answer_ground_truth,
    save_answer_ground_truth,
)
from eval.answer_scoring import score_cosine_similarity, score_llm_judge
from eval.ground_truth import load_ground_truth
from eval.retrieval_eval import GROUND_TRUTH_PATH, STRATEGIES

logger = logging.getLogger(__name__)

ANSWER_GROUND_TRUTH_PATH = REPO_ROOT / "data" / "eval" / "answer_ground_truth.json"
ANSWER_REPORT_PATH = REPO_ROOT / "data" / "eval" / "answer_report.md"


@dataclass
class AnswerEvaluationResult:
    """Average cosine-similarity/LLM-judge scores for one retrieval strategy."""

    strategy: RetrievalStrategy
    mean_cosine_similarity: float
    mean_llm_judge_score: float


def evaluate_combination(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    answer_ground_truth: list[AnswerGroundTruthItem],
    strategy: RetrievalStrategy,
    query_rewriting_enabled: bool,
) -> AnswerEvaluationResult:
    """Generate and score an answer for every ground-truth question under one strategy."""
    cosine_scores = []
    judge_scores = []
    for item in answer_ground_truth:
        result = answer_question(
            es_client,
            openai_client,
            item.question,
            strategy=strategy,
            query_rewriting_enabled=query_rewriting_enabled,
        )
        cosine_scores.append(
            score_cosine_similarity(openai_client, result.answer, item.reference_answer)
        )
        judge_scores.append(
            score_llm_judge(openai_client, item.question, item.reference_answer, result.answer)
        )

    return AnswerEvaluationResult(
        strategy=strategy,
        mean_cosine_similarity=sum(cosine_scores) / len(cosine_scores) if cosine_scores else 0.0,
        mean_llm_judge_score=sum(judge_scores) / len(judge_scores) if judge_scores else 0.0,
    )


def run_answer_evaluation(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    answer_ground_truth: list[AnswerGroundTruthItem],
    query_rewriting_enabled: bool,
) -> list[AnswerEvaluationResult]:
    """Evaluate every retrieval strategy against the answer ground truth."""
    results = []
    for strategy in STRATEGIES:
        logger.info(
            "Evaluating answers strategy=%s rewriting=%s", strategy, query_rewriting_enabled
        )
        results.append(
            evaluate_combination(
                es_client, openai_client, answer_ground_truth, strategy, query_rewriting_enabled
            )
        )
    return results


def best_result(results: list[AnswerEvaluationResult]) -> AnswerEvaluationResult:
    """Pick the best-performing strategy, ranked by LLM judge score then cosine similarity."""
    return max(results, key=lambda r: (r.mean_llm_judge_score, r.mean_cosine_similarity))


def format_report(results: list[AnswerEvaluationResult]) -> str:
    """Render a markdown comparison table, best strategy first."""
    ranked = sorted(
        results, key=lambda r: (r.mean_llm_judge_score, r.mean_cosine_similarity), reverse=True
    )
    lines = ["| Strategy | Cosine Similarity | LLM Judge |", "|---|---|---|"]
    for r in ranked:
        lines.append(
            f"| {r.strategy} | {r.mean_cosine_similarity:.3f} | {r.mean_llm_judge_score:.3f} |"
        )
    return "\n".join(lines)


def _load_or_build_answer_ground_truth(
    es_client: Elasticsearch, openai_client: OpenAI
) -> list[AnswerGroundTruthItem]:
    if ANSWER_GROUND_TRUTH_PATH.exists():
        answer_ground_truth = load_answer_ground_truth(ANSWER_GROUND_TRUTH_PATH)
        logger.info(
            "Loaded %d answer ground-truth items from %s",
            len(answer_ground_truth),
            ANSWER_GROUND_TRUTH_PATH,
        )
        return answer_ground_truth

    ground_truth = load_ground_truth(GROUND_TRUTH_PATH)
    logger.info(
        "No answer ground-truth set found at %s, generating one from %d retrieval "
        "ground-truth items",
        ANSWER_GROUND_TRUTH_PATH,
        len(ground_truth),
    )
    answer_ground_truth = build_answer_ground_truth(es_client, openai_client, ground_truth)
    save_answer_ground_truth(answer_ground_truth, ANSWER_GROUND_TRUTH_PATH)
    logger.info(
        "Saved %d answer ground-truth items to %s",
        len(answer_ground_truth),
        ANSWER_GROUND_TRUTH_PATH,
    )
    return answer_ground_truth


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    es_client = Elasticsearch(settings.elasticsearch_url)
    openai_client = OpenAI(api_key=settings.openai_api_key)

    answer_ground_truth = _load_or_build_answer_ground_truth(es_client, openai_client)
    results = run_answer_evaluation(
        es_client, openai_client, answer_ground_truth, settings.query_rewriting_enabled
    )

    report = format_report(results)
    ANSWER_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANSWER_REPORT_PATH.write_text(report + "\n")
    logger.info("Report saved to %s:\n%s", ANSWER_REPORT_PATH, report)

    winner = best_result(results)
    logger.info(
        "Best strategy: %s (cosine=%.3f, llm_judge=%.3f)",
        winner.strategy,
        winner.mean_cosine_similarity,
        winner.mean_llm_judge_score,
    )
    if winner.strategy == settings.retrieval_strategy:
        logger.info("Answer evaluation confirms the shipped default retrieval strategy.")
    else:
        logger.warning(
            "Answer evaluation's best strategy (%s) differs from the shipped default (%s); "
            "see README for the documented trade-off.",
            winner.strategy,
            settings.retrieval_strategy,
        )


if __name__ == "__main__":
    main()
