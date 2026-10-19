"""Versioned executable workflows with a hidden authoritative configuration.

Models receive a possibly stale predictive cache, task schemas, and tool feedback.
Only selected records receive fresh observation/continuation evidence. No hidden
configuration is exposed to action selection or dependency ranking.
"""

import random
from dataclasses import dataclass, field

MODES = ("amber", "blue", "green", "violet")


@dataclass
class BenchmarkEnv:
    seed: int
    task: str
    n: int = 24
    parents: list[list[int]] = field(init=False)
    cache: dict[str, str] = field(init=False)
    truth: dict[str, str] = field(init=False)
    risk: list[float] = field(init=False)
    done: set[int] = field(default_factory=set)
    failures: list[dict] = field(default_factory=list)
    attempts: int = 0
    epoch: int = 0

    def __post_init__(self):
        rng = random.Random(self.seed)
        if self.task not in ("dag", "precedence_chains"):
            raise ValueError("unknown task")
        self.parents = []
        for j in range(self.n):
            if self.task == "precedence_chains":
                # Four independent precedence chains; an early failure blocks a chain.
                self.parents.append([j - 4] if j >= 4 else [])
            else:
                self.parents.append(sorted(rng.sample(range(j), min(j, 2))))
        self.cache = {
            str(i): f"{rng.choice(MODES)}@{rng.randrange(1, 5)}" for i in range(self.n)
        }
        self.truth = self.cache.copy()
        self.risk = [rng.uniform(0.02, 0.30) for _ in range(self.n)]
        self.mutate(0)

    def mutate(self, epoch):
        """Exogenous mutations are paired across policies, independent of actions."""
        self.epoch = epoch
        rng = random.Random(self.seed + 200000 + epoch * 10000)
        changed = []
        for i, probability in enumerate(self.risk):
            if rng.random() < probability:
                mode, revision = self.truth[str(i)].split("@")
                mode = rng.choice([m for m in MODES if m != mode])
                self.truth[str(i)] = f"{mode}@{int(revision) + 1}"
                changed.append(i)
        return changed

    def graph(self, missing_edge_fraction=0.0):
        rng = random.Random(self.seed + 400000)
        edges = [[] for _ in range(self.n)]
        for j, parents in enumerate(self.parents):
            for i in parents:
                if rng.random() >= missing_edge_fraction:
                    edges[i].append(j)
        return edges

    def evidence(self, indices):
        # A one-step successful read-only continuation gives a predictive target.
        records = []
        for i in indices:
            mode, revision = self.truth[str(i)].split("@")
            records.append(
                {
                    "state": str(i),
                    "previous_prediction": self.cache[str(i)],
                    "observed_configuration": {"mode": mode, "revision": int(revision)},
                    "continuation": {
                        "action": "validate_access",
                        "argument": f"{mode}@{revision}",
                        "result": "accepted",
                    },
                }
            )
        return records

    def action(self, item):
        self.attempts += 1
        if not isinstance(item, dict) or type(item.get("job")) is not int:
            return {"ok": False, "reason": "invalid_action"}
        job = item["job"]
        if not 0 <= job < self.n or job in self.done:
            return {"job": job, "ok": False, "reason": "invalid_or_completed_job"}
        if self.task == "precedence_chains" and any(
            p not in self.done for p in self.parents[job]
        ):
            return {"job": job, "ok": False, "reason": "prerequisite_job_incomplete"}
        certificates = item.get("certificates", {})
        if not isinstance(certificates, dict):
            return {"job": job, "ok": False, "reason": "invalid_certificates"}
        required = [job, *self.parents[job]]
        missing_keys = [str(i) for i in required if str(i) not in certificates]
        if missing_keys:
            return {
                "job": job,
                "ok": False,
                "reason": "invalid_missing_certificate_keys",
                "required_keys": [str(i) for i in required],
                "missing_keys": missing_keys,
            }
        wrong = [
            str(i) for i in required if certificates.get(str(i)) != self.truth[str(i)]
        ]
        if wrong:
            result = {
                "job": job,
                "ok": False,
                "reason": "stale_or_wrong_prediction",
                "states": wrong,
            }
            self.failures.append(result)
            return result
        self.done.add(job)
        return {"job": job, "ok": True}

    def public(self):
        """Preserve the model-facing observation format used in the study."""
        return {
            "domain": "repair" if self.task == "precedence_chains" else "dag",
            "jobs": [
                {
                    "job": j,
                    "requires_states": [j, *parents],
                    "requires_completed_jobs": parents
                    if self.task == "precedence_chains"
                    else [],
                }
                for j, parents in enumerate(self.parents)
            ],
            "predictions": self.cache.copy(),
            "completed_jobs": sorted(self.done),
        }


def select_records(world, selector, budget_fraction, seed, missing_edge_fraction=0):
    from .selection import select

    edges = world.graph(missing_edge_fraction)
    return select(selector, budget_fraction, edges, world.risk, seed)


def oracle_actions(world, limit=4):
    """Verifier sanity check only; never used by a measured model."""
    actions = []
    completed = world.done.copy()
    for j, parents in enumerate(world.parents):
        if j in completed:
            continue
        if world.task == "precedence_chains" and not set(parents) <= completed:
            continue
        actions.append(
            {
                "job": j,
                "certificates": {str(i): world.truth[str(i)] for i in [j, *parents]},
            }
        )
        completed.add(j)
        if len(actions) == limit:
            break
    return actions
