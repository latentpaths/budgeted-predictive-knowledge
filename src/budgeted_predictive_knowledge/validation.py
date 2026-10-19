"""Deterministic validation for study configuration, tasks, and released episodes."""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from .environments import BenchmarkEnv
from .experiments import (
    EPISODES_PATH,
    STUDIES_PATH,
    episode_id,
    episode_specs,
    experiment_lookup,
    experiment_overview,
    load_episode_results,
    load_studies,
)

EXPECTED_COUNTS = {
    "primary_static": 912,
    "gpt_static": 144,
    "additional_static": 576,
    "feedback": 240,
}
EXPECTED_MODELS = {
    "qwen/qwen3-30b-a3b-instruct-2507",
    "openai/gpt-4.1-mini",
    "z-ai/glm-5.3-flash",
    "qwen/qwen3.6-35b-a3b",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(
    root: Path | None = None, *, data: Path | None = None, config: Path | None = None
) -> dict:
    root = root or Path.cwd()
    data = data or root / EPISODES_PATH
    config = config or root / STUDIES_PATH
    catalog = load_studies(config)
    experiments = experiment_lookup(catalog)
    rows = load_episode_results(data)
    required = {
        "study",
        "episode_id",
        "condition_group",
        "model",
        "seed",
        "task",
        "selector",
        "budget_fraction",
        "missing_edge_fraction",
        "completion",
        "success",
        "completed",
        "attempts",
        "calls",
        "update_calls",
        "updates",
        "valid_updates",
        "correct_updates",
        "prompt_tokens",
        "completion_tokens",
        "missing_usage",
        "api_errors",
        "latency_seconds",
        "invalid_actions",
        "stale_errors",
        "selected",
        "round_completion",
        "feedback",
    }
    require(len(rows) == 1872, "expected 1,872 episode records")
    require(
        Counter(row.get("study") for row in rows) == EXPECTED_COUNTS,
        "study counts do not match the released matrix",
    )
    require(
        {row.get("model") for row in rows} == EXPECTED_MODELS,
        "model set does not match the released matrix",
    )
    require(
        all(required <= row.keys() for row in rows),
        "episode record is missing required fields",
    )
    require(
        len({row["episode_id"] for row in rows}) == len(rows),
        "episode identifiers are not globally unique",
    )
    for row in rows:
        require(
            isinstance(row["episode_id"], str)
            and row["episode_id"] == episode_id(row)
            and isinstance(row["seed"], int)
            and row["task"] in {"dag", "precedence_chains"}
            and isinstance(row["selector"], str)
            and isinstance(row["budget_fraction"], (int, float))
            and isinstance(row["missing_edge_fraction"], (int, float))
            and 0 <= row["completion"] <= 1
            and row["success"] in {0, 1}
            and math.isclose(row["completed"], 24 * row["completion"])
            and row["success"] == int(row["completed"] == 24)
            and isinstance(row["selected"], list)
            and isinstance(row["feedback"], list),
            f"invalid episode schema or values for {row['episode_id']}",
        )
        require(
            row["study"] != "feedback"
            or (
                isinstance(row.get("selection_seconds"), (int, float))
                and isinstance(row.get("belief_history"), list)
            ),
            f"feedback diagnostics are missing for {row['episode_id']}",
        )

    expected_order = []
    task_keys = set()
    fingerprints = {}
    for study, config in catalog["studies"].items():
        episodes = episode_specs(config)
        require(
            len(episodes) == EXPECTED_COUNTS[study],
            f"configured episode count changed for {study}",
        )
        require(
            len(episodes) == len({spec["episode_id"] for spec in episodes}),
            f"configured episode specifications are not unique for {study}",
        )
        expected_order.extend((study, spec["episode_id"]) for spec in episodes)
        for spec in episodes:
            task_keys.add((spec["task"], spec["seed"]))
    require(
        [(row["study"], row["episode_id"]) for row in rows] == expected_order,
        "episodes are not in deterministic configuration order",
    )

    for task, seed in sorted(task_keys):
        world = BenchmarkEnv(seed, task)
        payload = {
            "task": task,
            "parents": world.parents,
            "initial_cache": world.cache,
            "risk": world.risk,
            "truth_epoch0": world.truth.copy(),
        }
        world.mutate(1)
        payload["truth_epoch1"] = world.truth.copy()
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        require(
            digest not in fingerprints,
            f"seeded worlds collide: {(task, seed)} and {fingerprints.get(digest)}",
        )
        fingerprints[digest] = (task, seed)

    return {
        "episodes": len(rows),
        "experiments": {
            experiment["experiment_id"]: sum(
                experiments[row["condition_group"]]["experiment_id"]
                == experiment["experiment_id"]
                for row in rows
            )
            for experiment in experiment_overview(catalog)
        },
        "studies": dict(sorted(EXPECTED_COUNTS.items())),
        "models": sorted(EXPECTED_MODELS),
        "unique_tasks": len(task_keys),
        "duplicate_worlds": 0,
    }
