"""End-to-end ingestion entrypoint: fetch -> transform -> embed -> index.

Run with: uv run python -m ingestion.pipeline
"""

import logging
from itertools import batched

from elasticsearch import Elasticsearch
from openai import OpenAI

from config import get_settings
from ingestion.elasticsearch_index import INDEX_NAME, ensure_index, index_food
from ingestion.embeddings import embed_texts
from ingestion.transform import transform_food
from ingestion.usda_client import USDAClient

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 50


def run_ingestion() -> int:
    """Fetch the configured USDA subset, embed, and index it. Returns the document count."""
    settings = get_settings()
    usda_client = USDAClient(api_key=settings.usda_api_key)
    openai_client = OpenAI(api_key=settings.openai_api_key)
    es_client = Elasticsearch(settings.elasticsearch_url)

    ensure_index(es_client)

    indexed_count = 0
    for raw_batch in batched(usda_client.iter_foods(), EMBEDDING_BATCH_SIZE):
        foods = [transform_food(raw) for raw in raw_batch]
        embeddings = embed_texts(openai_client, [food.search_text for food in foods])
        for food, embedding in zip(foods, embeddings, strict=True):
            index_food(es_client, food, embedding)
        indexed_count += len(foods)
        logger.info("Indexed %d foods so far", indexed_count)

    es_client.indices.refresh(index=INDEX_NAME)
    return indexed_count


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    count = run_ingestion()
    logger.info("Ingestion complete: %d documents indexed into %r", count, INDEX_NAME)


if __name__ == "__main__":
    main()
