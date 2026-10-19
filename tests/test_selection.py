import pytest

from budgeted_predictive_knowledge.selection import (
    STATIC_SELECTORS,
    dependency_importance,
    select,
)


@pytest.mark.parametrize("selector", STATIC_SELECTORS)
@pytest.mark.parametrize("budget_fraction", [0, 0.1, 0.2, 1])
def test_budget(selector, budget_fraction):
    edges = [[1], [2], []]
    selected = select(selector, budget_fraction, edges, [0.1] * 3, 0)
    expected = (
        3
        if selector == "all_records"
        else 0
        if selector == "no_updates"
        else int(3 * budget_fraction)
    )
    assert len(selected) == len(set(selected)) == expected
    assert all(0 <= i < 3 for i in selected)


def test_diamond_counts_descendant_once():
    assert dependency_importance([[1, 2], [3], [3], []], 1) == [4, 2, 2, 1]


def test_invalid_graph():
    with pytest.raises(ValueError):
        dependency_importance([[0]])
