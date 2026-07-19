"""Quick exploration helper: load an Elasticsearch index into a pandas DataFrame.

Usage:
    uv run python scripts/explore_es.py
    uv run python scripts/explore_es.py --index usda_foods --size 500
"""

import argparse

import pandas as pd
from elasticsearch import Elasticsearch

from config import get_settings


def load_index_to_df(client: Elasticsearch, index_name: str, size: int = 1000) -> pd.DataFrame:
    """Fetch up to `size` documents from an index and flatten them into a DataFrame."""
    response = client.search(index=index_name, size=size, query={"match_all": {}})
    hits = response["hits"]["hits"]
    records = [{"_id": hit["_id"], **hit["_source"]} for hit in hits]
    return pd.json_normalize(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default="usda_foods", help="Index name to load")
    parser.add_argument("--size", type=int, default=1000, help="Max number of documents to fetch")
    args = parser.parse_args()

    settings = get_settings()
    client = Elasticsearch(settings.elasticsearch_url)

    df = load_index_to_df(client, args.index, args.size)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print(f"Loaded {len(df)} documents from '{args.index}'\n")
    print(df.head())
    print("\nColumns:", list(df.columns))

    # Drop into an interactive shell with `df` available for further exploration.
    import code

    code.interact(
        local={"df": df, "client": client}, banner="\n`df` and `client` are ready. Ctrl-D to exit."
    )


if __name__ == "__main__":
    main()
