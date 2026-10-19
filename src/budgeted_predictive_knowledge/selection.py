"""Budgeted selection using only supplied, pre-update information."""

import math
import random
from collections import deque

STATIC_SELECTORS = (
    "no_updates",
    "even_spacing",
    "random",
    "change_risk",
    "dependency_importance",
    "risk_dependency",
    "all_records",
)


def dependency_importance(edges: list[list[int]], discount: float = 0.9) -> list[float]:
    """Count each reachable decision once, using shortest dependency distance.

    Every vertex is a job. Graphs must be topologically ordered DAGs.
    """
    if not 0 <= discount <= 1:
        raise ValueError("discount must be in [0, 1]")
    n = len(edges)
    for i, children in enumerate(edges):
        if any(j <= i or j >= n for j in children):
            raise ValueError("edges must form a topologically ordered DAG")
    scores = []
    for i in range(n):
        distances = {i: 0}
        queue = deque([i])
        while queue:
            v = queue.popleft()
            for child in edges[v]:
                if child not in distances:
                    distances[child] = distances[v] + 1
                    queue.append(child)
        scores.append(sum(discount**d for d in distances.values()))
    return scores


def select(
    selector: str,
    budget_fraction: float,
    edges: list[list[int]],
    change_risk: list[float],
    seed: int,
) -> list[int]:
    n = len(edges)
    if (
        selector not in STATIC_SELECTORS
        or not 0 <= budget_fraction <= 1
        or len(change_risk) != n
    ):
        raise ValueError("invalid selector, budget fraction, or signal length")
    if any(not math.isfinite(x) or x < 0 for x in change_risk):
        raise ValueError("change risk must be finite and nonnegative")
    k = (
        n
        if selector == "all_records"
        else 0
        if selector == "no_updates"
        else math.floor(n * budget_fraction)
    )
    rng = random.Random(seed)
    order = list(range(n))
    rng.shuffle(order)  # randomized, reproducible tie-breaking; no position advantage
    if selector == "even_spacing":
        return [math.floor((j + 0.5) * n / k) for j in range(k)]
    if selector in ("dependency_importance", "risk_dependency"):
        scores = dependency_importance(edges)
        if selector == "risk_dependency":
            scores = [s * u for s, u in zip(scores, change_risk)]
        order.sort(key=lambda i: scores[i], reverse=True)
    elif selector == "change_risk":
        order.sort(key=lambda i: change_risk[i], reverse=True)
    return sorted(order[:k])
