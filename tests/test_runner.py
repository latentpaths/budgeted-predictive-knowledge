import asyncio
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from budgeted_predictive_knowledge import cli
from budgeted_predictive_knowledge.runner import parse_object, run


@pytest.fixture
def fake_provider(monkeypatch):
    requests = []

    class APIError(Exception):
        pass

    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        async def create(self, **request):
            requests.append(request)
            return SimpleNamespace(
                id="mock",
                model=request["model"],
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"actions": []}'),
                        finish_reason="stop",
                    )
                ],
                usage=SimpleNamespace(
                    model_dump=lambda: {"prompt_tokens": 10, "completion_tokens": 2}
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


def settings():
    config = {
        "max_calls": 8,
        "condition_groups": [
            {
                "name": "mock",
                "model": "mock-model",
                "seed_start": 99,
                "seeds": 1,
                "tasks": ["dag"],
                "selectors": ["no_updates"],
                "budget_fractions": [0.0],
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


def test_completed_episode_resume_makes_no_additional_requests(tmp_path, fake_provider):
    config, transport = settings()
    asyncio.run(run("mock", config, transport, {}, tmp_path))
    first = (tmp_path / "episode_results.jsonl").read_bytes()
    assert len(fake_provider) == 8
    asyncio.run(run("mock", config, transport, {}, tmp_path))
    assert len(fake_provider) == 8
    assert (tmp_path / "episode_results.jsonl").read_bytes() == first


def test_interrupted_episode_reuses_logged_responses(tmp_path, fake_provider):
    config, transport = settings()
    asyncio.run(run("mock", config, transport, {}, tmp_path))
    (tmp_path / "episode_results.jsonl").unlink()
    asyncio.run(run("mock", config, transport, {}, tmp_path))
    assert len(fake_provider) == 8
    row = json.loads((tmp_path / "episode_results.jsonl").read_text())
    assert row["calls"] == 8 and row["prompt_tokens"] == 80


def test_changed_manifest_rejected(tmp_path, fake_provider):
    config, transport = settings()
    asyncio.run(run("mock", config, transport, {}, tmp_path))
    with pytest.raises(ValueError, match="Configuration"):
        asyncio.run(run("mock", {**config, "max_calls": 9}, transport, {}, tmp_path))


def test_cli_defaults_to_study_directory_and_resumes(
    tmp_path, fake_provider, monkeypatch
):
    config, transport = settings()
    catalog = {
        "studies": {"mock": config},
        "transport": transport,
        "request_options": {},
    }
    monkeypatch.setattr(cli, "load_studies", lambda path: catalog)
    monkeypatch.chdir(tmp_path)
    cli.main(["run", "--study", "mock"])
    output = tmp_path / "output/runs/mock/episode_results.jsonl"
    first = output.read_bytes()
    cli.main(["run", "--study", "mock"])
    assert output.read_bytes() == first
    assert len(fake_provider) == 8


def test_json_parser_fails_closed():
    assert parse_object("not json") == {}
    assert parse_object("[1]") == {}
