"""Hit rate and MRR metrics for retrieval evaluation.

Both take a `relevance` matrix: one boolean list per query, ranked in retrieval
order, where an entry is True if that retrieved result matches the query's
expected answer.
"""


def hit_rate(relevance: list[list[bool]]) -> float:
    """Fraction of queries with at least one relevant result anywhere in the ranking."""
    if not relevance:
        return 0.0
    return sum(any(query_relevance) for query_relevance in relevance) / len(relevance)


def mrr(relevance: list[list[bool]]) -> float:
    """Mean reciprocal rank of the first relevant result per query (0 if none found)."""
    if not relevance:
        return 0.0
    total = 0.0
    for query_relevance in relevance:
        for rank, is_relevant in enumerate(query_relevance, start=1):
            if is_relevant:
                total += 1.0 / rank
                break
    return total / len(relevance)
