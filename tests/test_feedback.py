from itertools import combinations

import numpy as np
import pytest

from budgeted_predictive_knowledge.feedback import (
    ValidityBeliefs,
    expected_progress,
    required_sets,
    select_feedback_records,
)


def test_joint_unlocks_complementary_prerequisites():
    # Updating two prerequisites restores three goals; updating a separate error restores one.
    parents = [[], [], [0, 1], [0, 1], []]
    done = {0, 1}
    q = [0, 0, 1, 1, 0]
    assert select_feedback_records("joint", 2, parents, done, "dag", q, 0) == [0, 1]
    sets = required_sets(parents, done, "dag")
    assert expected_progress(sets, q, {0}) == expected_progress(sets, q, set())
    assert expected_progress(sets, q, {0, 1}) > expected_progress(sets, q, {0, 4})


@pytest.mark.parametrize("task", ["dag", "precedence_chains"])
def test_vectorized_selection_matches_scalar_enumeration(task):
    parents = [[], [0], [1], [0, 2], []]
    done = {0}
    q = np.array([0.2, 0, 0.8, 1, 0.5])
    sets = required_sets(parents, done, task)
    selected = select_feedback_records("joint", 2, parents, done, task, q, 4)
    optimum = max(expected_progress(sets, q, set(c)) for c in combinations(range(5), 2))
    assert expected_progress(sets, q, set(selected)) == pytest.approx(optimum)


def test_completed_predecessor_still_supplies_direct_state():
    assert required_sets([[], [0], [1]], {0}, "precedence_chains") == [
        frozenset({0, 1}),
        frozenset({0, 1, 2}),
    ]
    assert required_sets([[], [0], [1]], {0, 1}, "precedence_chains") == [
        frozenset({1, 2})
    ]


def test_feedback_tracks_cache_not_arbitrary_submitted_values():
    b = ValidityBeliefs([0.1, 0.2])
    b.observe(
        {"job": 0, "certificates": {"0": "wrong"}},
        {"reason": "stale_or_wrong_prediction", "states": ["0"]},
        [[], []],
        {"0": "cached", "1": "other"},
    )
    assert b.valid[0] == 0.9
    b.observe(
        {"job": 0, "certificates": {"0": "cached"}},
        {"reason": "stale_or_wrong_prediction", "states": ["0"]},
        [[], []],
        {"0": "cached", "1": "other"},
    )
    assert b.valid[0] == 0
    b.advance()
    assert b.valid[0] == 0


def test_observed_refresh_can_reveal_an_incorrect_updater_output():
    b = ValidityBeliefs([0.1])
    b.update([{"state": "0", "continuation": {"argument": "green@2"}}], {"0": "blue@1"})
    assert b.valid[0] == 0
