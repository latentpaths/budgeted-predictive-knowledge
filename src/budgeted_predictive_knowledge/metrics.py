"""Condition summaries and paired-seed comparisons used in the paper."""

import math
from collections import defaultdict

import numpy as np

GROUP_KEYS = (
    "condition_group",
    "model",
    "task",
    "missing_edge_fraction",
    "selector",
    "budget_fraction",
)
SELECTOR_ORDER = (
    "random",
    "even_spacing",
    "change_risk",
    "dependency_importance",
    "risk_dependency",
    "feedback_risk",
    "feedback_risk_dependency",
    "joint",
    "no_updates",
    "all_records",
)
SELECTOR_LABELS = {
    "no_updates": "No updates",
    "all_records": "All records",
    "even_spacing": "Even spacing",
    "random": "Random",
    "change_risk": "R",
    "dependency_importance": "D",
    "risk_dependency": "RD",
    "feedback_risk": "FR",
    "feedback_risk_dependency": "FRD",
    "joint": "Joint",
}
CONTROL_SELECTORS = frozenset({"no_updates", "all_records"})
MODEL_NAMES = {
    "qwen/qwen3-30b-a3b-instruct-2507": "Qwen3-30B",
    "openai/gpt-4.1-mini": "GPT-4.1-mini",
    "z-ai/glm-5.3-flash": "GLM-5.3-Flash",
    "qwen/qwen3.6-35b-a3b": "Qwen3.6-35B",
}


def wilson_interval(successes: float, n: int) -> list[float]:
    p = successes / n
    z = 1.959963984540054
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0, center - half), min(1, center + half)]


def bootstrap_mean_interval(values: list[float]) -> list[float]:
    array = np.asarray(values)
    rng = np.random.default_rng(20260912)
    means = rng.choice(array, size=(10_000, len(array)), replace=True).mean(axis=1)
    return np.quantile(means, [0.025, 0.975]).tolist()


def summarize(rows: list[dict]) -> tuple[dict[tuple, list[dict]], dict[tuple, dict]]:
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in GROUP_KEYS)].append(row)
    summaries = {}
    for key, group in groups.items():
        summary = dict(zip(GROUP_KEYS, key))
        summary.update(n=len(group), successes=sum(row["success"] for row in group))
        for metric in (
            "success",
            "completion",
            "calls",
            "updates",
            "stale_errors",
            "invalid_actions",
            "prompt_tokens",
            "completion_tokens",
            "latency_seconds",
        ):
            values = [row[metric] for row in group]
            summary[metric] = float(np.mean(values))
            if metric == "success":
                summary["success_ci"] = wilson_interval(sum(values), len(values))
            elif metric == "completion":
                summary["completion_ci"] = bootstrap_mean_interval(values)
        summary["total_tokens"] = (
            summary["prompt_tokens"] + summary["completion_tokens"]
        )
        summary["selection_seconds"] = float(
            np.mean(
                [
                    row.get("selection_seconds", 0.0) / max(1, len(row["selected"]))
                    for row in group
                ]
            )
        )
        summaries[key] = summary
    return groups, summaries


def get_summary(
    summaries: dict[tuple, dict],
    condition_group: str,
    task: str,
    selector: str,
    budget_fraction: float | None = None,
) -> dict:
    if budget_fraction is None:
        budget_fraction = (
            1.0
            if selector == "all_records"
            else 0.0
            if selector == "no_updates"
            else 0.2
        )
    matches = [
        summary
        for key, summary in summaries.items()
        if key[0] == condition_group
        and key[2] == task
        and key[4] == selector
        and key[5] == budget_fraction
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one summary for {condition_group}/{task}/{selector}"
        )
    return matches[0]


def paired(
    groups: dict[tuple, list[dict]],
    condition_group: str,
    model: str,
    task: str,
    target: str,
    baseline: str,
    budget_fraction: float = 0.2,
) -> tuple[float, list[float]]:
    """Compare two selectors at the same budget with complete dependencies."""
    return paired_difference(
        groups[(condition_group, model, task, 0.0, target, budget_fraction)],
        groups[(condition_group, model, task, 0.0, baseline, budget_fraction)],
    )


def paired_difference(
    target: list[dict], baseline: list[dict]
) -> tuple[float, list[float]]:
    """Mean target-minus-baseline completion and bootstrap interval on paired seeds."""
    left = {row["seed"]: row for row in target}
    right = {row["seed"]: row for row in baseline}
    if len(left) != len(target) or len(right) != len(baseline):
        raise ValueError("duplicate seed in paired contrast")
    if not left or left.keys() != right.keys():
        raise ValueError("unpaired contrast: selector seed sets differ")
    seeds = sorted(left)
    delta = [left[seed]["completion"] - right[seed]["completion"] for seed in seeds]
    return float(np.mean(delta)), bootstrap_mean_interval(delta)
