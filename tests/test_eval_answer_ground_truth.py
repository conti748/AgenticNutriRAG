from pathlib import Path
from unittest.mock import MagicMock

from eval.answer_ground_truth import (
    AnswerGroundTruthItem,
    build_answer_ground_truth,
    generate_reference_answer,
    load_answer_ground_truth,
    save_answer_ground_truth,
)
from eval.ground_truth import GroundTruthItem


def _mock_openai_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=content))
    ]
    return client


def _food_detail(fdc_id: int) -> dict:
    return {
        "fdc_id": fdc_id,
        "food_name": f"Food {fdc_id}",
        "nutrients": {"protein_g": 12.6},
        "all_nutrients": [],
    }


def test_generate_reference_answer_returns_stripped_llm_output() -> None:
    client = _mock_openai_client("  Eggs have 12.6g of protein per 100g.  ")

    answer = generate_reference_answer(client, "How much protein is in an egg?", _food_detail(1))

    assert answer == "Eggs have 12.6g of protein per 100g."


def test_generate_reference_answer_returns_empty_string_on_empty_response() -> None:
    client = _mock_openai_client("")

    assert generate_reference_answer(client, "Q?", _food_detail(1)) == ""


def test_generate_reference_answer_prompts_with_food_data() -> None:
    client = _mock_openai_client("Some answer.")

    generate_reference_answer(client, "How much protein?", _food_detail(1))

    _, kwargs = client.chat.completions.create.call_args
    user_message = kwargs["messages"][1]["content"]
    assert "Food 1" in user_message
    assert "protein_g" in user_message


def test_build_answer_ground_truth_generates_one_item_per_question() -> None:
    ground_truth = [
        GroundTruthItem(question="Q1", fdc_id=1, food_name="Egg"),
        GroundTruthItem(question="Q2", fdc_id=2, food_name="Milk"),
    ]
    es_client = MagicMock()
    es_client.get.side_effect = [
        {"_source": {"food_name": "Egg", "nutrients": {}, "all_nutrients": []}},
        {"_source": {"food_name": "Milk", "nutrients": {}, "all_nutrients": []}},
    ]
    openai_client = MagicMock()
    openai_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content="Answer 1"))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content="Answer 2"))]),
    ]

    items = build_answer_ground_truth(es_client, openai_client, ground_truth)

    assert [item.reference_answer for item in items] == ["Answer 1", "Answer 2"]
    assert [item.fdc_id for item in items] == [1, 2]


def test_build_answer_ground_truth_skips_food_not_indexed() -> None:
    from elasticsearch import NotFoundError

    ground_truth = [GroundTruthItem(question="Q1", fdc_id=1, food_name="Egg")]
    es_client = MagicMock()
    es_client.get.side_effect = NotFoundError(
        "not found", meta=MagicMock(), body={"error": "not found"}
    )
    openai_client = MagicMock()

    items = build_answer_ground_truth(es_client, openai_client, ground_truth)

    assert items == []
    openai_client.chat.completions.create.assert_not_called()


def test_build_answer_ground_truth_skips_empty_reference_answers() -> None:
    ground_truth = [GroundTruthItem(question="Q1", fdc_id=1, food_name="Egg")]
    es_client = MagicMock()
    es_client.get.return_value = {
        "_source": {"food_name": "Egg", "nutrients": {}, "all_nutrients": []}
    }
    openai_client = MagicMock()
    openai_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=""))
    ]

    items = build_answer_ground_truth(es_client, openai_client, ground_truth)

    assert items == []


def test_save_and_load_answer_ground_truth_round_trips(tmp_path: Path) -> None:
    items = [
        AnswerGroundTruthItem(
            question="How much protein is in an egg?",
            fdc_id=1,
            food_name="Egg",
            reference_answer="Eggs have 12.6g of protein per 100g.",
        )
    ]
    path = tmp_path / "nested" / "answer_ground_truth.json"

    save_answer_ground_truth(items, path)
    loaded = load_answer_ground_truth(path)

    assert loaded == items
