# Budgeted Predictive Knowledge

Which stored predictions should an agent refresh under a limited update budget?
Experiments compare selection rules with a fixed LLM policy and updater in synthetic
workflows. Some rules improve intermediate progress; reliable completion and
gains across policies remain unestablished.

[Paper on Zenodo](https://doi.org/10.5281/zenodo.24196448) · [Experiment reference](docs/reference.md)

## Reproduce

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/latentpaths/budgeted-predictive-knowledge.git
cd budgeted-predictive-knowledge
uv sync --locked
uv run --locked bpk validate
uv run --locked bpk reproduce
```

After installation, reproduction runs offline without credentials or LaTeX.
It checks 1,872 retained episodes and regenerates statistics and figures.
See the [reference](docs/reference.md) for results, protocols, output files and
fresh experiment commands. Fresh inference runs consume provider credits.

## Development

```sh
uv sync --locked --group dev
uv run --locked --group dev python -m pytest -q
uv run --locked --group dev ruff check src tests
uv run --locked --group dev ruff format --check src tests
```

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
  url = {https://doi.org/10.5281/zenodo.24196448},
  doi = {10.5281/zenodo.24196448},
  note = {Accepted poster; Non-archival workshop paper}
}
```

<!-- END generated citations -->

Prime Intellect provided inference credits. Code and software documentation use
[MIT](LICENSE#software-mit-license). The paper, original figures, and original research results use
[CC BY 4.0](LICENSE#research-material-creative-commons-attribution-40-international). Third-party material retains its existing terms.
Contact [Ayush Bodade](mailto:ayush@latentpaths.com).
