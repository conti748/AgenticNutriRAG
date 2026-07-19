from unittest.mock import MagicMock

import pytest

from eval.answer_scoring import (
    JudgeScoreParseError,
    _parse_judge_score,
    cosine_similarity,
    score_cosine_similarity,
    score_llm_judge,
)


def test_cosine_similarity_identical_vectors_is_one() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors_is_negative_one() -> None:
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector_is_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_score_cosine_similarity_embeds_both_answers(monkeypatch) -> None:
    monkeypatch.setattr(
        "eval.answer_scoring.embed_texts",
        lambda client, texts: [[1.0, 0.0], [1.0, 0.0]],
    )
    openai_client = MagicMock()

    score = score_cosine_similarity(openai_client, "generated", "reference")

    assert score == pytest.approx(1.0)


def test_parse_judge_score_extracts_integer() -> None:
    assert _parse_judge_score("5") == 5
    assert _parse_judge_score("Score: 3") == 3


def test_parse_judge_score_clamps_out_of_range_values() -> None:
    assert _parse_judge_score("9") == 5
    assert _parse_judge_score("0") == 1


def test_parse_judge_score_raises_when_unparseable() -> None:
    with pytest.raises(JudgeScoreParseError):
        _parse_judge_score("not a score")
    with pytest.raises(JudgeScoreParseError):
        _parse_judge_score(None)


def test_score_llm_judge_returns_parsed_score() -> None:
    openai_client = MagicMock()
    openai_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="4"))
    ]

    score = score_llm_judge(openai_client, "Q?", "reference answer", "generated answer")

    assert score == 4.0


def test_score_llm_judge_prompts_with_question_and_both_answers() -> None:
    openai_client = MagicMock()
    openai_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="5"))
    ]

    score_llm_judge(openai_client, "How much protein?", "12.6g", "About 12.6g of protein.")

    _, kwargs = openai_client.chat.completions.create.call_args
    user_message = kwargs["messages"][1]["content"]
    assert "How much protein?" in user_message
    assert "12.6g" in user_message
    assert "About 12.6g of protein." in user_message
