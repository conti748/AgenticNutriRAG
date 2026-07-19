from unittest.mock import MagicMock

from agent.query_rewriting import rewrite_query


def _mock_openai_client(rewritten_text: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=rewritten_text))
    ]
    return client


def test_rewrite_query_returns_llm_output_when_enabled() -> None:
    client = _mock_openai_client("protein-dense low-calorie foods")

    result = rewrite_query(client, "what should I eat for lots of protein?", enabled=True)

    assert result == "protein-dense low-calorie foods"
    client.chat.completions.create.assert_called_once()


def test_rewrite_query_passes_through_when_disabled() -> None:
    client = _mock_openai_client("should not be used")

    result = rewrite_query(client, "raw question", enabled=False)

    assert result == "raw question"
    client.chat.completions.create.assert_not_called()


def test_rewrite_query_falls_back_to_question_on_empty_response() -> None:
    client = _mock_openai_client("")

    result = rewrite_query(client, "raw question", enabled=True)

    assert result == "raw question"
