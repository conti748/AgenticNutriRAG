"""Client for the USDA FoodData Central API.

Only the ``Foundation Foods`` data type is fetched (see project README's
Dataset section) to bound embedding cost/time to a subset of a few thousand
records rather than the full 300k+ item corpus.
"""

from collections.abc import Iterator
from typing import Any

import requests

FDC_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
FOUNDATION_FOODS_DATA_TYPE = "Foundation"
PAGE_SIZE = 200


class USDAClient:
    """Fetches food records from the USDA FoodData Central API."""

    def __init__(self, api_key: str, base_url: str = FDC_BASE_URL) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._session = requests.Session()

    def iter_foods(
        self,
        data_type: str = FOUNDATION_FOODS_DATA_TYPE,
        page_size: int = PAGE_SIZE,
    ) -> Iterator[dict[str, Any]]:
        """Yield raw food records for the given data type, handling pagination."""
        page_number = 1
        while True:
            page = self._fetch_page(data_type, page_size, page_number)
            if not page:
                return
            yield from page
            if len(page) < page_size:
                return
            page_number += 1

    def _fetch_page(self, data_type: str, page_size: int, page_number: int) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "api_key": self._api_key,
            "dataType": data_type,
            "pageSize": page_size,
            "pageNumber": page_number,
        }
        response = self._session.get(
            f"{self._base_url}/foods/list",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()
        return result
