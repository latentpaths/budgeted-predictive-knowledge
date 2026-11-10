# Which predictions are worth updating?

An agent has stale predictions and a limited budget for refreshing them. This
project tests which records to update before a fixed LLM policy continues acting.
Using supplied change risks and dependencies improves intermediate progress in
specific comparisons; full-episode success remains low and gains across other
policies are uncertain. No model weights change.

[Paper](paper.pdf) · [Protocol and evidence](experiments/README.md) · [Command reference](docs/reproduction.md)

*Budgeted Predictive Knowledge for Long-Horizon Agents* — Ayush Bodade.
Accepted poster, NEmo workshop at NeurIPS 2026.

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

## Development

```sh
uv sync --locked --group dev
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
```

These checks run offline after dependency installation. Inference tests use a mocked provider.

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
