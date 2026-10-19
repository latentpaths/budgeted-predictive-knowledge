"""Reproduce numerical results from the retained episode measurements."""

import csv
import hashlib
import itertools
import json
from pathlib import Path

from .experiments import (
    experiment_lookup,
    experiment_overview,
    load_episode_results,
    load_studies,
)
from .metrics import (
    CONTROL_SELECTORS,
    GROUP_KEYS,
    MODEL_NAMES,
    SELECTOR_LABELS,
    SELECTOR_ORDER,
    paired_difference,
    summarize,
)


def paired_contrasts(groups: dict) -> list[dict]:
    """Compare selectors on identical seeds within each experimental condition.

    No-update and full-update controls have their own record budgets. Other
    selectors are compared only at the same budget. Positive values favor target.
    """
    contexts = sorted({key[:4] for key in groups})
    contrasts = []
    for context in contexts:
        keys = sorted(
            (key for key in groups if key[:4] == context),
            key=lambda key: (key[5], SELECTOR_ORDER.index(key[4])),
        )
        for baseline_key, target_key in itertools.combinations(keys, 2):
            if baseline_key[5] != target_key[5] and not (
                baseline_key[4] in CONTROL_SELECTORS
                or target_key[4] in CONTROL_SELECTORS
            ):
                continue
            baseline, target = groups[baseline_key], groups[target_key]
            mean, (low, high) = paired_difference(target, baseline)
            contrasts.append(
                {
                    **dict(zip(GROUP_KEYS[:4], context)),
                    "target": target_key[4],
                    "target_budget_fraction": target_key[5],
                    "baseline": baseline_key[4],
                    "baseline_budget_fraction": baseline_key[5],
                    "n_pairs": len(target),
                    "completion_difference": mean,
                    "ci_low": low,
                    "ci_high": high,
                    "difference_pp": 100 * mean,
                    "ci_low_pp": 100 * low,
                    "ci_high_pp": 100 * high,
                }
            )
    return contrasts


def model_statistics(rows: list[dict], prices: dict) -> list[dict]:
    statistics = []
    for model in sorted({row["model"] for row in rows}):
        selected = [row for row in rows if row["model"] == model]
        sums = {
            metric: sum(row[metric] for row in selected)
            for metric in (
                "calls",
                "prompt_tokens",
                "completion_tokens",
                "updates",
                "valid_updates",
                "correct_updates",
                "api_errors",
                "missing_usage",
            )
        }
        price = prices[model]
        statistics.append(
            {
                "model": model,
                "model_name": MODEL_NAMES[model],
                "episodes": len(selected),
                **sums,
                "total_tokens": sums["prompt_tokens"] + sums["completion_tokens"],
                "parsed_update_rate": sums["valid_updates"] / sums["updates"],
                "correct_update_rate": sums["correct_updates"] / sums["updates"],
                "estimated_cost_usd": (
                    sums["prompt_tokens"] * price["input"]
                    + sums["completion_tokens"] * price["output"]
                )
                / 1e6,
            }
        )
    return statistics


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def analyze(data: Path, config: Path, output: Path) -> dict:
    """Write machine-readable results and figures; never modify the input data."""
    rows = load_episode_results(data)
    catalog = load_studies(config)
    if not rows:
        raise ValueError("episode evidence is empty")
    experiments = experiment_lookup(catalog)
    groups, summaries = summarize(rows)
    contrasts = paired_contrasts(groups)
    contrasts = [
        {**contrast, **experiments[contrast["condition_group"]]}
        for contrast in contrasts
    ]
    models = model_statistics(rows, catalog["prices"])
    conditions = []
    for key in sorted(summaries):
        summary = summaries[key].copy()
        for metric in ("completion", "success"):
            summary[f"{metric}_ci_low"], summary[f"{metric}_ci_high"] = summary.pop(
                f"{metric}_ci"
            )
        summary["selector_label"] = SELECTOR_LABELS[summary["selector"]]
        summary["record_budget"] = int(24 * summary["budget_fraction"])
        summary.update(experiments[summary["condition_group"]])
        conditions.append(summary)
    totals = {
        metric: sum(row[metric] for row in rows)
        for metric in (
            "calls",
            "prompt_tokens",
            "completion_tokens",
            "api_errors",
            "missing_usage",
            "valid_updates",
            "correct_updates",
            "updates",
        )
    }
    totals["episodes"] = len(rows)
    totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
    totals["estimated_cost_usd"] = sum(row["estimated_cost_usd"] for row in models)
    diagnostics = {
        "evidence_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
        "configuration_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "totals": totals,
        "experiments": {
            experiment["experiment_id"]: {
                "experiment_name": experiment["experiment_name"],
                "question": experiment["question"],
                **{
                    metric: sum(
                        1 if metric == "episodes" else row[metric]
                        for row in rows
                        if experiments[row["condition_group"]]["experiment_id"]
                        == experiment["experiment_id"]
                    )
                    for metric in ("episodes", "api_errors", "missing_usage")
                },
                "reference_experiment_ids": experiment["reference_experiment_ids"],
            }
            for experiment in experiment_overview(catalog)
        },
        "studies": {
            study: {
                "episodes": sum(row["study"] == study for row in rows),
                "api_errors": sum(
                    row["api_errors"] for row in rows if row["study"] == study
                ),
                "missing_usage": sum(
                    row["missing_usage"] for row in rows if row["study"] == study
                ),
            }
            for study in sorted({row["study"] for row in rows})
        },
        "excluded_collection": catalog["diagnostics"]["excluded_transport_collection"],
        "cost_basis": "Historical list-price estimate before cache discounts; excludes unreported usage and the excluded collection.",
        "uncertainty": {
            "completion": "10,000 bootstrap resamples with seed 20260912; percentile 95% intervals.",
            "paired_contrasts": "Resample within-condition paired seed differences; no multiplicity adjustment.",
            "success": "95% Wilson intervals.",
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "condition_summary.csv", conditions)
    write_csv(output / "paired_comparisons.csv", contrasts)
    write_csv(output / "model_summary.csv", models)
    (output / "validation.json").write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n"
    )
    import matplotlib.pyplot as plt

    from .figures import (
        PDF_METADATA,
        plot_cross_model_comparisons,
        plot_feedback_comparisons,
        plot_missing_dependencies,
        plot_update_budgets,
    )

    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    for name, plot, arguments in (
        ("update_budgets", plot_update_budgets, summaries),
        ("missing_dependencies", plot_missing_dependencies, rows),
        ("cross_model_comparisons", plot_cross_model_comparisons, groups),
        ("feedback_comparisons", plot_feedback_comparisons, groups),
    ):
        figure = plot(arguments)
        try:
            figure.savefig(figures / f"{name}.pdf", metadata=PDF_METADATA)
        finally:
            plt.close(figure)
    return diagnostics
