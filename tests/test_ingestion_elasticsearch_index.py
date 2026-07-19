from unittest.mock import MagicMock

from ingestion.elasticsearch_index import (
    EMBEDDING_DIMENSIONS,
    INDEX_MAPPING,
    INDEX_NAME,
    ensure_index,
    index_food,
)
from ingestion.models import CoreNutrients, FoodDocument


def test_index_mapping_has_hybrid_fields() -> None:
    properties = INDEX_MAPPING["properties"]

    assert properties["search_text"]["type"] == "text"
    assert properties["embedding"]["type"] == "dense_vector"
    assert properties["embedding"]["dims"] == EMBEDDING_DIMENSIONS

    nutrient_props = properties["nutrients"]["properties"]
    for field in ("calories_kcal", "protein_g", "fat_g", "carbohydrate_g"):
        assert nutrient_props[field]["type"] == "float"

    assert properties["all_nutrients"]["type"] == "nested"


def test_ensure_index_creates_when_missing() -> None:
    client = MagicMock()
    client.indices.exists.return_value = False

    ensure_index(client)

    client.indices.create.assert_called_once_with(index=INDEX_NAME, mappings=INDEX_MAPPING)


def test_ensure_index_skips_when_present() -> None:
    client = MagicMock()
    client.indices.exists.return_value = True

    ensure_index(client)

    client.indices.create.assert_not_called()


def test_index_food_uses_stable_fdc_id() -> None:
    client = MagicMock()
    food = FoodDocument(
        fdc_id=747447,
        food_name="Hummus, commercial",
        food_category="Legumes and Legume Products",
        data_type="Foundation",
        search_text="Hummus, commercial.",
        nutrients=CoreNutrients(
            calories_kcal=166.0, protein_g=7.14, fat_g=9.6, carbohydrate_g=14.3
        ),
        all_nutrients=[],
    )

    index_food(client, food, embedding=[0.1, 0.2])

    client.index.assert_called_once()
    _, kwargs = client.index.call_args
    assert kwargs["index"] == INDEX_NAME
    assert kwargs["id"] == "747447"
    assert kwargs["document"]["embedding"] == [0.1, 0.2]
    assert kwargs["document"]["fdc_id"] == "747447"
