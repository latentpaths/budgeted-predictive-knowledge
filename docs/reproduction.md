# Reproduction and experiment commands

Run commands from the repository root. Start with the [README](../README.md#reproduce-the-results)
for installation and offline reproduction.

## Inspect the experiments

```sh
uv run --locked bpk experiments
uv run --locked bpk experiments --json
```

The [experiment guide](../experiments/README.md) owns the task protocol, selection
rules, four experimental questions, retained episode counts, and statistical
interpretation. Its [run reference](../experiments/README.md#run-reference) maps the
historical batch IDs to those questions. The [shared catalog](../experiments/studies.json)
supplies the names used by the CLI and analysis exports; exported condition and
paired-comparison CSVs include `experiment_id` and `experiment_name` alongside
the recorded identity fields.

## Generated results

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

## Evidence and licenses

The release contains 1,872 retained episode measurements. Their SHA-256 is
`1d11634d0b5668e08e71284420a6e2fccda8412e92d3050b6c9fc78bd6c2a621`.
Model requests, task seeds, recorded measurements, episode IDs, statistical
procedures, and saved-run identities are preserved. Frozen numerical and protocol
references are regression checks, rather than older versions of the paper.
