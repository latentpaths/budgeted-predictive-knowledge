import hashlib
import json
from pathlib import Path

import pytest

from budgeted_predictive_knowledge.analysis import model_statistics, paired_contrasts
from budgeted_predictive_knowledge.experiments import (
    EPISODES_PATH,
    STUDIES_PATH,
    load_episode_results,
    load_studies,
)
from budgeted_predictive_knowledge.metrics import GROUP_KEYS, paired, summarize
from budgeted_predictive_knowledge.validation import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evidence():
    return load_episode_results(ROOT / EPISODES_PATH)


def test_retained_results_checksum_and_matrix():
    assert hashlib.sha256((ROOT / EPISODES_PATH).read_bytes()).hexdigest() == (
        "1d11634d0b5668e08e71284420a6e2fccda8412e92d3050b6c9fc78bd6c2a621"
    )
    result = validate(ROOT)
    assert result["episodes"] == 1872
    assert result["duplicate_worlds"] == 0


def test_summaries_match_authoritative_numerics(evidence):
    reference = json.loads(
        (ROOT / "tests/fixtures/numerical_reference.json").read_text()
    )
    groups, summaries = summarize(evidence)
    for expected in reference["conditions"]:
        key = tuple(expected[name] for name in GROUP_KEYS)
        assert summaries[key] == expected
    assert len(summaries) == len(reference["conditions"])

    def identity(contrast):
        return tuple(contrast[k] for k in GROUP_KEYS[:4]) + (
            contrast["target"],
            contrast["target_budget_fraction"],
            contrast["baseline"],
            contrast["baseline_budget_fraction"],
        )

    assert {identity(c): c for c in paired_contrasts(groups)} == {
        identity(c): c for c in reference["contrasts"]
    }
    catalog = load_studies(ROOT / STUDIES_PATH)
    assert model_statistics(evidence, catalog["prices"]) == reference["models"]


def test_unpaired_seeds_fail(evidence):
    groups, _ = summarize(evidence)
    key = (
        "primary_budget_sweep",
        "qwen/qwen3-30b-a3b-instruct-2507",
        "dag",
        0.0,
        "risk_dependency",
        0.2,
    )
    groups[key] = groups[key][1:]
    with pytest.raises(ValueError, match="unpaired"):
        paired(
            groups, "primary_budget_sweep", key[1], "dag", "risk_dependency", "random"
        )
    with pytest.raises(ValueError, match="unpaired"):
        paired_contrasts(groups)


def test_duplicate_seeds_fail(evidence):
    groups, _ = summarize(evidence)
    key = (
        "primary_budget_sweep",
        "qwen/qwen3-30b-a3b-instruct-2507",
        "dag",
        0.0,
        "risk_dependency",
        0.2,
    )
    groups[key].append(groups[key][0])
    with pytest.raises(ValueError, match="duplicate"):
        paired(
            groups, "primary_budget_sweep", key[1], "dag", "risk_dependency", "random"
        )
    with pytest.raises(ValueError, match="duplicate"):
        paired_contrasts(groups)
