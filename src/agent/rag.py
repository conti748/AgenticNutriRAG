"""The agentic RAG loop: rewrite -> retrieve -> tool-call -> grounded answer generation."""

import json
import logging
from typing import Any, cast

from elasticsearch import Elasticsearch
from openai import OpenAI

from agent.models import AgentAnswer, RetrievedFood
from agent.query_rewriting import CHAT_MODEL, rewrite_query
from agent.retrieval import retrieve
from agent.tools import LOOKUP_FOOD_NUTRIENTS_TOOL, lookup_food_nutrients
from config import RetrievalStrategy, get_settings

logger = logging.getLogger(__name__)

NOT_FOUND_ANSWER = (
    "I couldn't find relevant nutrition data in the USDA food database to answer that question."
)

# Minimum top-hit score per strategy below which retrieval is treated as having found
# nothing relevant. Score scales differ by strategy (BM25 is unbounded, kNN cosine
# similarity is 0-1, RRF fusion scores are small), so each gets its own threshold.
# Informal starting points; revisit once retrieval evaluation (tasks.md section 4)
# picks a default strategy.
MIN_RELEVANCE_SCORE: dict[RetrievalStrategy, float] = {
    "text_only": 1.0,
    "vector_only": 0.5,
    "hybrid": 0.01,
}

SYSTEM_PROMPT = (
    "You are a nutrition assistant. Answer the user's question using only the "
    "candidate foods provided and any nutrient detail you retrieve via the "
    "lookup_food_nutrients tool. Always cite the specific food name(s) you used. "
    "Do not rely on outside nutrition knowledge."
)

MAX_TOOL_ITERATIONS = 4
TOOL_ITERATION_LIMIT_ANSWER = (
    "I wasn't able to finish looking up the nutrient details needed for this question."
)


def answer_question(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    question: str,
    strategy: RetrievalStrategy | None = None,
    query_rewriting_enabled: bool | None = None,
) -> AgentAnswer:
    """Run the full agentic RAG loop for one question: rewrite, retrieve, answer."""
    settings = get_settings()
    resolved_strategy = strategy if strategy is not None else settings.retrieval_strategy
    resolved_rewriting = (
        query_rewriting_enabled
        if query_rewriting_enabled is not None
        else settings.query_rewriting_enabled
    )

    rewritten_query = rewrite_query(openai_client, question, enabled=resolved_rewriting)
    candidates = retrieve(es_client, openai_client, rewritten_query, resolved_strategy)

    if not candidates or candidates[0].score < MIN_RELEVANCE_SCORE[resolved_strategy]:
        return AgentAnswer(
            answer=NOT_FOUND_ANSWER,
            rewritten_query=rewritten_query,
            retrieval_strategy=resolved_strategy,
            sources=[],
        )

    answer_text = _generate_answer(es_client, openai_client, question, candidates)

    return AgentAnswer(
        answer=answer_text,
        rewritten_query=rewritten_query,
        retrieval_strategy=resolved_strategy,
        sources=candidates,
    )


def _generate_answer(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    question: str,
    candidates: list[RetrievedFood],
) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _format_user_message(question, candidates)},
    ]

    for _ in range(MAX_TOOL_ITERATIONS):
        response = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=cast(Any, messages),
            tools=cast(Any, [LOOKUP_FOOD_NUTRIENTS_TOOL]),
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content or ""

        messages.append(message.model_dump(exclude_none=True))
        for tool_call in message.tool_calls:
            args = json.loads(cast(Any, tool_call).function.arguments)
            result = lookup_food_nutrients(es_client, int(args["fdc_id"]))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result) if result is not None else "not found",
                }
            )

    logger.warning("Agent loop exceeded max tool iterations for question: %r", question)
    return TOOL_ITERATION_LIMIT_ANSWER


def _format_user_message(question: str, candidates: list[RetrievedFood]) -> str:
    candidate_lines = "\n".join(
        f"- FDC ID {food.fdc_id}: {food.food_name} ({food.search_text})" for food in candidates
    )
    return (
        f"Question: {question}\n\n"
        f"Candidate foods from retrieval:\n{candidate_lines}\n\n"
        "Use the lookup_food_nutrients tool if you need specific nutrient values beyond "
        "what's summarized above."
    )
