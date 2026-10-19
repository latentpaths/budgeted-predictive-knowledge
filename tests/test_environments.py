import pytest

from budgeted_predictive_knowledge.environments import (
    BenchmarkEnv,
    oracle_actions,
    select_records,
)


@pytest.mark.parametrize("task", ["dag", "precedence_chains"])
def test_authoritative_witness_completes_with_mutation(task):
    w = BenchmarkEnv(3, task)
    for turn in range(6):
        if turn == 3:
            w.mutate(1)
        for action in oracle_actions(w):
            assert w.action(action)["ok"]
    assert len(w.done) == 24


def test_no_hidden_state_in_public_observation():
    w = BenchmarkEnv(4, "dag")
    public = w.public()
    w.truth["0"] = "secret-value"
    assert w.public() == public
    assert "secret-value" not in str(public)


def test_missing_evidence_does_not_change_authority():
    w = BenchmarkEnv(5, "dag")
    before = w.truth.copy()
    w.graph(0.6)
    assert w.truth == before


def test_failures_do_not_reveal_token_or_complete_job():
    w = BenchmarkEnv(3, "precedence_chains")
    reply = w.action({"job": 0, "certificates": {"0": "wrong"}})
    assert not reply["ok"] and not w.done
    assert w.truth["0"] not in str(reply)
    assert (
        w.action({"job": 4, "certificates": {}})["reason"]
        == "prerequisite_job_incomplete"
    )


@pytest.mark.parametrize(
    "selector",
    [
        "even_spacing",
        "random",
        "change_risk",
        "dependency_importance",
        "risk_dependency",
    ],
)
def test_equal_record_budgets(selector):
    assert len(select_records(BenchmarkEnv(2, "dag"), selector, 0.2, 2)) == 4


def test_missing_certificate_is_not_staleness():
    w = BenchmarkEnv(0, "dag")
    r = w.action({"job": 4, "certificates": {}})
    assert r["reason"] == "invalid_missing_certificate_keys"
    assert w.failures == []
