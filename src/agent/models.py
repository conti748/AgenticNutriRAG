"""Data models shared across the agent's retrieval and generation flow."""

from pydantic import BaseModel


class RetrievedFood(BaseModel):
    """A candidate food document returned by retrieval, with its relevance score."""

    fdc_id: int
    food_name: str
    food_category: str | None
    search_text: str
    score: float


class AgentAnswer(BaseModel):
    """The agent's final response to a nutrition question."""

    answer: str
    rewritten_query: str
    retrieval_strategy: str
    sources: list[RetrievedFood]
