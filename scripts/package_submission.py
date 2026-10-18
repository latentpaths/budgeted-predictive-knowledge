"""Package a verified manuscript using author-local sources under paper/."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/latentpaths/budgeted-predictive-knowledge"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_files(root: Path) -> list[Path]:
    """An allowlist excludes credentials, run logs, caches, and historical copies."""
    names = (
        ".env.example",
        ".gitignore",
        ".python-version",
        "README.md",
        "docs/submission.md",
        "docs/reproduction.md",
        "LICENSE",
        "docs/LICENSE-CC-BY-4.0",
        "pyproject.toml",
        "uv.lock",
        "paper.pdf",
        "scripts/package_submission.py",
        "experiments/README.md",
        "experiments/studies.json",
        "experiments/episode_results.jsonl",
        "tests/fixtures/numerical_reference.json",
        "tests/fixtures/protocol_reference.json",
        "paper/README.md",
        "paper/main.tex",
        "paper/neurips_2026.sty",
        "paper/build.py",
        "paper/render.py",
        "paper/pyproject.toml",
        "paper/uv.lock",
        "paper/tests/test_build.py",
        "paper/tests/fixtures/latex_reference.json",
    )
    files = [root / name for name in names]
    for pattern in (
        "src/budgeted_predictive_knowledge/*.py",
        "tests/test_*.py",
        "paper/generated/*.tex",
        "paper/generated/*.pdf",
    ):
        files.extend(root.glob(pattern))
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(
                f"Required regular file is missing: {path.relative_to(root)}"
            )
    return sorted(set(files))


def write_archive(path: Path, entries: dict[str, bytes]) -> None:
    """Stable member order and timestamps make identical inputs reproducible."""
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(entries.items()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)


def package(root: Path, output: Path) -> dict:
    report_path = root / "paper/build/verification.json"
    if not report_path.is_file():
        raise ValueError(
            "Submission packaging requires author-local paper/ sources and a verified "
            "build; see docs/submission.md. Use bpk reproduce for public results."
        )
    report = json.loads(report_path.read_text())
    if report["main_pages"] != 4 or report["sha256"] != checksum(root / "paper.pdf"):
        raise ValueError(
            "Build and publish the current four-page manuscript before packaging"
        )
    if not report.get("inputs_sha256"):
        raise ValueError("Rebuild the manuscript to record its input checksums")
    for name, expected in report["inputs_sha256"].items():
        if checksum(root / name) != expected:
            raise ValueError(f"Manuscript inputs changed after verification: {name}")
    files = repository_files(root)
    output = output.resolve()
    if (
        output == root
        or output in {path.parent for path in files}
        or any(output in path.parents for path in files)
    ):
        raise ValueError("Use a separate output directory, such as output/submission")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "paper.pdf", output / "paper.pdf")
    source = {
        "paper-source/" + str(path.relative_to(root / "paper")): path.read_bytes()
        for path in [root / "paper/main.tex", root / "paper/neurips_2026.sty"]
        + sorted((root / "paper/generated").glob("*.tex"))
        + sorted((root / "paper/generated").glob("*.pdf"))
    }
    for name in ("LICENSE", "docs/LICENSE-CC-BY-4.0"):
        source[f"paper-source/{name}"] = (root / name).read_bytes()
    source["paper-source/README.md"] = (
        b"# Manuscript source\n\n"
        b"Compile from this directory with `tectonic main.tex`. Generated tables and "
        b"figures are included; Python and inference credentials are not required.\n\n"
        b"Author-owned manuscript content uses CC BY 4.0. The retained NeurIPS "
        b"style keeps its existing terms. See LICENSE and docs/LICENSE-CC-BY-4.0.\n\n"
        b"Citation is in CITATION.md.\n"
    )
    _, opening, citation = (root / "README.md").read_text().partition("```bibtex\n")
    bibtex, closing, _ = citation.partition("\n```")
    if not opening or not closing:
        raise ValueError("README.md must contain the paper's BibTeX citation")
    source["paper-source/CITATION.md"] = (
        "# Citation\n\n```bibtex\n" + bibtex + "\n```\n"
    ).encode()
    source["paper-source/docs/LICENSE-CC-BY-4.0"] = source[
        "paper-source/docs/LICENSE-CC-BY-4.0"
    ].replace(b"../README.md#citation", b"../CITATION.md")
    write_archive(output / "paper-source.zip", source)
    write_archive(
        output / "supplementary-code.zip",
        {
            "budgeted-predictive-knowledge/"
            + str(path.relative_to(root)): path.read_bytes()
            for path in files
        },
    )
    manifest = {
        "title": "Which Predictions Are Worth Updating? Budgeted Predictive Knowledge for Long-Horizon Agents",
        "repository": REPOSITORY,
        "status": "prepared; not submitted",
        "main_pages": report["main_pages"],
        "total_pages": report["total_pages"],
        "evidence": report["evidence"],
        "evidence_sha256": checksum(root / "experiments/episode_results.jsonl"),
        "artifacts": {
            name: {
                "sha256": checksum(output / name),
                "bytes": (output / name).stat().st_size,
            }
            for name in ("paper.pdf", "paper-source.zip", "supplementary-code.zip")
        },
        "source_files_sha256": {
            str(path.relative_to(root)): checksum(path) for path in files
        },
        "verification": {"archives_tested": False},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify_packages(root: Path, output: Path, manifest: dict) -> None:
    """Test extracted archives; never substitute the author's checkout for them."""
    from pypdf import PdfReader

    def page_text(path):
        return [page.extract_text() for page in PdfReader(path).pages]

    def run(command, cwd):
        subprocess.run(
            command,
            cwd=cwd,
            check=True,
            env={**os.environ, "SOURCE_DATE_EPOCH": "1767225600"},
        )

    expected = page_text(output / "paper.pdf")
    with TemporaryDirectory(prefix="bpk-submission-") as temporary:
        stage = Path(temporary)
        for name in ("paper-source.zip", "supplementary-code.zip"):
            with ZipFile(output / name) as archive:
                if archive.testzip() is not None:
                    raise ValueError(f"Corrupt archive: {name}")
                archive.extractall(stage)
        source = stage / "paper-source"
        run(["tectonic", "--keep-logs", "main.tex"], source)
        if page_text(source / "main.pdf") != expected:
            raise ValueError(
                "Standalone manuscript source does not reproduce the PDF text"
            )
        code = stage / "budgeted-predictive-knowledge"
        run(["uv", "sync", "--locked", "--offline", "--group", "dev"], code)
        for arguments in (
            ["bpk", "validate"],
            ["bpk", "experiments", "--json"],
            ["bpk", "reproduce"],
            ["pytest", "-q"],
            ["ruff", "check", "src", "tests", "scripts"],
            ["ruff", "format", "--check", "src", "tests", "scripts"],
        ):
            run(["uv", "run", "--locked", "--offline", *arguments], code)
        run(
            [
                "uv",
                "sync",
                "--project",
                "paper",
                "--locked",
                "--offline",
                "--group",
                "dev",
            ],
            code,
        )
        for arguments in (
            ["python", "paper/build.py", "--refresh"],
            ["pytest", "-c", "paper/pyproject.toml", "paper/tests", "-q"],
            ["ruff", "check", "paper/build.py", "paper/render.py", "paper/tests"],
            [
                "ruff",
                "format",
                "--check",
                "paper/build.py",
                "paper/render.py",
                "paper/tests",
            ],
        ):
            run(
                [
                    "uv",
                    "run",
                    "--project",
                    "paper",
                    "--locked",
                    "--offline",
                    *arguments,
                ],
                code,
            )
        if page_text(code / "paper/build/main.pdf") != expected:
            raise ValueError(
                "Extracted code and data do not reproduce the manuscript text"
            )
        actual = json.loads((code / "output/analysis/validation.json").read_text())
        if actual["evidence_sha256"] != manifest["evidence_sha256"]:
            raise ValueError(
                "Extracted evidence checksum differs from the submitted evidence"
            )
    manifest["verification"] = {
        "archives_tested": True,
        "standalone_source_pdf_text_matches": True,
        "extracted_code_reproduces_pdf_text": True,
        "offline_reproduction_and_tests_passed": True,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output/submission")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Compile and test fresh archive extractions",
    )
    args = parser.parse_args()
    try:
        manifest = package(ROOT, args.output)
        if args.verify:
            verify_packages(ROOT, args.output, manifest)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Submission packaging failed: {exc}\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "artifacts": manifest["artifacts"],
                "verification": manifest["verification"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
