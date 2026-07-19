import json
from unittest.mock import MagicMock

from agent.rag import MIN_RELEVANCE_SCORE, NOT_FOUND_ANSWER, answer_question
from agent.retrieval import RetrievedFood

SAMPLE_QUESTIONS = [
    "How much protein is in an egg?",
    "What's a good low-calorie source of fiber?",
    "How much vitamin C does an orange have?",
]


def _rewriting_client(rewritten: str = "eggs protein") -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=rewritten))
    ]
    return client


def _stub_retrieve(monkeypatch, candidates: list[RetrievedFood]) -> None:
    monkeypatch.setattr("agent.rag.retrieve", lambda *args, **kwargs: candidates)


def _final_answer_response(text: str) -> MagicMock:
    message = MagicMock(content=text, tool_calls=None)
    return MagicMock(choices=[MagicMock(message=message)])


def _tool_call_response(fdc_id: int, call_id: str = "call_1") -> MagicMock:
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function.arguments = json.dumps({"fdc_id": fdc_id})
    message = MagicMock(content=None, tool_calls=[tool_call])
    message.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{"id": call_id}],
    }
    return MagicMock(choices=[MagicMock(message=message)])


def test_answer_question_returns_not_found_when_no_candidates(monkeypatch) -> None:
    _stub_retrieve(monkeypatch, [])
    es_client = MagicMock()
    openai_client = _rewriting_client()

    result = answer_question(es_client, openai_client, SAMPLE_QUESTIONS[0], strategy="hybrid")

    assert result.answer == NOT_FOUND_ANSWER
    assert result.sources == []


def test_answer_question_returns_not_found_below_relevance_threshold(monkeypatch) -> None:
    low_score_food = RetrievedFood(
        fdc_id=1, food_name="Water", food_category=None, search_text="Water.", score=0.0
    )
    _stub_retrieve(monkeypatch, [low_score_food])
    es_client = MagicMock()
    openai_client = _rewriting_client()

    result = answer_question(es_client, openai_client, SAMPLE_QUESTIONS[0], strategy="hybrid")

    assert result.answer == NOT_FOUND_ANSWER
    assert MIN_RELEVANCE_SCORE["hybrid"] > 0.0


def test_answer_question_generates_grounded_answer_with_sources(monkeypatch) -> None:
    food = RetrievedFood(
        fdc_id=747997,
        food_name="Egg, whole, raw",
        food_category="Dairy and Egg Products",
        search_text="Egg, whole, raw. 143 kcal, 12.6g protein.",
        score=15.0,
    )
    _stub_retrieve(monkeypatch, [food])
    es_client = MagicMock()
    openai_client = _rewriting_client()
    openai_client.chat.completions.create.side_effect = [
        openai_client.chat.completions.create.return_value,  # rewrite call
        _final_answer_response("Eggs (FDC 747997) have 12.6g of protein per 100g."),
    ]

    result = answer_question(es_client, openai_client, SAMPLE_QUESTIONS[0], strategy="hybrid")

    assert "747997" in result.answer
    assert result.sources == [food]
    assert result.retrieval_strategy == "hybrid"


def test_answer_question_handles_tool_call_round_trip(monkeypatch) -> None:
    food = RetrievedFood(
        fdc_id=747997,
        food_name="Egg, whole, raw",
        food_category="Dairy and Egg Products",
        search_text="Egg, whole, raw.",
        score=15.0,
    )
    _stub_retrieve(monkeypatch, [food])
    monkeypatch.setattr(
        "agent.rag.lookup_food_nutrients",
        lambda es_client, fdc_id: {"fdc_id": fdc_id, "nutrients": {"vitamin_d_ug": 2.0}},
    )
    es_client = MagicMock()
    openai_client = _rewriting_client()
    openai_client.chat.completions.create.side_effect = [
        openai_client.chat.completions.create.return_value,  # rewrite call
        _tool_call_response(747997),
        _final_answer_response("Egg (FDC 747997) has 2.0ug of vitamin D."),
    ]

    result = answer_question(es_client, openai_client, "How much vitamin D is in an egg?")

    assert "747997" in result.answer
    assert openai_client.chat.completions.create.call_count == 3


def test_answer_question_over_sample_questions_never_fabricates_without_sources(
    monkeypatch,
) -> None:
    _stub_retrieve(monkeypatch, [])
    es_client = MagicMock()

    for question in SAMPLE_QUESTIONS:
        openai_client = _rewriting_client()
        result = answer_question(es_client, openai_client, question, strategy="text_only")
        assert result.answer == NOT_FOUND_ANSWER
        assert result.sources == []
