from unittest.mock import MagicMock

from agent.retrieval import retrieve


def _es_response(fdc_ids: list[int]) -> dict:
    return {
        "hits": {
            "hits": [
                {
                    "_id": str(fdc_id),
                    "_score": 10.0 - i,
                    "_source": {
                        "fdc_id": str(fdc_id),
                        "food_name": f"Food {fdc_id}",
                        "food_category": "Test Category",
                        "search_text": f"Food {fdc_id} description.",
                    },
                }
                for i, fdc_id in enumerate(fdc_ids)
            ]
        }
    }


def _openai_client_with_embedding() -> MagicMock:
    client = MagicMock()
    client.embeddings.create.return_value.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    return client


def test_retrieve_text_only_uses_match_query() -> None:
    es_client = MagicMock()
    es_client.search.return_value = _es_response([1, 2])
    openai_client = MagicMock()

    results = retrieve(es_client, openai_client, "eggs", strategy="text_only", top_k=2)

    _, kwargs = es_client.search.call_args
    assert kwargs["query"] == {"match": {"search_text": "eggs"}}
    assert "knn" not in kwargs
    assert "retriever" not in kwargs
    assert [food.fdc_id for food in results] == [1, 2]
    openai_client.embeddings.create.assert_not_called()


def test_retrieve_vector_only_uses_knn_query() -> None:
    es_client = MagicMock()
    es_client.search.return_value = _es_response([3])
    openai_client = _openai_client_with_embedding()

    results = retrieve(es_client, openai_client, "eggs", strategy="vector_only", top_k=1)

    _, kwargs = es_client.search.call_args
    assert kwargs["knn"]["field"] == "embedding"
    assert kwargs["knn"]["query_vector"] == [0.1, 0.2, 0.3]
    assert kwargs["knn"]["k"] == 1
    assert results[0].fdc_id == 3


def test_retrieve_hybrid_issues_separate_text_and_vector_queries() -> None:
    es_client = MagicMock()
    es_client.search.side_effect = [_es_response([1, 2, 3]), _es_response([3, 4])]
    openai_client = _openai_client_with_embedding()

    retrieve(es_client, openai_client, "eggs", strategy="hybrid", top_k=2)

    first_call, second_call = es_client.search.call_args_list
    assert first_call.kwargs["query"] == {"match": {"search_text": "eggs"}}
    assert second_call.kwargs["knn"]["field"] == "embedding"


def test_retrieve_hybrid_fuses_results_via_reciprocal_rank_fusion() -> None:
    es_client = MagicMock()
    # food 3 appears in both lists (text rank 3, vector rank 1), so it should be
    # fused to the top despite not being the top hit in either individual query.
    es_client.search.side_effect = [_es_response([1, 2, 3]), _es_response([3, 4])]
    openai_client = _openai_client_with_embedding()

    results = retrieve(es_client, openai_client, "eggs", strategy="hybrid", top_k=2)

    assert [food.fdc_id for food in results] == [3, 1]
    assert results[0].score > results[1].score


def test_retrieve_parses_scores_and_category() -> None:
    es_client = MagicMock()
    es_client.search.return_value = _es_response([7])
    openai_client = MagicMock()

    results = retrieve(es_client, openai_client, "eggs", strategy="text_only")

    assert results[0].score == 10.0
    assert results[0].food_category == "Test Category"
    assert results[0].search_text == "Food 7 description."
