from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ingestion import pipeline

FAKE_SETTINGS = SimpleNamespace(
    usda_api_key="usda-key",
    openai_api_key="openai-key",
    elasticsearch_url="http://localhost:9200",
)


def _raw_food(fdc_id: int) -> dict:
    return {
        "fdcId": fdc_id,
        "description": f"Food {fdc_id}",
        "dataType": "Foundation",
        "foodCategory": "Test Category",
        "foodNutrients": [
            {
                "amount": 100.0,
                "nutrient": {"id": 1008, "number": "208", "name": "Energy", "unitName": "kcal"},
            },
            {
                "amount": 10.0,
                "nutrient": {"id": 1003, "number": "203", "name": "Protein", "unitName": "g"},
            },
            {
                "amount": 5.0,
                "nutrient": {
                    "id": 1004,
                    "number": "204",
                    "name": "Total lipid (fat)",
                    "unitName": "g",
                },
            },
            {
                "amount": 20.0,
                "nutrient": {
                    "id": 1005,
                    "number": "205",
                    "name": "Carbohydrate, by difference",
                    "unitName": "g",
                },
            },
        ],
    }


def _run_pipeline_with_fake_foods(fdc_ids: list[int]) -> tuple[int, list[str]]:
    raw_foods = [_raw_food(fdc_id) for fdc_id in fdc_ids]
    indexed_ids: list[str] = []

    def fake_index_food(client, food, embedding, index_name=pipeline.INDEX_NAME):  # noqa: ANN001
        indexed_ids.append(str(food.fdc_id))

    with (
        patch.object(pipeline, "get_settings", return_value=FAKE_SETTINGS),
        patch.object(pipeline, "USDAClient") as mock_usda_cls,
        patch.object(pipeline, "OpenAI"),
        patch.object(pipeline, "Elasticsearch") as mock_es_cls,
        patch.object(pipeline, "ensure_index") as mock_ensure_index,
        patch.object(pipeline, "embed_texts") as mock_embed_texts,
        patch.object(pipeline, "index_food", side_effect=fake_index_food),
    ):
        mock_usda_cls.return_value.iter_foods.return_value = iter(raw_foods)
        mock_embed_texts.side_effect = lambda client, texts: [[0.0] * 3 for _ in texts]
        mock_es_instance = MagicMock()
        mock_es_cls.return_value = mock_es_instance

        count = pipeline.run_ingestion()

        mock_ensure_index.assert_called_once_with(mock_es_instance)
        mock_es_instance.indices.refresh.assert_called_once_with(index=pipeline.INDEX_NAME)

    return count, indexed_ids


def test_run_ingestion_indexes_every_fetched_food() -> None:
    count, indexed_ids = _run_pipeline_with_fake_foods([1, 2, 3])

    assert count == 3
    assert indexed_ids == ["1", "2", "3"]


def test_run_ingestion_is_idempotent_across_runs() -> None:
    _, first_run_ids = _run_pipeline_with_fake_foods([1, 2, 3])
    _, second_run_ids = _run_pipeline_with_fake_foods([1, 2, 3])

    assert first_run_ids == second_run_ids


def test_run_ingestion_handles_empty_subset() -> None:
    count, indexed_ids = _run_pipeline_with_fake_foods([])

    assert count == 0
    assert indexed_ids == []
