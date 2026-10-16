import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def offline_command(*arguments, cwd=ROOT):
    # Block all socket connections and reject inference imports in the subprocess.
    script = """
import builtins, socket, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'openai', 'dotenv'}:
        raise AssertionError('offline command imported inference dependencies')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
def forbidden(*args, **kwargs):
    raise AssertionError('offline command attempted a network connection')
socket.socket.connect = forbidden
from budgeted_predictive_knowledge.cli import main
main(sys.argv[1:])
"""
    env = {key: value for key, value in os.environ.items() if key != "PRIME_API_KEY"}
    return subprocess.run(
        [sys.executable, "-c", script, *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_dry_run_is_offline_and_does_not_create_run_directory(tmp_path):
    output = tmp_path / "run"
    result = offline_command(
        "run", "--study", "feedback", "--dry-run", "--output", str(output)
    )
    plan = json.loads(result.stdout)
    assert plan["episode_count"] == len(plan["episodes"]) == 240
    assert plan["logical_call_upper_bound"] <= plan["logical_call_cap"]
    assert not output.exists()


def test_experiment_overview_is_offline_and_read_only(tmp_path):
    shutil.copytree(ROOT / "experiments", tmp_path / "experiments")
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    overview = json.loads(offline_command("experiments", "--json", cwd=tmp_path).stdout)
    text = offline_command("experiments", cwd=tmp_path).stdout
    assert sum(experiment["episode_count"] for experiment in overview) == 1872
    for experiment in overview:
        assert experiment["experiment_name"] in text
        assert experiment["question"] in text
        for model in experiment["models"]:
            assert model["model_name"] in text
    assert "gpt_static" not in text and "additional_static" not in text
    assert {p.relative_to(tmp_path) for p in tmp_path.rglob("*")} == before


def test_reproduce_without_credentials_network_or_inference_sdk(tmp_path):
    output = tmp_path / "results"
    result = offline_command("reproduce", "--output", str(output))
    assert json.loads(result.stdout)["validation"]["episodes"] == 1872
    with (output / "condition_summary.csv").open() as stream:
        assert len(list(csv.DictReader(stream))) > 34
    from budgeted_predictive_knowledge.experiments import (
        experiment_lookup,
        load_studies,
    )

    lookup = experiment_lookup(load_studies())
    reference = json.loads(
        (ROOT / "tests/fixtures/numerical_reference.json").read_text()
    )
    for filename, reference_key in (
        ("condition_summary.csv", "conditions"),
        ("paired_comparisons.csv", "contrasts"),
    ):
        with (output / filename).open() as stream:
            exported = list(csv.DictReader(stream))
        assert len(exported) == len(reference[reference_key])
        keys = ["condition_group", "model", "task", "missing_edge_fraction"]
        keys += (
            ["selector", "budget_fraction"]
            if reference_key == "conditions"
            else [
                "target",
                "target_budget_fraction",
                "baseline",
                "baseline_budget_fraction",
            ]
        )

        def identity(row, keys=keys):
            return tuple(
                float(row[key]) if key.endswith("_fraction") else row[key]
                for key in keys
            )

        expected_rows = {identity(row): row for row in reference[reference_key]}
        for row in exported:
            expected = expected_rows[identity(row)]
            labels = lookup[row["condition_group"]]
            assert all(row[key] == value for key, value in labels.items())
            for key, value in expected.items():
                if key.endswith("_ci"):
                    assert float(row[f"{key}_low"]) == value[0]
                    assert float(row[f"{key}_high"]) == value[1]
                elif isinstance(value, (int, float)):
                    assert float(row[key]) == value
                else:
                    assert row[key] == value
    report = json.loads((output / "validation.json").read_text())
    assert {key: value["episodes"] for key, value in report["experiments"].items()} == {
        "budget_allocation": 816,
        "missing_dependencies": 96,
        "cross_model_comparison": 720,
        "feedback_and_joint_selection": 240,
    }
    assert len(list((output / "figures").glob("*.pdf"))) == 4
    assert {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()} == {
        "condition_summary.csv",
        "paired_comparisons.csv",
        "model_summary.csv",
        "validation.json",
        "figures/update_budgets.pdf",
        "figures/missing_dependencies.pdf",
        "figures/cross_model_comparisons.pdf",
        "figures/feedback_comparisons.pdf",
    }


def test_validate_is_offline():
    assert json.loads(offline_command("validate").stdout)["episodes"] == 1872


def test_reproduce_uses_default_input_and_output_paths(tmp_path):
    shutil.copytree(ROOT / "experiments", tmp_path / "experiments")
    offline_command("reproduce", cwd=tmp_path)
    output = tmp_path / "output/analysis"
    assert (output / "validation.json").is_file()
    assert len(list(output.glob("*.csv"))) == 3


def test_default_dry_run_creates_no_output_directory(tmp_path):
    shutil.copytree(ROOT / "experiments", tmp_path / "experiments")
    offline_command("run", "--study", "feedback", "--dry-run", cwd=tmp_path)
    assert not (tmp_path / "output").exists()


def test_removed_analyze_command_is_rejected():
    result = subprocess.run(
        [sys.executable, "-m", "budgeted_predictive_knowledge.cli", "analyze"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
