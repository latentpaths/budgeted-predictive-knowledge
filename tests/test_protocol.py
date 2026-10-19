"""Frozen pre-cleanup request and outcome checks, using a deterministic provider."""

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from budgeted_predictive_knowledge.runner import run

REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures/protocol_reference.json").read_text()
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def install_provider(monkeypatch):
    """Refresh from supplied evidence; submit certificates from the public cache."""
    requests = []

    class APIError(Exception):
        pass

    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        async def create(self, **request):
            requests.append(request)
            payload = json.loads(request["messages"][1]["content"])
            if isinstance(payload, list):
                # Deliberate updater mistakes exercise validity and rejection feedback.
                response = {
                    record["state"]: record["continuation"]["argument"]
                    if int(record["state"]) % 3
                    else "wrong"
                    for record in payload
                }
            else:
                completed = set(payload["completed_jobs"])
                actions = []
                for job in payload["jobs"]:
                    if (
                        job["job"] in completed
                        or not set(job["requires_completed_jobs"]) <= completed
                    ):
                        continue
                    actions.append(
                        {
                            "job": job["job"],
                            "certificates": {
                                str(i): payload["predictions"][str(i)]
                                for i in job["requires_states"]
                            },
                        }
                    )
                    completed.add(job["job"])
                    if len(actions) == 4:
                        break
                response = {"actions": actions}
            return SimpleNamespace(
                id="protocol-test",
                model=request["model"],
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps(response)),
                        finish_reason="stop",
                    )
                ],
                usage=SimpleNamespace(
                    model_dump=lambda: {
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                    }
                ),
            )

        async def close(self):
            pass

    sdk = ModuleType("openai")
    sdk.APIError = APIError
    sdk.RateLimitError = type("RateLimitError", (APIError,), {})
    sdk.AsyncOpenAI = Client
    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    monkeypatch.setitem(sys.modules, "openai", sdk)
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    monkeypatch.setenv("PRIME_API_KEY", "test-only")
    return requests


def protocol_settings(selector, task):
    fraction = (
        0 if selector == "no_updates" else 1 if selector == "all_records" else 0.2
    )
    config = {
        "max_calls": 10,
        "condition_groups": [
            {
                "name": "protocol",
                "model": "mock-model",
                "seed_start": 17,
                "seeds": 1,
                "tasks": [task],
                "selectors": [selector],
                "budget_fractions": [fraction],
            }
        ],
    }
    transport = {
        "base_url": "https://example.invalid",
        "concurrency": 1,
        "timeout_seconds": 1,
        "default_request": {},
        "rate_limit": {"max_attempts": 1},
    }
    return config, transport


def outcome_digest(row):
    identity_and_timing = {
        "episode_id",
        "condition_group",
        "task",
        "selector",
        "budget_fraction",
        "missing_edge_fraction",
        "study",
        "model",
        "seed",
        "selection_seconds",
        "latency_seconds",
    }
    return digest(
        {key: value for key, value in row.items() if key not in identity_and_timing}
    )


@pytest.mark.parametrize(
    "reference", REFERENCE, ids=lambda r: f"{r['task']}/{r['selector']}"
)
def test_policy_requests_and_outcomes_match_original(reference, tmp_path, monkeypatch):
    requests = install_provider(monkeypatch)
    config, transport = protocol_settings(reference["selector"], reference["task"])
    asyncio.run(run("protocol", config, transport, {}, tmp_path))
    row = json.loads((tmp_path / "episode_results.jsonl").read_text())
    assert digest(requests) == reference["requests_sha256"]
    assert outcome_digest(row) == reference["outcome_sha256"]
