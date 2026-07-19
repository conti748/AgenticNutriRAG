from eval.metrics import hit_rate, mrr


def test_hit_rate_all_relevant() -> None:
    assert hit_rate([[True], [False, True]]) == 1.0


def test_hit_rate_partial() -> None:
    assert hit_rate([[True, False], [False, False]]) == 0.5


def test_hit_rate_empty_relevance_is_zero() -> None:
    assert hit_rate([]) == 0.0


def test_mrr_rewards_earlier_rank() -> None:
    assert mrr([[True, False]]) == 1.0
    assert mrr([[False, True]]) == 0.5


def test_mrr_zero_when_never_found() -> None:
    assert mrr([[False, False]]) == 0.0


def test_mrr_averages_across_queries() -> None:
    assert mrr([[True], [False]]) == 0.5


def test_mrr_empty_relevance_is_zero() -> None:
    assert mrr([]) == 0.0
