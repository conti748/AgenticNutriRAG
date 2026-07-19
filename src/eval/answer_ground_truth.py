"""Reference-answer generation for answer evaluation.

Extends the retrieval ground-truth set (eval.ground_truth) with an LLM-generated
reference answer per question, grounded in the question's expected food's full
nutrient data, for scoring the agent's generated answers against.
"""

import json
import logging
from pathlib import Path
from typing import Any

from elasticsearch import Elasticsearch
from openai import OpenAI
from pydantic import BaseModel

from agent.query_rewriting import CHAT_MODEL
from agent.tools import lookup_food_nutrients
from eval.ground_truth import GroundTruthItem

logger = logging.getLogger(__name__)

REFERENCE_ANSWER_SYSTEM_PROMPT = (
    "You write the ideal, factual answer to a nutrition question, grounded strictly in the "
    "food data provided. Answer only using the given data, cite the food by name, and keep "
    "the answer to one or two sentences. Respond with only the answer, no explanation."
)


class AnswerGroundTruthItem(BaseModel):
    """A retrieval ground-truth question paired with an LLM-generated reference answer."""

    question: str
    fdc_id: int
    food_name: str
    reference_answer: str


def generate_reference_answer(client: OpenAI, question: str, food_detail: dict[str, Any]) -> str:
    """Ask the LLM for the ideal answer to `question`, grounded in `food_detail`."""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": REFERENCE_ANSWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Food: {food_detail['food_name']}\n"
                    f"Nutrients: {json.dumps(food_detail['nutrients'])}"
                ),
            },
        ],
        temperature=0,
    )
    answer = response.choices[0].message.content
    return answer.strip() if answer else ""


def build_answer_ground_truth(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    ground_truth: list[GroundTruthItem],
) -> list[AnswerGroundTruthItem]:
    """Generate one reference answer per retrieval ground-truth question."""
    items = []
    for gt in ground_truth:
        food_detail = lookup_food_nutrients(es_client, gt.fdc_id)
        if food_detail is None:
            logger.warning("FDC ID %s not indexed, skipping reference answer", gt.fdc_id)
            continue
        reference_answer = generate_reference_answer(openai_client, gt.question, food_detail)
        if not reference_answer:
            logger.warning("Empty reference answer for FDC ID %s, skipping", gt.fdc_id)
            continue
        items.append(
            AnswerGroundTruthItem(
                question=gt.question,
                fdc_id=gt.fdc_id,
                food_name=gt.food_name,
                reference_answer=reference_answer,
            )
        )
    return items


def save_answer_ground_truth(items: list[AnswerGroundTruthItem], path: Path) -> None:
    """Save the answer ground-truth set as JSON, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([item.model_dump() for item in items], indent=2))


def load_answer_ground_truth(path: Path) -> list[AnswerGroundTruthItem]:
    """Load a previously saved answer ground-truth set."""
    return [AnswerGroundTruthItem(**item) for item in json.loads(path.read_text())]
