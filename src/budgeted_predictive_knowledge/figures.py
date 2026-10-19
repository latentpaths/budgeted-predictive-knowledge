"""Figures of budget allocation, dependency information, and paired effects."""

from datetime import UTC, datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from .metrics import MODEL_NAMES, SELECTOR_LABELS, bootstrap_mean_interval, paired

COLORS = {
    "no_updates": "#999999",
    "all_records": "#252525",
    "even_spacing": "#56B4E9",
    "random": "#E69F00",
    "change_risk": "#009E73",
    "dependency_importance": "#0072B2",
    "risk_dependency": "#CC79A7",
}

PDF_METADATA = {
    "Creator": "budgeted-predictive-knowledge",
    "CreationDate": datetime(2026, 1, 1, tzinfo=UTC),
    "ModDate": datetime(2026, 1, 1, tzinfo=UTC),
}


def _style() -> None:
    plt.rcParams.update(
        {"font.size": 9, "axes.spines.top": False, "axes.spines.right": False}
    )


def plot_update_budgets(summaries: dict, *, sample_notes: bool = True) -> Figure:
    """Compare completion and success across record-update budgets."""
    _style()
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.5), sharex=True, sharey="row")
    for col, task in enumerate(("dag", "precedence_chains")):
        for selector in (
            "even_spacing",
            "random",
            "change_risk",
            "dependency_importance",
            "risk_dependency",
            "no_updates",
            "all_records",
        ):
            points = [
                summary
                for key, summary in summaries.items()
                if key[0] == "primary_budget_sweep"
                and key[2] == task
                and key[4] == selector
            ]
            points.sort(key=lambda item: item["budget_fraction"])
            for row_index, metric in enumerate(("success", "completion")):
                ax = axes[row_index, col]
                if selector in ("no_updates", "all_records"):
                    ax.axhline(
                        points[0][metric],
                        color=COLORS[selector],
                        linestyle="--" if selector == "all_records" else ":",
                        label=SELECTOR_LABELS[selector],
                        lw=1.2,
                    )
                else:
                    x = [point["budget_fraction"] * 100 for point in points]
                    ax.plot(
                        x,
                        [point[metric] for point in points],
                        color=COLORS[selector],
                        marker="o",
                        markersize=3,
                        label=SELECTOR_LABELS[selector],
                        lw=1.5,
                    )
                    ax.fill_between(
                        x,
                        [point[f"{metric}_ci"][0] for point in points],
                        [point[f"{metric}_ci"][1] for point in points],
                        color=COLORS[selector],
                        alpha=0.07,
                    )
                ax.set_ylim(-0.03, 1.03)
                ax.grid(alpha=0.2)
                ax.set_xticks([10, 20, 30])
        axes[0, col].set_title("DAG" if task == "dag" else "Precedence Chains")
        axes[1, col].set_xlabel("Nominal record budget (%)")
    axes[0, 0].set_ylabel("Episode success rate")
    axes[1, 0].set_ylabel("Subgoal completion rate")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.04 if sample_notes else 0, 1, 0.86))
    if sample_notes:
        fig.text(
            0.5,
            0.005,
            "24 paired seeds per condition; shaded bands: 95% intervals",
            ha="center",
            fontsize=7,
        )
    return fig


def plot_missing_dependencies(rows: list[dict], *, sample_notes: bool = True) -> Figure:
    """Compare selectors as dependency edges are withheld."""
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.4), sharey=True)
    for ax, task in zip(axes, ("dag", "precedence_chains")):
        for selector in ("dependency_importance", "risk_dependency"):
            clean = [
                row["completion"]
                for row in rows
                if row["condition_group"] == "primary_budget_sweep"
                and row["task"] == task
                and row["selector"] == selector
                and row["budget_fraction"] == 0.2
                and row["seed"] < 1012
            ]
            points = [(0, float(np.mean(clean)), bootstrap_mean_interval(clean))]
            for missing_edge_fraction in (0.3, 0.6):
                values = [
                    row["completion"]
                    for row in rows
                    if row["condition_group"] == "missing_dependencies"
                    and row["task"] == task
                    and row["selector"] == selector
                    and row["missing_edge_fraction"] == missing_edge_fraction
                ]
                points.append(
                    (
                        missing_edge_fraction,
                        float(np.mean(values)),
                        bootstrap_mean_interval(values),
                    )
                )
            x = [100 * point[0] for point in points]
            ax.plot(
                x,
                [point[1] for point in points],
                marker="o",
                color=COLORS[selector],
                label=SELECTOR_LABELS[selector],
            )
            ax.fill_between(
                x,
                [point[2][0] for point in points],
                [point[2][1] for point in points],
                color=COLORS[selector],
                alpha=0.12,
            )
        ax.set(
            title="DAG" if task == "dag" else "Precedence Chains",
            xlabel="Missing dependency edges (%)",
            ylim=(0, 1.03),
        )
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Subgoal completion rate")
    axes[1].legend(fontsize=8)
    fig.tight_layout(rect=(0, 0.07 if sample_notes else 0, 1, 1))
    if sample_notes:
        fig.text(
            0.5,
            0.005,
            "12 paired seeds per condition; shaded bands: 95% bootstrap intervals",
            ha="center",
            fontsize=7,
        )
    return fig


def plot_cross_model_comparisons(groups: dict, *, sample_notes: bool = True) -> Figure:
    """Compare paired static-selector gains across models and tasks."""
    _style()
    model_groups = [
        ("qwen/qwen3-30b-a3b-instruct-2507", "primary_budget_sweep"),
        ("openai/gpt-4.1-mini", "gpt_static"),
        ("z-ai/glm-5.3-flash", "glm_static"),
        ("qwen/qwen3.6-35b-a3b", "qwen_static"),
    ]
    fig, ax = plt.subplots(figsize=(7, 2.8))
    labels, means, lows, highs = [], [], [], []
    for model, condition_group in model_groups:
        for task in ("dag", "precedence_chains"):
            mean, interval = paired(
                groups, condition_group, model, task, "risk_dependency", "random"
            )
            labels.append(
                f"{MODEL_NAMES[model]}\n{'DAG' if task == 'dag' else 'Precedence'}"
            )
            means.append(100 * mean)
            lows.append(100 * (mean - interval[0]))
            highs.append(100 * (interval[1] - mean))
    ax.errorbar(
        np.arange(len(means)),
        means,
        yerr=[lows, highs],
        fmt="o",
        color="#0072B2",
        capsize=3,
    )
    ax.axhline(0, color="#555555", linewidth=1)
    ax.set_ylabel("RD − random progress (pp)")
    ax.set_xticks(np.arange(len(labels)), labels, fontsize=7)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout(rect=(0, 0.07 if sample_notes else 0, 1, 1))
    if sample_notes:
        fig.text(
            0.5,
            0.005,
            "Paired-seed effects: Qwen3-30B / GLM / Qwen3.6 n=24; GPT n=12. Bars: 95% bootstrap intervals",
            ha="center",
            fontsize=7,
        )
    return fig


def plot_feedback_comparisons(groups: dict, *, sample_notes: bool = True) -> Figure:
    """Compare joint selection with feedback and static selectors."""
    _style()
    models = [
        ("openai/gpt-4.1-mini", "gpt_feedback"),
        ("qwen/qwen3.6-35b-a3b", "qwen_feedback"),
    ]
    contrasts = {}
    for model, condition_group in models:
        for task in ("dag", "precedence_chains"):
            contrasts[(model, task, "risk")] = paired(
                groups, condition_group, model, task, "joint", "feedback_risk"
            )
            contrasts[(model, task, "static")] = paired(
                groups, condition_group, model, task, "joint", "risk_dependency"
            )
            if model == "openai/gpt-4.1-mini":
                contrasts[(model, task, "dependency_importance")] = paired(
                    groups,
                    condition_group,
                    model,
                    task,
                    "joint",
                    "feedback_risk_dependency",
                )

    fig, ax = plt.subplots(figsize=(7, 4.2))
    labels, means, lows, highs, colors = [], [], [], [], []
    comparison_names = {
        "risk": "FR",
        "static": "RD",
        "dependency_importance": "FRD",
    }
    for model, _ in models:
        for task in ("dag", "precedence_chains"):
            for comparison in ("risk", "static", "dependency_importance"):
                key = (model, task, comparison)
                if key not in contrasts:
                    continue
                mean, interval = contrasts[key]
                labels.append(
                    f"{MODEL_NAMES[model]} / "
                    f"{'DAG' if task == 'dag' else 'Precedence'} vs. "
                    f"{comparison_names[comparison]}"
                )
                means.append(100 * mean)
                lows.append(100 * (mean - interval[0]))
                highs.append(100 * (interval[1] - mean))
                colors.append(
                    {
                        "risk": "#0072B2",
                        "static": "#CC79A7",
                        "dependency_importance": "#E69F00",
                    }[comparison]
                )
    for y, mean, low, high, color in zip(range(len(means)), means, lows, highs, colors):
        ax.errorbar(mean, y, xerr=[[low], [high]], fmt="o", color=color, capsize=3)
    ax.axvline(0, color="#555555", linewidth=1)
    ax.set_xlabel("Joint progress difference (percentage points)")
    ax.set_yticks(range(len(labels)), labels, fontsize=8)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout(rect=(0, 0.07 if sample_notes else 0, 1, 1))
    if sample_notes:
        fig.text(
            0.5,
            0.005,
            "12 paired seeds per comparison; bars: 95% bootstrap intervals",
            ha="center",
            fontsize=7,
        )
    return fig
