"""Feedback-conditioned update selection using only observable information.

Joint selection enumerates size-k subsets and numerically maximizes a
requirement-validity proxy, treating scores within 1e-12 as ties. It does not
query unselected hidden state or simulate an oracle policy.
"""

import random
from functools import lru_cache
from itertools import combinations

import numpy as np


class ValidityBeliefs:
    """Independent probabilities that the current cached predictions remain valid."""

    def __init__(self, risk):
        self.risk = np.asarray(risk, dtype=float)
        self.valid = 1 - self.risk

    def advance(self):
        self.valid *= 1 - self.risk

    def update(self, evidence, predictions):
        # The validated target is observed only for records already selected.
        for record in evidence:
            i = record["state"]
            self.valid[int(i)] = float(
                predictions[i] == record["continuation"]["argument"]
            )

    def observe(self, action, reply, parents, predictions):
        if not isinstance(action, dict) or type(action.get("job")) is not int:
            return
        j = action["job"]
        if not 0 <= j < len(parents):
            return
        cert = action.get("certificates", {})
        if not isinstance(cert, dict):
            return
        if not reply.get("ok") and reply.get("reason") != "stale_or_wrong_prediction":
            return
        wrong = set(reply.get("states", []))
        for i in [j, *parents[j]]:
            # Feedback about a different submitted value does not certify the cache.
            if cert.get(str(i)) == predictions[str(i)]:
                self.valid[i] = float(str(i) not in wrong)
            elif str(i) not in wrong:
                self.valid[i] = 0.0


def required_sets(parents, done, task):
    """State requirements for each unfinished subgoal, including unfinished predecessors."""
    sets = []
    for j in range(len(parents)):
        if j in done:
            continue
        pending = [j]
        needed = set()
        seen = set()
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            needed.update([node, *parents[node]])
            if task == "precedence_chains":
                pending.extend(p for p in parents[node] if p not in done)
        sets.append(frozenset(needed))
    return sets


@lru_cache(maxsize=16)
def candidate_sets(n, k):
    candidates = tuple(combinations(range(n), k))
    masks = np.array([sum(1 << i for i in c) for c in candidates], dtype=np.uint32)
    return candidates, masks


def expected_progress(sets, validity, selected):
    """Reference scalar objective, useful for independent verification."""
    return sum(
        float(np.prod([validity[i] for i in needed if i not in selected]))
        for needed in sets
    )


def select_feedback_records(selector, k, parents, done, task, validity, seed):
    n = len(parents)
    q = np.asarray(validity, dtype=float)
    if q.shape != (n,) or not np.all(np.isfinite(q)) or np.any((q < 0) | (q > 1)):
        raise ValueError("validity must contain one probability per state")
    if not 0 <= k <= n or n > 31:
        raise ValueError("exact selector supports at most 31 states and a valid budget")
    sets = required_sets(parents, done, task)
    rng = random.Random(seed)
    order = list(range(n))
    rng.shuffle(order)
    if selector in ("feedback_risk", "feedback_risk_dependency"):
        weights = [sum(i in needed for needed in sets) for i in range(n)]
        score = (1 - q) if selector == "feedback_risk" else (1 - q) * np.array(weights)
        order.sort(key=lambda i: score[i], reverse=True)
        return sorted(order[:k])
    if selector != "joint":
        raise ValueError("unknown feedback selector")
    candidates, masks = candidate_sets(n, k)
    scores = np.zeros(len(candidates))
    for needed in sets:
        probability = np.ones(len(candidates))
        for i in needed:
            probability *= np.where((masks & (1 << i)) != 0, 1.0, q[i])
        scores += probability
    best = np.flatnonzero(np.isclose(scores, scores.max(), rtol=0, atol=1e-12))
    return list(candidates[int(best[rng.randrange(len(best))])])
