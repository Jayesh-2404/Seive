from sieve import allocator


def test_learned_splits_is_a_dict() -> None:
    assert isinstance(allocator.learned_splits(), dict)


def test_learned_allocate_returns_a_valid_split() -> None:
    allocation = allocator.allocate("fix a bug", 600, 5000, learned=True)
    split = allocation["split"]
    assert set(split) == {"symbols", "semantic", "summary", "memory"}
    assert abs(sum(split.values()) - 1.0) < 1e-9
    assert sum(allocation["tokens"].values()) <= 600


def test_rule_is_still_the_default() -> None:
    rule = allocator.allocate("fix a bug", 600, 5000)
    learned = allocator.allocate("fix a bug", 600, 5000, learned=True)
    assert "learned" not in rule["reason"]
    assert isinstance(learned["split"], dict)
