from unittest.mock import MagicMock, patch

from agent.models import RetrievedFood
from eval.ground_truth import GroundTruthItem
from eval.retrieval_eval import (
    REWRITING_OPTIONS,
    STRATEGIES,
    EvaluationResult,
    best_result,
    evaluate_combination,
    format_report,
    run_retrieval_evaluation,
)


def _food(fdc_id: int) -> RetrievedFood:
    return RetrievedFood(
        fdc_id=fdc_id, food_name="Food", food_category=None, search_text="x", score=1.0
    )


def test_evaluate_combination_scores_hits_and_misses() -> None:
    ground_truth = [
        GroundTruthItem(question="Q1", fdc_id=1, food_name="Egg"),
        GroundTruthItem(question="Q2", fdc_id=2, food_name="Milk"),
    ]
    es_client = MagicMock()
    openai_client = MagicMock()

    with (
        patch("eval.retrieval_eval.rewrite_query", side_effect=lambda c, q, enabled: q),
        patch("eval.retrieval_eval.retrieve", side_effect=[[_food(1), _food(9)], [_food(9)]]),
    ):
        result = evaluate_combination(
            es_client,
            openai_client,
            ground_truth,
            strategy="text_only",
            query_rewriting_enabled=False,
        )

    assert result.strategy == "text_only"
    assert result.query_rewriting_enabled is False
    assert result.hit_rate == 0.5
    assert result.mrr == 0.5


def test_run_retrieval_evaluation_covers_every_combination() -> None:
    ground_truth = [GroundTruthItem(question="Q1", fdc_id=1, food_name="Egg")]
    es_client = MagicMock()
    openai_client = MagicMock()

    with (
        patch("eval.retrieval_eval.rewrite_query", side_effect=lambda c, q, enabled: q),
        patch("eval.retrieval_eval.retrieve", return_value=[_food(1)]),
    ):
        results = run_retrieval_evaluation(es_client, openai_client, ground_truth)

    combos = {(r.strategy, r.query_rewriting_enabled) for r in results}
    assert combos == {(s, r) for s in STRATEGIES for r in REWRITING_OPTIONS}


def test_best_result_ranks_by_mrr_then_hit_rate() -> None:
    weaker = EvaluationResult(
        strategy="text_only", query_rewriting_enabled=False, hit_rate=0.5, mrr=0.3
    )
    stronger = EvaluationResult(
        strategy="hybrid", query_rewriting_enabled=True, hit_rate=0.6, mrr=0.5
    )

    assert best_result([weaker, stronger]) is stronger


def test_format_report_lists_best_combination_first() -> None:
    weaker = EvaluationResult(
        strategy="text_only", query_rewriting_enabled=False, hit_rate=0.5, mrr=0.3
    )
    stronger = EvaluationResult(
        strategy="hybrid", query_rewriting_enabled=True, hit_rate=0.6, mrr=0.5
    )

    report = format_report([weaker, stronger])

    assert report.index("hybrid") < report.index("text_only")
