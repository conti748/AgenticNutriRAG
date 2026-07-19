"""Answer-quality scoring: embedding cosine-similarity and LLM-as-judge.

Two independent, complementary ways to score a generated answer against a reference
answer (design.md Decision 5): cosine similarity between their embeddings (cheap,
purely semantic), and an LLM judge rubric (captures faithfulness/relevance nuance
that embedding similarity alone can miss).
"""

import math

from openai import OpenAI

from agent.query_rewriting import CHAT_MODEL
from ingestion.embeddings import embed_texts

LLM_JUDGE_SYSTEM_PROMPT = (
    "You are grading a nutrition assistant's answer against a reference answer, both "
    "written to answer the same question from the same underlying food data. Rate the "
    "generated answer's relevance (does it address the question) and faithfulness (does "
    "it agree with the reference, without fabricating facts) on a single 1-5 scale: "
    "1 = irrelevant or contradicts the reference, 3 = partially relevant/faithful, "
    "5 = fully relevant and faithful. Respond with only the integer score."
)

MIN_JUDGE_SCORE = 1
MAX_JUDGE_SCORE = 5


class JudgeScoreParseError(ValueError):
    """Raised when the LLM judge doesn't return a parseable integer score."""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors, 0.0 if either is a zero vector."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def score_cosine_similarity(
    openai_client: OpenAI, generated_answer: str, reference_answer: str
) -> float:
    """Embed both answers and return their cosine similarity."""
    generated_vector, reference_vector = embed_texts(
        openai_client, [generated_answer, reference_answer]
    )
    return cosine_similarity(generated_vector, reference_vector)


def score_llm_judge(
    openai_client: OpenAI, question: str, reference_answer: str, generated_answer: str
) -> float:
    """Ask an LLM judge to rate the generated answer 1-5 against the reference."""
    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": LLM_JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Reference answer: {reference_answer}\n\n"
                    f"Generated answer: {generated_answer}"
                ),
            },
        ],
        temperature=0,
    )
    return float(_parse_judge_score(response.choices[0].message.content))


def _parse_judge_score(content: str | None) -> int:
    """Extract and clamp an integer 1-5 score from the judge's raw response."""
    digits = "".join(ch for ch in (content or "").strip() if ch.isdigit())
    if not digits:
        raise JudgeScoreParseError(f"LLM judge response not parseable as a score: {content!r}")
    return min(max(int(digits[0]), MIN_JUDGE_SCORE), MAX_JUDGE_SCORE)
