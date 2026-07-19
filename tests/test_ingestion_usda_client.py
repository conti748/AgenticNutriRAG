from unittest.mock import MagicMock, patch

from ingestion.usda_client import USDAClient


def _response(payload: list[dict]) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_iter_foods_paginates_until_short_page() -> None:
    client = USDAClient(api_key="test-key")
    full_page = [{"fdcId": i} for i in range(2)]
    short_page = [{"fdcId": 100}]

    with patch.object(client._session, "get") as mock_get:
        mock_get.side_effect = [_response(full_page), _response(short_page)]

        foods = list(client.iter_foods(page_size=2))

    assert [f["fdcId"] for f in foods] == [0, 1, 100]
    assert mock_get.call_count == 2


def test_iter_foods_stops_on_empty_page() -> None:
    client = USDAClient(api_key="test-key")

    with patch.object(client._session, "get") as mock_get:
        mock_get.side_effect = [_response([])]

        foods = list(client.iter_foods(page_size=200))

    assert foods == []
    assert mock_get.call_count == 1


def test_iter_foods_passes_api_key_and_data_type() -> None:
    client = USDAClient(api_key="secret")

    with patch.object(client._session, "get") as mock_get:
        mock_get.return_value = _response([])

        list(client.iter_foods(data_type="Foundation", page_size=10))

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["api_key"] == "secret"
    assert kwargs["params"]["dataType"] == "Foundation"
    assert kwargs["params"]["pageSize"] == 10
    assert kwargs["params"]["pageNumber"] == 1
