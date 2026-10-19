"""Submission archives use current verified inputs and exclude private files."""

import importlib.util
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "package_submission", ROOT / "scripts/package_submission.py"
)
submission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(submission)


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "repository"
    # Public tests construct manuscript inputs instead of reading private sources.
    for name in (
        ".env.example",
        ".gitignore",
        ".python-version",
        "README.md",
        "LICENSE",
        "docs/LICENSE-CC-BY-4.0",
        "docs/submission.md",
        "docs/reproduction.md",
        "pyproject.toml",
        "uv.lock",
        "paper.pdf",
        "scripts/package_submission.py",
        "experiments/README.md",
        "experiments/studies.json",
        "experiments/episode_results.jsonl",
        "tests/fixtures/numerical_reference.json",
        "tests/fixtures/protocol_reference.json",
    ):
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    shutil.copytree(
        ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    for test in (ROOT / "tests").glob("test_*.py"):
        shutil.copy2(test, root / "tests" / test.name)
    for name in (
        "paper/README.md",
        "paper/main.tex",
        "paper/neurips_2026.sty",
        "paper/build.py",
        "paper/render.py",
        "paper/pyproject.toml",
        "paper/uv.lock",
        "paper/tests/test_build.py",
        "paper/tests/fixtures/latex_reference.json",
    ):
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("author input fixture\n")
    report = root / "paper/build/verification.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "main_pages": 4,
                "total_pages": 15,
                "sha256": submission.checksum(root / "paper.pdf"),
                "inputs_sha256": {
                    "paper/main.tex": submission.checksum(root / "paper/main.tex")
                },
                "evidence": {"episodes": 1872},
            }
        )
    )
    return root


def test_archives_are_reproducible_and_exclude_private_and_old_files(
    workspace, tmp_path
):
    for name in (".env", "paper/build/old.pdf", "output/previous.pdf", ".venv/secret"):
        path = workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("private placeholder")
    first, second = tmp_path / "first", tmp_path / "second"
    manifest = submission.package(workspace, first)
    submission.package(workspace, second)
    for name in ("paper-source.zip", "supplementary-code.zip"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        with ZipFile(first / name) as archive:
            assert any(member.endswith("LICENSE") for member in archive.namelist())
            assert any(
                member.endswith("docs/LICENSE-CC-BY-4.0")
                for member in archive.namelist()
            )
            if name == "paper-source.zip":
                citation = archive.read("paper-source/CITATION.md").decode()
                assert "@misc{bodade2026budgeted" in citation
            else:
                assert (
                    "budgeted-predictive-knowledge/src/budgeted_predictive_knowledge/cli.py"
                    in archive.namelist()
                )
            assert not any(
                part in {".env", ".venv", "build", "output", "previous.pdf"}
                for member in archive.namelist()
                for part in Path(member).parts
            )
    assert manifest["verification"]["archives_tested"] is False
    assert json.loads((first / "manifest.json").read_text()) == manifest


def test_changed_manuscript_input_cannot_be_packaged(workspace, tmp_path):
    source = workspace / "paper/main.tex"
    source.write_text(source.read_text() + "\n% changed after compilation\n")
    output = tmp_path / "submission"
    with pytest.raises(ValueError, match="inputs changed after verification"):
        submission.package(workspace, output)
    assert not output.exists()


def test_public_checkout_explains_author_packaging_requirement(tmp_path):
    output = tmp_path / "submission"
    with pytest.raises(ValueError, match="author-local paper/"):
        submission.package(tmp_path, output)
    assert not output.exists()
