# Reproduction and fresh runs

Run commands from the repository root. The public checkout contains the data and
code needed for numerical reproduction; manuscript sources are author-local.

## Quick start: reproduce the reported results

Use Python 3.12 and [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/latentpaths/budgeted-predictive-knowledge.git
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

The [experiment guide](../experiments/README.md#four-experimental-questions) explains
each controlled comparison and its interpretation. The shared catalog in
[the configuration](../experiments/studies.json) supplies the experiment names used
by the CLI and analysis exports. Both condition and paired-comparison CSVs include
`experiment_id` and `experiment_name` alongside their existing identity fields.

## Fresh runs

Run batches retain their historical identifiers so saved runs can resume. See
[the run reference](../experiments/README.md#run-reference) for their mapping to the
four questions. Inspect the feedback experiment without making requests or
creating run files:

```sh
uv run --locked bpk run --study feedback --dry-run
```

Fresh experiments consume inference credits through
[Prime Intellect](https://www.primeintellect.ai/). Install the optional inference
dependencies and set `PRIME_API_KEY` in your shell or a local `.env` file using
[`.env.example`](../.env.example):

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


## Development

```sh
uv sync --locked --group dev
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
```

These checks run offline after dependency installation. Inference tests use a mocked provider.
