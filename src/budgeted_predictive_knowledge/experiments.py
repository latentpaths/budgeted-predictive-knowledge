"""Study inputs, deterministic episode specifications, and request settings."""

import hashlib
import json
from pathlib import Path

STUDIES_PATH = Path("experiments/studies.json")
EPISODES_PATH = Path("experiments/episode_results.jsonl")
ANALYSIS_PATH = Path("output/analysis")
RUNS_PATH = Path("output/runs")
IDENTITY_FIELDS = (
    "condition_group",
    "model",
    "seed",
    "task",
    "selector",
    "budget_fraction",
    "missing_edge_fraction",
)


def load_studies(path: Path = STUDIES_PATH) -> dict:
    return json.loads(path.read_text())


def load_episode_results(path: Path = EPISODES_PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def experiment_lookup(catalog: dict) -> dict[str, dict]:
    """Assign each historical condition group to one scientific question.

    Presentation metadata is separate from run configurations and episode identity.
    References reuse results for comparison without assigning or counting them twice.
    """
    configured = [
        group["name"]
        for study in catalog["studies"].values()
        for group in study["condition_groups"]
    ]
    if len(configured) != len(set(configured)):
        raise ValueError("condition group names must be globally unique")
    experiments = catalog["experiment_catalog"]
    ids = [experiment["id"] for experiment in experiments]
    if len(ids) != len(set(ids)):
        raise ValueError("experiment IDs must be unique")
    lookup = {}
    for experiment in experiments:
        for reference in experiment.get("reference_experiment_ids", []):
            if reference not in ids or reference == experiment["id"]:
                raise ValueError(f"invalid experiment reference: {reference}")
        for name in experiment["condition_groups"]:
            if name in lookup:
                raise ValueError(
                    f"condition group belongs to multiple experiments: {name}"
                )
            lookup[name] = {
                "experiment_id": experiment["id"],
                "experiment_name": experiment["name"],
            }
    if set(lookup) != set(configured):
        raise ValueError(
            "experiment catalog must cover exactly the configured condition groups"
        )
    return lookup


def experiment_overview(catalog: dict) -> list[dict]:
    """Describe questions, models, and budgets from the configured run matrices."""
    from .metrics import CONTROL_SELECTORS, MODEL_NAMES

    lookup = experiment_lookup(catalog)
    specs = [
        spec for study in catalog["studies"].values() for spec in episode_specs(study)
    ]
    overview = []
    for experiment in catalog["experiment_catalog"]:
        selected = [
            spec
            for spec in specs
            if lookup[spec["condition_group"]]["experiment_id"] == experiment["id"]
        ]
        models = []
        for model in dict.fromkeys(spec["model"] for spec in selected):
            episodes = [spec for spec in selected if spec["model"] == model]
            budgets = {
                "record_budgets": sorted(
                    {
                        int(24 * spec["budget_fraction"])
                        for spec in episodes
                        if spec["selector"] not in CONTROL_SELECTORS
                    }
                ),
                "control_budgets": sorted(
                    {
                        int(24 * spec["budget_fraction"])
                        for spec in episodes
                        if spec["selector"] in CONTROL_SELECTORS
                    }
                ),
            }
            models.append(
                {
                    "model": model,
                    "model_name": MODEL_NAMES.get(model, model),
                    "episode_count": len(episodes),
                    **budgets,
                }
            )
        overview.append(
            {
                "experiment_id": experiment["id"],
                "experiment_name": experiment["name"],
                "question": experiment["question"],
                "episode_count": len(selected),
                "models": models,
                "condition_groups": experiment["condition_groups"],
                "reference_experiment_ids": experiment.get(
                    "reference_experiment_ids", []
                ),
                "reference_note": experiment.get("reference_note", ""),
            }
        )
    return overview


def episode_id(spec: dict) -> str:
    """Identify an experimental condition and seed independently of measurements."""
    identity = {field: spec[field] for field in IDENTITY_FIELDS}
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[
        :20
    ]


def episode_specs(config: dict) -> list[dict]:
    episodes = []
    for group in config["condition_groups"]:
        conditions = [
            (selector, budget)
            for selector in group["selectors"]
            for budget in group["budget_fractions"]
        ]
        conditions += [
            (selector, 0 if selector == "no_updates" else 1)
            for selector in group.get("controls", [])
        ]
        for seed in range(group["seed_start"], group["seed_start"] + group["seeds"]):
            for task in group["tasks"]:
                for missing in group.get("missing_edge_fractions", [0.0]):
                    for selector, budget in conditions:
                        spec = {
                            "condition_group": group["name"],
                            "model": group["model"],
                            "seed": seed,
                            "task": task,
                            "selector": selector,
                            "budget_fraction": budget,
                            "missing_edge_fraction": missing,
                        }
                        spec["episode_id"] = episode_id(spec)
                        episodes.append(spec)
    return episodes


def merged_transport(catalog: dict, study: dict) -> dict:
    transport = {**catalog["transport"], **study.get("transport", {})}
    transport["rate_limit"] = {
        **catalog["transport"]["rate_limit"],
        **study.get("transport", {}).get("rate_limit", {}),
    }
    return transport


def call_upper_bound(episodes: list[dict]) -> int:
    return sum(8 + (0 if spec["selector"] == "no_updates" else 2) for spec in episodes)


def plan_run(study: str, catalog: dict) -> dict:
    config = catalog["studies"][study]
    episodes = episode_specs(config)
    expected = call_upper_bound(episodes)
    if expected > config["max_calls"]:
        raise ValueError(f"Expected {expected} calls exceeds cap")
    return {
        "study": study,
        "episode_count": len(episodes),
        "logical_call_upper_bound": expected,
        "logical_call_cap": config["max_calls"],
        "transport": merged_transport(catalog, config),
        "request_options": catalog["request_options"],
        "episodes": episodes,
    }
