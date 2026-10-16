# Camera-ready submission

**Which Predictions Are Worth Updating? Budgeted Predictive Knowledge for
Long-Horizon Agents** — Ayush Bodade, Independent Researcher,
ayush@latentpaths.com.

Accepted as a poster at the Neuro-Symbolic Embodied Intelligence workshop,
NeurIPS 2026. The [workshop instructions](https://nemo.semantic.review/#call)
specify the NeurIPS 2026 style with `sglblindworkshop`, four main pages for
short papers, and references and appendices outside that limit. The
[camera-ready deadline](https://nemo.semantic.review/#dates) is October 31, 2026.

This repository prepares the files for submission. It does not upload them to
OpenReview or modify the existing submission.

## Files to upload

Run the commands below to write one current set under `output/submission/`:

| File | Purpose |
| --- | --- |
| `paper.pdf` | Named camera-ready manuscript with four main pages |
| `paper-source.zip` | Standalone LaTeX source, venue style, tables, and figures |
| `supplementary-code.zip` | Current implementation, retained data, tests, manuscript tools, and locked dependencies |
| `manifest.json` | Artifact checksums, episode counts, manuscript input hashes, and archive verification status |

The root `paper.pdf` is the canonical manuscript. Build copies and the PDF in
the upload directory are generated from it. There are no separate old manuscripts
or alternate implementations in the repository.

## Prepare and verify

Install Python 3.12, uv, and Tectonic. From the repository root:

```sh
uv sync --locked --group dev
uv sync --project paper --locked --group dev
uv run --locked bpk validate
uv run --locked bpk reproduce
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
uv run --project paper python paper/build.py --refresh --publish
uv run --project paper pytest -c paper/pyproject.toml paper/tests -q
uv run --project paper ruff check paper/build.py paper/render.py paper/tests
uv run --project paper ruff format --check paper/build.py paper/render.py paper/tests
uv run --project paper python scripts/package_submission.py --verify
```

Inspect the compiled pages before uploading. The package command refuses a PDF
that differs from the verified build or whose manuscript inputs have changed.
With `--verify`, it extracts both archives into a temporary directory, compiles
the standalone source, reruns numerical reproduction and tests from the extracted
code, and checks that both produce matching manuscript page text. Python
dependency checks use the local uv cache in offline mode; initial installation
and uncached TeX resources can need network access. No inference requests are made.

`manifest.json` records `archives_tested: true` only after those checks pass.
The archives use an explicit file allowlist and exclude credentials, raw request
logs, virtual environments, caches, build products, and previous versions.

## Reviewer recommendations included

| Recommendation | Location in the current paper |
| --- | --- |
| Define DAG and Precedence Chains before using them in methods | Introduction; full protocol in Experiments |
| Make the experimental story easier to follow | Experiment overview table; four matching Results paragraphs and appendix sections |
| Report budgets 2, 4, and 7 and no/all-update controls for the primary policy | Appendix C, complete budget tables and budget curves |
| Point explicitly to missing-dependency results | Results paragraph; Appendix D |
| Point to all feedback conditions, including Random and full updating | Results paragraph; Appendix F |
| Separate related work and clarify the contribution | Related Work section distinguishes this formulation and evaluation from earlier allocation principles |
| Include the code repository in the paper | Direct Code and data link in the Introduction and reproducibility appendix |

The six selector names are defined in the shared method table and explained in
the worked example. The paper preserves the reviewers' evidence boundaries:
supplied risks and graphs, synthetic workflows, uncertain gains across policies,
uncertain Joint-versus-FRD gains, low complete-episode success, and no established
inference-cost advantage. The revision adds no experiments.

## Evidence and licenses

The release contains 1,872 retained episode measurements. Their SHA-256 is
`1d11634d0b5668e08e71284420a6e2fccda8412e92d3050b6c9fc78bd6c2a621`.
Model requests, task seeds, recorded measurements, episode IDs, statistical
procedures, and saved-run identities are preserved. Frozen numerical and protocol
references are regression checks, rather than older versions of the paper.

Code and software documentation use MIT; author-owned paper content, original
figures, and original results use CC BY 4.0. Third-party material, including the
retained venue style, keeps its existing terms. Both archives include the
applicable license and citation files.
