import copy
import hashlib
import json
from pathlib import Path

import pytest

from budgeted_predictive_knowledge.experiments import (
    EPISODES_PATH,
    STUDIES_PATH,
    episode_specs,
    experiment_lookup,
    experiment_overview,
    load_episode_results,
    load_studies,
    merged_transport,
    plan_run,
)


def test_unique_episode_specs():
    config = {
        "condition_groups": [
            {
                "name": "a",
                "model": "test",
                "seed_start": 0,
                "seeds": 2,
                "tasks": ["dag", "precedence_chains"],
                "selectors": ["random"],
                "budget_fractions": [0.1, 0.2],
                "controls": ["no_updates", "all_records"],
            }
        ]
    }
    episodes = episode_specs(config)
    assert len(episodes) == len({j["episode_id"] for j in episodes}) == 16


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_partitions_evidence_without_counting_references_twice():
    catalog = load_studies(ROOT / STUDIES_PATH)
    overview = experiment_overview(catalog)
    expected = {
        "budget_allocation": 816,
        "missing_dependencies": 96,
        "cross_model_comparison": 720,
        "feedback_and_joint_selection": 240,
    }
    assert {e["experiment_id"]: e["episode_count"] for e in overview} == expected
    lookup = experiment_lookup(catalog)
    rows = load_episode_results(ROOT / EPISODES_PATH)
    assert {
        experiment: sum(
            lookup[row["condition_group"]]["experiment_id"] == experiment
            for row in rows
        )
        for experiment in expected
    } == expected
    cross_model = overview[2]
    assert cross_model["reference_experiment_ids"] == ["budget_allocation"]
    assert [m["episode_count"] for m in cross_model["models"]] == [144, 288, 288]
    assert overview[0]["models"][0]["record_budgets"] == [2, 4, 7]
    assert overview[0]["models"][0]["control_budgets"] == [0, 24]


@pytest.mark.parametrize("problem", ["missing", "duplicate", "unknown", "reference"])
def test_catalog_rejects_ambiguous_or_incomplete_mapping(problem):
    catalog = copy.deepcopy(load_studies(ROOT / STUDIES_PATH))
    experiments = catalog["experiment_catalog"]
    if problem == "missing":
        experiments.pop()
    elif problem == "duplicate":
        experiments[1]["condition_groups"].append("primary_budget_sweep")
    elif problem == "unknown":
        experiments[0]["condition_groups"].append("unknown")
    else:
        experiments[2]["reference_experiment_ids"] = ["unknown"]
    with pytest.raises(ValueError):
        experiment_lookup(catalog)


def test_presentation_catalog_does_not_change_saved_run_settings():
    current = load_studies(ROOT / STUDIES_PATH)
    current.pop("experiment_catalog")
    assert hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest() == (
        "63ed302f70e30ee9a6011de37957fb83d0224fa327bdac1c6dd95d4e473af368"
    )


def test_study_matrices_and_transport():
    catalog = load_studies(ROOT / STUDIES_PATH)
    assert {
        study: plan_run(study, catalog)["episode_count"] for study in catalog["studies"]
    } == {
        "primary_static": 912,
        "gpt_static": 144,
        "additional_static": 576,
        "feedback": 240,
    }
    assert (
        merged_transport(catalog, catalog["studies"]["feedback"])["rate_limit"][
            "max_attempts"
        ]
        == 1
    )
    assert (
        merged_transport(catalog, catalog["studies"]["primary_static"])["concurrency"]
        == 24
    )
    assert (
        catalog["diagnostics"]["excluded_transport_collection"]["logged_calls"] == 1101
    )
