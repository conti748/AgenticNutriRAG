from pathlib import Path
from unittest.mock import MagicMock

from eval.ground_truth import (
    GroundTruthItem,
    filter_ground_truth,
    generate_ground_truth,
    generate_question_for_food,
    load_ground_truth,
    sample_indexed_foods,
    save_ground_truth,
)


def _es_response(foods: list[dict]) -> dict:
    return {"hits": {"hits": [{"_source": food} for food in foods]}}


def _food(fdc_id: int) -> dict:
    return {
        "fdc_id": str(fdc_id),
        "food_name": f"Food {fdc_id}",
        "food_category": "Test Category",
        "search_text": "description",
        "nutrients": {"calories_kcal": 100.0, "iron_mg": 2.0},
    }


def test_sample_indexed_foods_is_deterministic_given_seed() -> None:
    es_client = MagicMock()
    es_client.search.return_value = _es_response([_food(i) for i in range(10)])

    first = sample_indexed_foods(es_client, sample_size=3, seed=1)
    second = sample_indexed_foods(es_client, sample_size=3, seed=1)

    assert first == second
    assert len(first) == 3


def test_sample_indexed_foods_caps_at_available_documents() -> None:
    es_client = MagicMock()
    es_client.search.return_value = _es_response([_food(1)])

    result = sample_indexed_foods(es_client, sample_size=5, seed=1)

    assert len(result) == 1


def _mock_openai_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=content))
    ]
    return client


def test_generate_question_for_food_returns_stripped_llm_output() -> None:
    client = _mock_openai_client("  How much protein is in an egg?  ")

    question = generate_question_for_food(client, _food(1))

    assert question == "How much protein is in an egg?"


def test_generate_question_for_food_returns_empty_string_on_empty_response() -> None:
    client = _mock_openai_client("")

    assert generate_question_for_food(client, _food(1)) == ""


def test_generate_question_for_food_prompts_with_nutrients_not_just_name() -> None:
    client = _mock_openai_client("Some question?")

    generate_question_for_food(client, _food(1))

    _, kwargs = client.chat.completions.create.call_args
    user_message = kwargs["messages"][1]["content"]
    assert "iron_mg: 2.0" in user_message
    assert "Test Category" in user_message


def test_generate_question_for_food_handles_missing_nutrients() -> None:
    client = _mock_openai_client("Some question?")
    food = {"fdc_id": "1", "food_name": "Food 1", "food_category": None, "search_text": "x"}

    question = generate_question_for_food(client, food)

    assert question == "Some question?"


def test_generate_ground_truth_skips_empty_questions() -> None:
    es_client = MagicMock()
    es_client.search.return_value = _es_response([_food(1), _food(2)])
    openai_client = MagicMock()
    openai_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content="How much protein?"))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content=""))]),
    ]

    items = generate_ground_truth(es_client, openai_client, sample_size=2, seed=1)

    assert len(items) == 1
    assert items[0].question == "How much protein?"


def test_filter_ground_truth_drops_short_duplicate_and_refusal_questions() -> None:
    items = [
        GroundTruthItem(question="How much protein is in an egg?", fdc_id=1, food_name="Egg"),
        GroundTruthItem(question="how much PROTEIN is in an egg?", fdc_id=1, food_name="Egg"),
        GroundTruthItem(question="Too short", fdc_id=2, food_name="Milk"),
        GroundTruthItem(
            question="I'm sorry, I cannot help with that request.", fdc_id=3, food_name="X"
        ),
        GroundTruthItem(
            question="What vitamins does an orange contain?", fdc_id=4, food_name="Orange"
        ),
    ]

    filtered = filter_ground_truth(items)

    assert [item.fdc_id for item in filtered] == [1, 4]


def test_save_and_load_ground_truth_round_trips(tmp_path: Path) -> None:
    items = [GroundTruthItem(question="How much protein is in an egg?", fdc_id=1, food_name="Egg")]
    path = tmp_path / "nested" / "ground_truth.json"

    save_ground_truth(items, path)
    loaded = load_ground_truth(path)

    assert loaded == items
