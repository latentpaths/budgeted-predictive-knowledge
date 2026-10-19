# Experiments

The experiment asks which stored predictions should receive fresh evidence
before a fixed LLM policy continues acting. The allocation constraint counts
records, not inference tokens. No model weights change.

## Tasks and policy protocol

An episode has 24 jobs and 24 hidden versioned access tokens. The policy sees
job requirements, stored token predictions, completed jobs, remaining actions,
and execution feedback. It cannot inspect current hidden values. Only selected
records receive observed configurations and validated one-step continuations as
updater inputs.

- `dag`: jobs require their own token and direct dependency tokens. Jobs have
  no completion-order constraint.
- `precedence_chains`: four six-job chains additionally require predecessor
  jobs to finish. A completed predecessor's token can still be needed later.

There are eight rounds of up to four actions. State-change events occur before
rounds one and five, each followed by record selection and an updater call unless
no records are selected. Completed jobs stay complete. Missing or malformed
actions consume their slots. Rejection can identify stale submitted states but
cannot reveal their correct values.

Change risks are sampled independently of graph position. Selectors share paired
worlds within a study and cannot use realized hidden changes to rank updates.
Missing dependency edges affect the selector's graph only; policy job
specifications remain complete.

The task identifiers above describe the two workflows. The frozen model-facing protocol
retains its original `domain` field and `repair` value for Precedence Chains,
along with the original prompts, action keys, and certificate keys. This preserves
what the models see when rerunning the study.

## Selectors

| Identifier | Paper label | Allocation rule |
| --- | --- | --- |
| `random` | Random | Seeded random records |
| `even_spacing` | Even spacing | Evenly spaced records |
| `change_risk` | R | Supplied change risk |
| `dependency_importance` | D | Discounted downstream dependency importance |
| `risk_dependency` | RD | Change risk × dependency importance |
| `feedback_risk` | FR | Estimated invalidity using changes and execution feedback |
| `feedback_risk_dependency` | FRD | Estimated invalidity × remaining requirement demand |
| `joint` | Joint | Exhaustive set selection using expected requirement validity |
| `no_updates` | No updates | Zero records |
| `all_records` | All records | All 24 records |

The record budget is `int(24 * budget_fraction)`: fractions 0.1, 0.2, and 0.3
select 2, 4, and 7 records per update step. Static dependency importance counts
each reachable job once at its shortest discounted distance. Feedback estimates
track the current cache, including incorrect updater outputs. Joint treats
objective differences within 1e-12 as ties and breaks ties using the paired seed.

## Four experimental questions

The catalog groups conditions by the question they answer. Models, task families,
and selectors remain separate attributes. All comparisons measure job progress,
full-episode success, and policy-plus-updater token usage under the shared protocol.

| Experiment ID | Experiment | Episodes |
| --- | --- | ---: |
| `budget_allocation` | Budget allocation | 816 |
| `missing_dependencies` | Missing dependencies | 96 |
| `cross_model_comparison` | Cross-model comparison | 720 |
| `feedback_and_joint_selection` | Feedback and joint selection | 240 |

### Budget allocation

**Which records should receive updates at each budget?** Qwen3-30B-A3B-Instruct-2507
compares Random, Even spacing, R, D, and RD at 2, 4, and 7 records per update step,
with no-update and all-record controls. Each condition uses 24 paired seeds per
task (1000–1023). This isolates the selection rule at equal budgets; controls
show the outcomes at zero and unrestricted record updates.

At four records, RD improves progress over Random by 10.9 percentage points on
DAG (95% CI [+1.9, +20.3]) and 7.6 on Precedence Chains ([+0.2, +15.1]). Episode
success remains 0/24 and 1/24 for both selectors. Higher intermediate progress
does not establish reliable completion.

### Missing dependencies

**How does incomplete dependency information affect selection?** Qwen3-30B tests
D and RD at four records with 30% or 60% of the selector's graph edges removed.
The 96 episodes use 12 paired seeds per task (1000–1011). The complete-graph
reference is recomputed from Budget allocation on those same 12 seeds.

The policy still receives complete job requirements. Compare progress curves
against that paired reference to assess sensitivity to missing structural
information. This tests withheld edges, rather than a learned graph extractor.
Reference episodes remain counted in Budget allocation.

### Cross-model comparison

**Do the selection gains hold across other policies?** GPT-4.1-mini, GLM-5.3-Flash,
and Qwen3.6-35B-A3B compare Random, R, D, and RD at four records, with no-update
and all-record controls. GPT uses 12 paired seeds per task (2000–2011), contributing
144 episodes; GLM and Qwen3.6 each use 24 (4000–4023), contributing 288 each.
The Qwen3-30B results at the same budget provide a reference from Budget allocation.

All six RD-versus-Random intervals for these three policies include zero. The
positive Qwen3-30B comparisons therefore do not establish a gain across policies.
Selectors are paired within each model; model comparisons also differ in seeds
and request settings and are not paired model effects. The 720 episodes here
exclude the reused Qwen3-30B reference.

### Feedback and joint selection

**Does execution feedback help, and does selecting updates jointly add value?**
At four records, GPT-4.1-mini compares Random, RD, FR, FRD, Joint, and all-record
updating; Qwen3.6-35B-A3B compares RD, FR, Joint, and all-record updating. Each
uses 12 fresh paired seeds per task (5000–5011), totaling 144 and 96 episodes.
FRD versus FR tests weighting estimated staleness by remaining dependency demand;
Joint versus FRD tests the additional value of selecting sets together on GPT.

GPT's FRD improves progress over FR by 12.2 percentage points on DAG (95% CI
[+4.5, +20.1]) and 14.6 on Precedence Chains ([+6.9, +21.5]). Both Joint-versus-FRD
intervals include zero. Joint versus RD changes both feedback use and the
selection objective, so that contrast alone cannot isolate the benefit of joint
selection. FRD was not tested on Qwen3.6.

## Inputs and catalog

- `studies.json` contains `experiment_catalog`, the shared question-based names
  and condition-group mapping, alongside the original run matrices, request
  settings, transport limits, historical prices, and exclusion diagnostics.
- `episode_results.jsonl` contains the 1,872 retained measurements, in historical
  run and condition-generation order. Each line is one episode. Fresh runs never
  write to this input file.

The catalog assigns every condition group to exactly one experiment. References
to other experiments do not add episodes. `bpk experiments` shows questions,
models, counts, and record budgets; `bpk experiments --json` also includes the
condition-group mapping and reference experiments. Counts and budgets are derived
from the run configuration.

Configuration version 2 retains `studies` containing `condition_groups`. Each
group specifies its model, seed range, `tasks`, `selectors`, `budget_fractions`,
optional `controls`, and optional `missing_edge_fractions`. Study-specific
transport settings override shared settings; rate-limit options merge separately.
Presentation metadata does not enter run manifests or episode identities.

The interrupted collection is recorded separately under `diagnostics`. Its
usage and costs are excluded from retained-sample totals. No retained outcome
was removed because of its performance.

## Run reference

These historical identifiers select collection batches with `bpk run --study`.
They remain stable for saved manifests, episode IDs, and output directories;
use the question-based experiment names when discussing the results.

| Run identifier | Condition groups | Experiment |
| --- | --- | --- |
| `primary_static` | `primary_budget_sweep`; `missing_dependencies` | Budget allocation (816); Missing dependencies (96) |
| `gpt_static` | `gpt_static` | Cross-model comparison: GPT-4.1-mini (144) |
| `additional_static` | `glm_static`; `qwen_static` | Cross-model comparison: GLM-5.3-Flash (288); Qwen3.6-35B-A3B (288) |
| `feedback` | `gpt_feedback`; `qwen_feedback` | Feedback and joint selection: GPT-4.1-mini (144); Qwen3.6-35B-A3B (96) |

```sh
uv run --locked bpk run --study feedback --dry-run
```

Omit `--dry-run` to make inference requests after installing the inference extra
and setting `PRIME_API_KEY`. Runs write to `output/runs/<study>/` by default.
Repeat the same command to resume; changed settings require a separate directory.

## Episode schema

| Fields | Meaning |
| --- | --- |
| `study`, `condition_group`, `model` | Historical run batch, condition group, and requested API model |
| `task`, `seed` | Task family and paired world seed |
| `selector`, `budget_fraction`, `missing_edge_fraction` | Update allocation and withheld-edge condition |
| `episode_id` | First 20 hexadecimal characters of SHA-256 over the sorted JSON identity fields: condition group, model, seed, task, selector, budget fraction, and missing-edge fraction |
| `completed`, `completion`, `success` | Completed jobs, completed/24, and whether all 24 jobs completed |
| `attempts`, `invalid_actions`, `stale_errors` | Action slots spent, malformed/invalid actions, and stale-prediction rejections |
| `selected`, `updates`, `valid_updates`, `correct_updates` | Selected record IDs by update step, total selections across steps, parsed updates, and correct new predictions |
| `round_completion`, `feedback` | Completed-job counts after each round and execution replies |
| `calls`, `update_calls`, `api_errors`, `missing_usage` | Logical inference calls, updater calls, API failures, and calls lacking usage reports |
| `prompt_tokens`, `completion_tokens`, `latency_seconds` | Reported input/output tokens and summed call latency |
| `belief_history`, `selection_seconds` | Feedback-study validity estimates before each selection and total selector time across update steps |

The question-based catalog leaves this recorded schema, all measurements, nested
traces, and episode IDs unchanged. Reports add `experiment_id` and
`experiment_name` by looking up the condition group; these labels are not added
to the retained episodes or used to calculate their IDs.

Fresh runs use the same schema and write `episode_results.jsonl`, `manifest.json`,
and private `calls.jsonl` files inside their run directory. The manifest fixes the
study, request settings, and transport configuration. Resume skips completed IDs
and reuses logged responses for matching complete request payloads. Private call
logs include request/response content and provider IDs; retained public data do
not include those historical logs.

## Analysis and interpretation

The condition and paired-comparison CSVs include `experiment_id` and
`experiment_name`; `validation.json` reports totals under `experiments` and
retains the historical `studies` totals. Reference results are counted once.

Condition summaries group by condition group, model, task, missing-edge fraction,
selector, and budget fraction. Episodes receive equal weight; different budgets
are never pooled. Selector time is mean seconds per update step, excluding
inference. Updater accuracy divides correct new predictions by selected records,
including missing or malformed updates in the denominator.

Completion intervals use 10,000 bootstrap resamples with NumPy seed 20260912.
Success intervals use Wilson's formula at 95%. Paired comparisons resample
within-condition target-minus-baseline completion differences on identical seeds.
Unequal or duplicate paired seeds fail validation. Intervals are not adjusted
for multiple comparisons.

Budgeted selectors are compared at equal budgets; no-update and all-record
controls retain their own budgets. Positive differences favor the named target.
Completion fractions use [0, 1]; columns ending in `_pp` use percentage points.
Reversing a comparison reverses its mean and interval endpoints.

Prices are historical USD per million tokens. Estimated costs sum reported
input/output usage before cache discounts and exclude unreported usage and the
excluded collection. They are not a measurement of out-of-pocket expense.
Neither higher job completion nor token totals alone establish reliable or
cheaper agents.

The tasks use supplied dependency graphs and change risks. They do not establish
physical embodiment, learned dependencies, calibrated validity probabilities,
or improvements to SKL training. Paper claims distinguish the Qwen3-30B budget-allocation
gains from inconclusive cross-model and Joint-versus-FRD comparisons.
