from unittest.mock import MagicMock, patch

from agent.models import AgentAnswer
from eval.answer_eval import (
    AnswerEvaluationResult,
    best_result,
    evaluate_combination,
    format_report,
    run_answer_evaluation,
)
from eval.answer_ground_truth import AnswerGroundTruthItem
from eval.retrieval_eval import STRATEGIES


def _answer_ground_truth() -> list[AnswerGroundTruthItem]:
    return [
        AnswerGroundTruthItem(
            question="Q1", fdc_id=1, food_name="Egg", reference_answer="Reference 1"
        ),
        AnswerGroundTruthItem(
            question="Q2", fdc_id=2, food_name="Milk", reference_answer="Reference 2"
        ),
    ]


def _agent_answer(text: str) -> AgentAnswer:
    return AgentAnswer(answer=text, rewritten_query="q", retrieval_strategy="hybrid", sources=[])


def test_evaluate_combination_averages_both_scores() -> None:
    es_client = MagicMock()
    openai_client = MagicMock()

    with (
        patch(
            "eval.answer_eval.answer_question",
            side_effect=[_agent_answer("Generated 1"), _agent_answer("Generated 2")],
        ),
        patch("eval.answer_eval.score_cosine_similarity", side_effect=[0.8, 0.6]),
        patch("eval.answer_eval.score_llm_judge", side_effect=[5.0, 3.0]),
    ):
        result = evaluate_combination(
            es_client,
            openai_client,
            _answer_ground_truth(),
            strategy="hybrid",
            query_rewriting_enabled=True,
        )

    assert result.strategy == "hybrid"
    assert result.mean_cosine_similarity == 0.7
    assert result.mean_llm_judge_score == 4.0


def test_run_answer_evaluation_covers_every_strategy() -> None:
    es_client = MagicMock()
    openai_client = MagicMock()

    with (
        patch("eval.answer_eval.answer_question", return_value=_agent_answer("Generated")),
        patch("eval.answer_eval.score_cosine_similarity", return_value=0.5),
        patch("eval.answer_eval.score_llm_judge", return_value=4.0),
    ):
        results = run_answer_evaluation(
            es_client, openai_client, _answer_ground_truth(), query_rewriting_enabled=True
        )

    assert {r.strategy for r in results} == set(STRATEGIES)


def test_best_result_ranks_by_llm_judge_then_cosine_similarity() -> None:
    weaker = AnswerEvaluationResult(
        strategy="text_only", mean_cosine_similarity=0.9, mean_llm_judge_score=2.0
    )
    stronger = AnswerEvaluationResult(
        strategy="hybrid", mean_cosine_similarity=0.5, mean_llm_judge_score=4.0
    )

    assert best_result([weaker, stronger]) is stronger


def test_format_report_lists_best_strategy_first() -> None:
    weaker = AnswerEvaluationResult(
        strategy="text_only", mean_cosine_similarity=0.5, mean_llm_judge_score=2.0
    )
    stronger = AnswerEvaluationResult(
        strategy="hybrid", mean_cosine_similarity=0.6, mean_llm_judge_score=4.0
    )

    report = format_report([weaker, stronger])

    assert report.index("hybrid") < report.index("text_only")
