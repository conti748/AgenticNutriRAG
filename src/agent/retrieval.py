"""Retrieval strategies over the hybrid Elasticsearch index: text, vector, and RRF hybrid.

All three strategies are exposed behind a single ``retrieve`` interface selected by a
``RetrievalStrategy`` argument, so callers (the agent loop, the evaluation harness) can
switch strategy without changing any other code.
"""

from typing import Any

from elasticsearch import Elasticsearch
from openai import OpenAI

from agent.models import RetrievedFood
from config import RetrievalStrategy
from ingestion.elasticsearch_index import INDEX_NAME
from ingestion.embeddings import embed_texts

DEFAULT_TOP_K = 5
NUM_CANDIDATES_MULTIPLIER = 10

# Reciprocal rank fusion for hybrid retrieval is computed in application code rather
# than via Elasticsearch's native `retriever`/RRF query, which requires an Enterprise
# or trial license and 403s on the free Basic license (see design.md Decision 2).
RRF_RANK_CONSTANT = 60
HYBRID_CANDIDATE_MULTIPLIER = 4


def retrieve(
    es_client: Elasticsearch,
    openai_client: OpenAI,
    query: str,
    strategy: RetrievalStrategy,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedFood]:
    """Retrieve candidate foods for a query using the given retrieval strategy."""
    if strategy == "text_only":
        response = _search_text_only(es_client, query, top_k)
        return [_to_retrieved_food(hit) for hit in response["hits"]["hits"]]
    if strategy == "vector_only":
        response = _search_vector_only(es_client, openai_client, query, top_k)
        return [_to_retrieved_food(hit) for hit in response["hits"]["hits"]]
    if strategy == "hybrid":
        return _search_hybrid(es_client, openai_client, query, top_k)
    raise ValueError(f"Unknown retrieval strategy: {strategy!r}")


def _search_text_only(es_client: Elasticsearch, query: str, top_k: int) -> Any:
    return es_client.search(
        index=INDEX_NAME,
        query={"match": {"search_text": query}},
        size=top_k,
    )


def _search_vector_only(
    es_client: Elasticsearch, openai_client: OpenAI, query: str, top_k: int
) -> Any:
    return es_client.search(
        index=INDEX_NAME,
        knn=_knn_clause(openai_client, query, top_k),
        size=top_k,
    )


def _search_hybrid(
    es_client: Elasticsearch, openai_client: OpenAI, query: str, top_k: int
) -> list[RetrievedFood]:
    """Fuse separate BM25 and kNN result lists via reciprocal rank fusion."""
    fetch_size = top_k * HYBRID_CANDIDATE_MULTIPLIER
    text_hits = _search_text_only(es_client, query, fetch_size)["hits"]["hits"]
    vector_hits = _search_vector_only(es_client, openai_client, query, fetch_size)["hits"]["hits"]

    fused_scores: dict[str, float] = {}
    sources: dict[str, dict[str, Any]] = {}
    for hits in (text_hits, vector_hits):
        for rank, hit in enumerate(hits, start=1):
            doc_id = hit["_id"]
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + 1.0 / (RRF_RANK_CONSTANT + rank)
            sources.setdefault(doc_id, hit["_source"])

    ranked_ids = sorted(fused_scores, key=lambda doc_id: fused_scores[doc_id], reverse=True)
    return [
        _to_retrieved_food({"_score": fused_scores[doc_id], "_source": sources[doc_id]})
        for doc_id in ranked_ids[:top_k]
    ]


def _knn_clause(openai_client: OpenAI, query: str, top_k: int) -> dict[str, Any]:
    vector = embed_texts(openai_client, [query])[0]
    return {
        "field": "embedding",
        "query_vector": vector,
        "k": top_k,
        "num_candidates": top_k * NUM_CANDIDATES_MULTIPLIER,
    }


def _to_retrieved_food(hit: dict[str, Any]) -> RetrievedFood:
    source = hit["_source"]
    return RetrievedFood(
        fdc_id=int(source["fdc_id"]),
        food_name=source["food_name"],
        food_category=source.get("food_category"),
        search_text=source["search_text"],
        score=hit["_score"],
    )
