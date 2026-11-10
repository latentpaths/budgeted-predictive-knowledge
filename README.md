<p>
  <a href="https://www.latentpaths.com/"><img src="https://raw.githubusercontent.com/latentpaths/.github/main/assets/latent-paths-wordmark.png" alt="Latent Paths" width="280"></a>
</p>

# Which predictions are worth updating?

An agent has stale predictions and a limited budget for refreshing them. This
project tests which records to update before a fixed LLM policy continues acting.
Using supplied change risks and dependencies improves intermediate progress in
specific comparisons; full-episode success remains low and gains across other
policies are uncertain. No model weights change.

[Paper](paper.pdf) · [Experiments](experiments/README.md)

*Budgeted Predictive Knowledge for Long-Horizon Agents* — Ayush Bodade.
Accepted poster, NEmo workshop at NeurIPS 2026.

[Reproduce results](#reproduce-the-results) · [Run new experiments](#fresh-runs) ·
[Develop](#development) · [Prepare the paper submission](#prepare-the-paper-submission)

## Reproduce the results

With Python 3.12 and [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/latentpaths/budgeted-predictive-knowledge.git
cd budgeted-predictive-knowledge
uv sync --locked
uv run --locked bpk validate
uv run --locked bpk reproduce
```

After installation, both commands run offline without API keys or LaTeX.
They validate the **1,872 retained episode measurements** and recompute statistics
and figures in `output/analysis/`. They make no inference calls.

## What the experiments show

Each synthetic episode has 24 jobs and 24 stored predictions of hidden,
versioned access tokens. A selector allocates updates, an LLM updater revises the
selected records, and a fixed LLM policy attempts the remaining jobs. The budget
counts records selected at each update step.

At four records per step, risk × downstream dependency importance (RD) gives the
following progress against random selection for Qwen3-30B-A3B-Instruct-2507.
Each row uses 24 paired world seeds; progress is the fraction of 24 jobs completed.

| Task | Random | RD | Paired gain, percentage points (95% CI) |
| --- | ---: | ---: | ---: |
| DAG | 46.0% | 56.9% | +10.9 [+1.9, +20.3] |
| Precedence Chains | 54.7% | 62.3% | +7.6 [+0.2, +15.1] |

Full-episode successes are 0/24 on DAG and 1/24 on Precedence Chains for both
selectors. All six corresponding RD-versus-random intervals across three
additional policies include zero.

In a feedback follow-up with GPT-4.1-mini, weighting estimated staleness by
remaining dependency demand improves progress over feedback risk alone by
12.2 percentage points on DAG (95% CI [+4.5, +20.1]) and 14.6 on Precedence Chains
([+6.9, +21.5]). The additional benefit of selecting records jointly is unresolved.

These are synthetic workflows with supplied risks and graphs. The comparisons do
not establish reliable completion, learned dependencies, or reduced inference cost.
The [experiment guide](experiments/README.md) defines the four experimental
questions, protocols, retained records, and statistical interpretation.

## Inspect the experiments

```sh
uv run --locked bpk experiments
uv run --locked bpk experiments --json
```

The [experiment guide](experiments/README.md) owns the task protocol, selection
rules, four experimental questions, retained episode counts, and statistical
interpretation. Its [run reference](experiments/README.md#run-reference) maps the
historical batch IDs to those questions. The [shared catalog](experiments/studies.json)
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


## Development

```sh
uv sync --locked --group dev
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
```

These checks run offline after dependency installation. Inference tests use a mocked provider.

## Evidence and licenses

The release contains 1,872 retained episode measurements. Their SHA-256 is
`1d11634d0b5668e08e71284420a6e2fccda8412e92d3050b6c9fc78bd6c2a621`.
Model requests, task seeds, recorded measurements, episode IDs, statistical
procedures, and saved-run identities are preserved. Frozen numerical and protocol
references are regression checks, rather than older versions of the paper.

Code and software documentation use MIT; author-owned paper content, original
figures, and original results use CC BY 4.0. Third-party material, including the
retained venue style, keeps its existing terms. The applicable licenses are included in this repository.

## Citation

<!-- BEGIN generated citations -->

```bibtex
@inproceedings{bodadepaperbodade2026budgeted,
  author = {Bodade, Ayush},
  title = {{Which Predictions Are Worth Updating? Budgeted Predictive Knowledge for Long-Horizon Agents}},
  year = {2026},
  month = {09},
  day = {30},
  date = {2026-09-30},
  booktitle = {Neuro-Symbolic Embodied Intelligence (NEmo), NeurIPS 2026 workshop},
  url = {https://openreview.net/forum?id=gcFFvKU0DS},
  note = {Accepted poster; Non-archival workshop paper}
}
```

<!-- END generated citations -->

Prime Intellect provided inference credits. Code and software documentation use
[MIT](LICENSE#software-mit-license). The paper, original figures, and original research results use
[CC BY 4.0](LICENSE#research-material-creative-commons-attribution-40-international). Third-party material retains its existing terms.
Contact [Ayush Bodade](mailto:ayush@latentpaths.com).