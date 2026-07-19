from unittest.mock import MagicMock

from elasticsearch import NotFoundError

from agent.tools import LOOKUP_FOOD_NUTRIENTS_TOOL, lookup_food_nutrients
from ingestion.elasticsearch_index import INDEX_NAME


def test_lookup_food_nutrients_returns_detail() -> None:
    es_client = MagicMock()
    es_client.get.return_value = {
        "_source": {
            "food_name": "Egg, whole, raw",
            "nutrients": {"calories_kcal": 143.0, "protein_g": 12.6},
            "all_nutrients": [
                {"nutrient_number": "203", "name": "Protein", "unit": "g", "value": 12.6}
            ],
        }
    }

    result = lookup_food_nutrients(es_client, 747997)

    es_client.get.assert_called_once_with(index=INDEX_NAME, id="747997")
    assert result is not None
    assert result["fdc_id"] == 747997
    assert result["food_name"] == "Egg, whole, raw"
    assert result["nutrients"]["protein_g"] == 12.6


def test_lookup_food_nutrients_returns_none_when_not_found() -> None:
    es_client = MagicMock()
    es_client.get.side_effect = NotFoundError(
        "not found", meta=MagicMock(), body={"error": "not found"}
    )

    result = lookup_food_nutrients(es_client, 999999)

    assert result is None


def test_tool_schema_declares_fdc_id_parameter() -> None:
    function = LOOKUP_FOOD_NUTRIENTS_TOOL["function"]

    assert function["name"] == "lookup_food_nutrients"
    assert function["parameters"]["required"] == ["fdc_id"]
    assert function["parameters"]["properties"]["fdc_id"]["type"] == "integer"
