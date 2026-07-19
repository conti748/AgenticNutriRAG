"""Elasticsearch index definition and document indexing for USDA foods."""

from typing import Any

from elasticsearch import Elasticsearch

from ingestion.embeddings import EMBEDDING_DIMENSIONS
from ingestion.models import FoodDocument

INDEX_NAME = "usda_foods"

INDEX_MAPPING: dict[str, Any] = {
    "properties": {
        "fdc_id": {"type": "keyword"},
        "food_name": {"type": "text"},
        "food_category": {"type": "keyword"},
        "data_type": {"type": "keyword"},
        "search_text": {"type": "text"},
        "embedding": {
            "type": "dense_vector",
            "dims": EMBEDDING_DIMENSIONS,
            "index": True,
            "similarity": "cosine",
        },
        "nutrients": {
            "properties": {
                "calories_kcal": {"type": "float"},
                "protein_g": {"type": "float"},
                "fat_g": {"type": "float"},
                "carbohydrate_g": {"type": "float"},
                "fiber_g": {"type": "float"},
                "sugars_g": {"type": "float"},
                "calcium_mg": {"type": "float"},
                "iron_mg": {"type": "float"},
                "potassium_mg": {"type": "float"},
                "sodium_mg": {"type": "float"},
                "vitamin_c_mg": {"type": "float"},
                "vitamin_d_ug": {"type": "float"},
            }
        },
        "all_nutrients": {
            "type": "nested",
            "properties": {
                "nutrient_number": {"type": "keyword"},
                "name": {"type": "keyword"},
                "unit": {"type": "keyword"},
                "value": {"type": "float"},
            },
        },
    }
}


def ensure_index(client: Elasticsearch, index_name: str = INDEX_NAME) -> None:
    """Create the index with the hybrid mapping if it doesn't already exist."""
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, mappings=INDEX_MAPPING)


def index_food(
    client: Elasticsearch,
    food: FoodDocument,
    embedding: list[float],
    index_name: str = INDEX_NAME,
) -> None:
    """Index one food document, keyed by its FDC ID for idempotent re-runs."""
    document = food.model_dump(exclude={"fdc_id"})
    document["fdc_id"] = str(food.fdc_id)
    document["embedding"] = embedding
    client.index(index=index_name, id=str(food.fdc_id), document=document)
