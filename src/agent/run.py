"""Manual smoke-test entrypoint: runs sample questions through the agent loop.

Run with: uv run python -m agent.run
Requires a populated Elasticsearch index (see ingestion.pipeline).
"""

import logging

from elasticsearch import Elasticsearch
from openai import OpenAI

from agent.rag import answer_question
from config import get_settings

logger = logging.getLogger(__name__)

SAMPLE_QUESTIONS = [
    "How much protein is in an egg?",
    "What's a good low-calorie source of fiber?",
    "How much vitamin C does an orange have?",
    "What foods are high in iron?",
    "Tell me about the nutrition profile of quinoa.",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    es_client = Elasticsearch(settings.elasticsearch_url)
    openai_client = OpenAI(api_key=settings.openai_api_key)

    for question in SAMPLE_QUESTIONS:
        result = answer_question(es_client, openai_client, question)
        logger.info("Q: %s", question)
        logger.info(
            "strategy=%s rewritten_query=%r", result.retrieval_strategy, result.rewritten_query
        )
        logger.info("A: %s", result.answer)
        logger.info("sources: %s", [f"{s.food_name} (FDC {s.fdc_id})" for s in result.sources])


if __name__ == "__main__":
    main()
