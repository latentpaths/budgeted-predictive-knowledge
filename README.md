# Which Predictions Are Worth Updating?

**Budgeted Predictive Knowledge for Long-Horizon Agents**  
Ayush Bodade · Independent Researcher · [ayush@latentpaths.com](mailto:ayush@latentpaths.com)

**Accepted as a poster at the [Neuro-Symbolic Embodied Intelligence (NEmo) workshop](https://nemo.semantic.review/), NeurIPS 2026.**

December 12, 2026 · Sydney, Australia

[Paper (PDF)](paper.pdf) · [Project website](https://latentpaths.com/projects/budgeted-predictive-knowledge) · [Workshop paper list](https://nemo.semantic.review/#accepted-papers) · [OpenReview paper](https://openreview.net/forum?id=gcFFvKU0DS) · [BibTeX](CITATION.bib)

When an agent's stored predictions become stale, which ones should receive fresh
evidence first? This repository studies how to allocate a fixed update budget
before an LLM policy continues acting. It contains the environments, update
selectors, inference runner, and **1,872 retained episode measurements** across
two task families and four LLM policies. No model weights change.

## Main findings

Each synthetic episode has 24 jobs and 24 stored predictions of hidden,
versioned access tokens. A selector chooses which predictions receive fresh
evidence; an LLM updater revises those records, and a fixed LLM policy attempts
the remaining jobs. The budget counts selected records, rather than tokens or
inference cost.

At a budget of **four records per update step**, combining supplied change risk
with downstream dependency importance (RD) improves progress over random
selection on the primary policy, Qwen3-30B-A3B-Instruct-2507:

| Task | Random: jobs completed | RD: jobs completed | Paired gain, percentage points (95% CI) |
| --- | ---: | ---: | ---: |
| DAG | 46.0% | 56.9% | +10.9 [+1.9, +20.3] |
| Precedence Chains | 54.7% | 62.3% | +7.6 [+0.2, +15.1] |

Each comparison uses 24 paired world seeds. Progress is the fraction of the 24
jobs completed. Full-episode successes remain 0/24 on DAG and 1/24 on Precedence
Chains for both selectors. All six corresponding RD-versus-random intervals
across the three additional policies include zero.

In the feedback follow-up, weighting estimated staleness by remaining dependency
demand (FRD) improves GPT-4.1-mini progress over feedback risk alone (FR) by
12.2 percentage points on DAG (95% CI [+4.5, +20.1]) and 14.6 on Precedence
Chains ([+6.9, +21.5]). The additional benefit of selecting records jointly over
FRD remains unresolved: both paired intervals include zero.

These results concern synthetic workflows with supplied dependency graphs and
change risks. They support better intermediate progress in the stated comparisons;
they do not establish reliable task completion, lower inference cost, physical
embodiment, or learned dependencies. The [paper](paper.pdf) reports the full
comparisons and uncertainty; the [experiment guide](experiments/README.md)
defines the protocol and analysis.

## Quick start: reproduce the reported results

Use Python 3.12 and [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/stochi0/budgeted-predictive-knowledge.git
cd budgeted-predictive-knowledge
uv sync --locked
uv run --locked bpk validate
uv run --locked bpk reproduce
```

After installation, validation and reproduction run offline. They require no API
key or LaTeX installation and make no inference calls. Validation checks retained
inputs; reproduction recomputes statistics and figures from the recorded episodes.

Results are written to the ignored `output/analysis/` directory:

| Output | Contents |
| --- | --- |
| `condition_summary.csv` | Condition means, intervals, successes, sample counts, usage, and errors |
| `paired_comparisons.csv` | Paired target-minus-baseline progress differences and intervals |
| `model_summary.csv` | Model totals, updater accuracy, and historical cost estimates |
| `validation.json` | Input checksums, totals, exclusions, and uncertainty definitions |
| `figures/*.pdf` | Budget, missing-dependency, cross-model, and feedback comparisons |

Both commands accept `--data` and `--config`; `reproduce` also accepts `--output`.
Run `uv run --locked bpk --help` for the command overview.

## Four experimental questions

The experiments follow the decision an agent faces: allocate limited updates,
check how much that decision depends on the supplied graph, compare policies,
and then use execution feedback to reconsider the allocation.

| Experiment | Question | Retained episodes |
| --- | --- | ---: |
| Budget allocation | Which records should receive updates at each budget? | 816 |
| Missing dependencies | How does incomplete dependency information affect selection? | 96 |
| Cross-model comparison | Do the selection gains hold across other policies? | 720 |
| Feedback and joint selection | Does execution feedback help, and does selecting updates jointly add value? | 240 |

Cross-model comparisons also reference the Qwen3-30B results from Budget
allocation at four records per update step. Those episodes are counted only in
Budget allocation; the four rows sum to **1,872**.

Browse the questions, models, episode counts, and budgets offline:

```sh
uv run --locked bpk experiments
uv run --locked bpk experiments --json
```

The [experiment guide](experiments/README.md#four-experimental-questions) explains
each controlled comparison and its interpretation. The shared catalog in
[the configuration](experiments/studies.json) supplies the experiment names used
by the CLI and analysis exports. Both condition and paired-comparison CSVs include
`experiment_id` and `experiment_name` alongside their existing identity fields.

## Fresh runs

Run batches retain their historical identifiers so saved runs can resume. See
[the run reference](experiments/README.md#run-reference) for their mapping to the
four questions. Inspect the feedback experiment without making requests or
creating run files:

```sh
uv run --locked bpk run --study feedback --dry-run
```

Fresh experiments consume inference credits through
[Prime Intellect](https://www.primeintellect.ai/). Install the optional inference
dependencies and set `PRIME_API_KEY` in your shell or a local `.env` file using
[`.env.example`](.env.example):

```sh
uv sync --locked --extra inference
uv run --locked bpk run --study feedback
```

Runs write measurements and request/response logs to `output/runs/<study>/`.
Repeat the command to resume; use `--output` for a separate run. Changed settings
require a new directory. Provider changes can make new runs differ from retained
results, even at temperature zero. Historical raw requests and responses are not
included in the public evidence; the retained episode measurements support
numerical reproduction.

## Repository guide

| Location | Contents |
| --- | --- |
| [paper.pdf](paper.pdf) | Current manuscript, including appendices |
| [paper/](paper/) | Current LaTeX sources, generated assets, build tools, and manuscript checks |
| [SUBMISSION.md](SUBMISSION.md) | Submission artifacts, verification, and reviewer recommendations |
| [scripts/package_submission.py](scripts/package_submission.py) | Build and verify the submission archives |
| [experiments/README.md](experiments/README.md) | Full experiment and analysis protocol |
| [experiments/studies.json](experiments/studies.json) | Experiment catalog, run settings, seeds, and historical prices |
| [experiments/episode_results.jsonl](experiments/episode_results.jsonl) | Retained episode measurements |
| [src/budgeted_predictive_knowledge/](src/budgeted_predictive_knowledge/) | Environments, selection, feedback, inference, statistics, figures, and CLI |
| [tests/](tests/) | Behavioral checks and frozen statistical/protocol references |
| [LICENSE-MIT](LICENSE-MIT) · [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0) | MIT software license and CC BY 4.0 research-content terms |
| `output/` | Ignored local results and fresh runs |

## Submission package

The current manuscript sources are in [paper/](paper/). The
[submission guide](SUBMISSION.md) records the upload files, reviewer changes,
and verification steps. With Tectonic installed:

```sh
uv sync --project paper --locked --group dev
uv run --project paper python paper/build.py --refresh --publish
uv run --project paper python scripts/package_submission.py --verify
```

The package contains one current PDF, a standalone LaTeX source ZIP, a code-and-data
ZIP, and a checksum/verification manifest under `output/submission/`. Verification
compiles and tests fresh archive extractions. Packaging does not submit to OpenReview.

## Development

```sh
uv sync --locked --group dev
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
```

These checks run offline after dependency installation. Inference tests use a mocked provider.

## Citation

If you use this code or the retained measurements, cite the accompanying workshop
paper. Download [CITATION.bib](CITATION.bib) or use the machine-readable
[CITATION.cff](CITATION.cff).

```bibtex
@misc{bodade2026budgeted,
  author       = {Ayush Bodade},
  title        = {Which Predictions Are Worth Updating? Budgeted Predictive Knowledge for Long-Horizon Agents},
  year         = {2026},
  howpublished = {Neuro-Symbolic Embodied Intelligence (NEmo), NeurIPS 2026 Workshop},
  note         = {Accepted poster; non-archival workshop paper},
  url          = {https://latentpaths.com/projects/budgeted-predictive-knowledge}
}
```

## Acknowledgment, license, and contact

The author thanks Prime Intellect for providing inference credits used in this
study.

Code and software documentation are licensed under [MIT](LICENSE-MIT).
The paper, original figures, and original research results are licensed under
[CC BY 4.0](LICENSE-CC-BY-4.0). Third-party material retains its existing terms.
For research questions, contact
[ayush@latentpaths.com](mailto:ayush@latentpaths.com).
