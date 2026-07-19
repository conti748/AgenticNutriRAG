"""Ground-truth generation for retrieval evaluation.

Samples indexed foods and uses an LLM to produce one plausible user question per
food, forming (question, FDC ID) pairs without any manual labeling.
"""

import json
import logging
import random
from pathlib import Path
from typing import Any

from elasticsearch import Elasticsearch
from openai import OpenAI
from pydantic import BaseModel

from agent.query_rewriting import CHAT_MODEL
from ingestion.elasticsearch_index import INDEX_NAME

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_SIZE = 30
DEFAULT_SEED = 42
MAX_INDEX_SCAN_SIZE = 1000

# Automated stand-in for manual spot-checking (design.md Risks / Trade-offs): drops
# degenerate LLM output rather than requiring a human review pass, so ground-truth
# generation stays fully reproducible.
MIN_QUESTION_LENGTH = 15
REFUSAL_MARKERS = ("i'm sorry", "i cannot", "i can't", "as an ai")

GROUND_TRUTH_SYSTEM_PROMPT = (
    "You write challenging but realistic questions a person might ask a nutrition "
    "assistant, used to test whether a search system can find the right food from "
    "the question alone. You are given one food, its category, and its full "
    "per-100g nutrient profile.\n\n"
    "Write ONE question about this specific food that:\n"
    "1. Identifies the food with a paraphrased description (a synonym, the "
    "specific preparation/variety/cut, how it's typically eaten) rather than "
    "copying its exact name or category string verbatim. The description must "
    "stay specific enough to point at THIS food rather than many other foods in "
    "the same broad category - avoid vague phrases like 'this food' or 'this "
    "option' with no distinguishing detail attached.\n"
    "2. Asks about ONE specific nutrient value - mix common macros (calories, "
    "protein, fat, carbs) with occasional vitamin/mineral/fiber/sugar questions - "
    "or takes a dietary-suitability angle (e.g. 'is this a good low-sodium "
    "option').\n\n"
    "Vary the phrasing and the nutrient/angle chosen across foods. Respond with "
    "only the question, no explanation."
)


class GroundTruthItem(BaseModel):
    """One (question, expected food) pair used to evaluate retrieval."""

    question: str
    fdc_id: int
    food_name: str


def sample_indexed_foods(
    es_client: Elasticsearch,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    """Randomly sample food documents from the index, deterministic given the seed."""
    response = es_client.search(
        index=INDEX_NAME,
        query={"match_all": {}},
        size=MAX_INDEX_SCAN_SIZE,
    )
    foods = [hit["_source"] for hit in response["hits"]["hits"]]
    return random.Random(seed).sample(foods, k=min(sample_size, len(foods)))


def _format_nutrients(nutrients: dict[str, Any]) -> str:
    lines = [f"- {name}: {value}" for name, value in nutrients.items() if value is not None]
    return "\n".join(lines) if lines else "(no detailed nutrient data)"


def generate_question_for_food(client: OpenAI, food: dict[str, Any]) -> str:
    """Ask the LLM for one plausible, indirect user question about this food."""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": GROUND_TRUTH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Food: {food['food_name']}\n"
                    f"Category: {food.get('food_category') or 'unknown'}\n"
                    f"Nutrients per 100g:\n{_format_nutrients(food.get('nutrients') or {})}"
                ),
            },
        ],
        temperature=0.8,
    )
    question = response.choices[0].message.content
    return question.strip() if question else ""


def generate_ground_truth(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
) -> list[GroundTruthItem]:
    """Sample indexed foods and generate one evaluation question per food."""
    foods = sample_indexed_foods(es_client, sample_size, seed)
    items = []
    for food in foods:
        question = generate_question_for_food(openai_client, food)
        if not question:
            logger.warning("Empty question generated for FDC ID %s, skipping", food["fdc_id"])
            continue
        items.append(
            GroundTruthItem(
                question=question,
                fdc_id=int(food["fdc_id"]),
                food_name=food["food_name"],
            )
        )
    return items


def filter_ground_truth(items: list[GroundTruthItem]) -> list[GroundTruthItem]:
    """Drop degenerate ground-truth items: too short, refusal-like, or duplicate questions."""
    seen_questions: set[str] = set()
    filtered = []
    for item in items:
        normalized = item.question.strip().lower()
        if len(item.question) < MIN_QUESTION_LENGTH:
            continue
        if any(marker in normalized for marker in REFUSAL_MARKERS):
            continue
        if normalized in seen_questions:
            continue
        seen_questions.add(normalized)
        filtered.append(item)
    return filtered


def save_ground_truth(items: list[GroundTruthItem], path: Path) -> None:
    """Save the ground-truth set as JSON, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([item.model_dump() for item in items], indent=2))


def load_ground_truth(path: Path) -> list[GroundTruthItem]:
    """Load a previously saved ground-truth set."""
    return [GroundTruthItem(**item) for item in json.loads(path.read_text())]
