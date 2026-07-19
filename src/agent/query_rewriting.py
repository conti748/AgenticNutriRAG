"""LLM-based query rewriting: turns a conversational question into a search-optimized query."""

from openai import OpenAI

CHAT_MODEL = "gpt-4o-mini"

REWRITE_SYSTEM_PROMPT = (
    "You rewrite user questions about food and nutrition into short, keyword-focused "
    "search queries for a food database. Name specific foods, nutrients, or food "
    "categories where possible. Respond with only the rewritten query, no explanation."
)


def rewrite_query(client: OpenAI, question: str, enabled: bool = True) -> str:
    """Rewrite the user's question into a search-optimized query, or pass it through as-is."""
    if not enabled:
        return question

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    rewritten = response.choices[0].message.content
    return rewritten.strip() if rewritten else question
