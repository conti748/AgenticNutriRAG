"""The lookup_food_nutrients tool: lets the model pull full nutrient detail on demand."""

from typing import Any

from elasticsearch import Elasticsearch, NotFoundError

from ingestion.elasticsearch_index import INDEX_NAME

LOOKUP_FOOD_NUTRIENTS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "lookup_food_nutrients",
        "description": (
            "Look up the full structured nutrient detail (all nutrients reported by "
            "USDA, not just the core macros) for a specific food by its FDC ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fdc_id": {
                    "type": "integer",
                    "description": "The USDA FoodData Central ID of the food.",
                }
            },
            "required": ["fdc_id"],
        },
    },
}


def lookup_food_nutrients(es_client: Elasticsearch, fdc_id: int) -> dict[str, Any] | None:
    """Fetch full nutrient detail for one food by FDC ID, or None if it isn't indexed."""
    try:
        response = es_client.get(index=INDEX_NAME, id=str(fdc_id))
    except NotFoundError:
        return None

    source: dict[str, Any] = response["_source"]
    return {
        "fdc_id": fdc_id,
        "food_name": source["food_name"],
        "nutrients": source["nutrients"],
        "all_nutrients": source["all_nutrients"],
    }
