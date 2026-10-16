"""Resumable, logged Prime Intellect evaluations of multi-round LLM tool policies."""

import asyncio
import hashlib
import json
import os
import random
import time
from datetime import UTC, datetime

from .environments import BenchmarkEnv, select_records
from .experiments import (
    EPISODES_PATH,
    call_upper_bound,
    episode_specs,
    load_episode_results,
)
from .feedback import ValidityBeliefs, select_feedback_records

ACTOR_PROMPT = """You are operating a versioned workflow. Complete as many jobs as possible within the action budget; the goal is to complete every job.
Each job needs certificates for exactly the listed requires_states, using their current predicted access tokens. Copy tokens from predictions. For repair workflows, requires_completed_jobs must have succeeded first. For DAG workflows there is no job-order constraint.
Return ONLY JSON {"actions":[{"job":INTEGER,"certificates":{"STATE_ID":"MODE@REVISION"}}]} with exactly four actions unless fewer than four jobs remain. Actions execute in the listed order. Never redo a completed job. Tool failures do not reveal the current valid token. Use feedback to avoid wasting actions. No inspection tool or other action is available; observation budgets are allocated separately. If a job failed and predictions have not changed, try other feasible jobs rather than repeating the same failure.
The workflow may change halfway through; refreshed predictions will be supplied.
IMPORTANT: requires_states includes the job's OWN state as well as dependencies. Include EVERY listed key. A missing key is a schema error, not a wrong prediction. Copy the CURRENT predictions exactly; never infer a different token from feedback.
Example: job 4 has requires_states [4,1,3] and predictions {"4":"blue@4","1":"amber@2","3":"green@1"}. A correct action is {"job":4,"certificates":{"4":"blue@4","1":"amber@2","3":"green@1"}}. Omitting key "4" or either dependency is invalid.
Return JSON only, without explanation."""

UPDATE_PROMPT = """Revise state-grounded predictive knowledge from these observed configurations and validated one-step continuations. For each supplied state, predict the access token that its next validate_access call will accept. The token format is MODE@REVISION. Later evidence overrides previous_prediction. Return ONLY a JSON object mapping each supplied state ID string to its predicted token string. Do not add states or explanations."""


def parse_object(content):
    if not isinstance(content, str):
        return {}
    try:
        result = json.loads(content)
    except ValueError:
        return {}
    return result if isinstance(result, dict) else {}


async def run(study, config, transport, request_options, output):
    try:
        from dotenv import load_dotenv
        from openai import APIError, AsyncOpenAI, RateLimitError
    except ImportError as exc:
        raise RuntimeError(
            "Fresh experiments require `uv sync --extra inference`."
        ) from exc
    load_dotenv()
    if not os.environ.get("PRIME_API_KEY"):
        raise ValueError("Set PRIME_API_KEY before running fresh experiments.")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 2,
        "study": study,
        "config": config,
        "transport": transport,
        "request_options": request_options,
    }
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if previous != manifest:
            raise ValueError(
                "Configuration or source changed; use a fresh run directory"
            )
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2))
    episodes = episode_specs(config)
    random.Random(73).shuffle(episodes)
    episode_path = output / EPISODES_PATH.name
    calls_path = output / "calls.jsonl"
    existing = load_episode_results(episode_path) if episode_path.exists() else []
    completed = {r["episode_id"] for r in existing}
    prior_calls = (
        [json.loads(line) for line in calls_path.read_text().splitlines()]
        if calls_path.exists()
        else []
    )
    # Reuse completed responses on resume; never silently pay for the same request twice.
    call_cache = {r["request_key"]: r for r in prior_calls}
    used_calls = len(prior_calls)
    expected = call_upper_bound(episodes)
    if expected > config["max_calls"]:
        raise ValueError(f"Expected {expected} calls exceeds cap")
    client = AsyncOpenAI(
        api_key=os.environ["PRIME_API_KEY"],
        base_url=transport["base_url"],
        max_retries=0,
        timeout=transport["timeout_seconds"],
    )
    semaphore = asyncio.Semaphore(transport["concurrency"])
    call_file = calls_path.open("a")
    episode_file = episode_path.open("a")

    async def call(spec, kind, number, messages):
        nonlocal used_calls
        request = {
            "model": spec["model"],
            "messages": messages,
            **transport["default_request"],
        }
        request.update(request_options.get(spec["model"], {}))
        key = hashlib.sha256(
            (
                spec["episode_id"]
                + kind
                + str(number)
                + json.dumps(request, sort_keys=True)
            ).encode()
        ).hexdigest()
        if key in call_cache:
            return call_cache[key]
        if used_calls >= config["max_calls"]:
            raise RuntimeError("Hard call cap reached")
        used_calls += 1
        started = time.monotonic()
        row = {
            "request_key": key,
            "episode_id": spec["episode_id"],
            "kind": kind,
            "number": number,
            "request": request,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        try:
            retry = transport["rate_limit"]
            for attempt in range(retry["max_attempts"]):
                try:
                    result = await client.chat.completions.create(**request)
                    break
                except RateLimitError as exc:
                    if attempt + 1 == retry["max_attempts"]:
                        raise
                    raw = exc.response.headers.get(
                        "retry-after", retry["min_delay_seconds"]
                    )
                    try:
                        delay = float(raw)
                    except (TypeError, ValueError):
                        delay = retry["min_delay_seconds"]
                    await asyncio.sleep(
                        min(
                            retry["max_delay_seconds"],
                            max(retry["min_delay_seconds"], delay),
                        )
                    )
            row.update(
                response_id=result.id,
                actual_model=result.model,
                content=result.choices[0].message.content,
                finish_reason=result.choices[0].finish_reason,
                usage=result.usage.model_dump() if result.usage else None,
            )
        except (APIError, IndexError, ValueError) as exc:
            row.update(
                error_type=type(exc).__name__,
                error_message=str(exc),
                content=None,
                usage=None,
            )
        row["latency_seconds"] = time.monotonic() - started
        call_file.write(json.dumps(row, sort_keys=True) + "\n")
        call_file.flush()
        call_cache[key] = row
        return row

    async def episode(spec):
        if spec["episode_id"] in completed:
            return
        async with semaphore:
            world = BenchmarkEnv(spec["seed"], spec["task"])
            beliefs = ValidityBeliefs(world.risk)
            belief_history = []
            selection_seconds = 0.0
            history = []
            logs = []
            selected_history = []
            valid_updates = 0
            correct_updates = 0
            update_total = 0
            invalid_actions = 0
            completed_rounds = []
            for turn in range(8):
                if turn in (0, 4):
                    epoch = turn // 4
                    if epoch:
                        world.mutate(epoch)
                        beliefs.advance()
                    selection_started = time.perf_counter()
                    belief_history.append(beliefs.valid.tolist())
                    if spec["selector"] in (
                        "feedback_risk",
                        "feedback_risk_dependency",
                        "joint",
                    ):
                        indices = select_feedback_records(
                            spec["selector"],
                            int(world.n * spec["budget_fraction"]),
                            world.parents,
                            world.done,
                            world.task,
                            beliefs.valid,
                            spec["seed"] + 90000 + epoch,
                        )
                    else:
                        indices = select_records(
                            world,
                            spec["selector"],
                            spec["budget_fraction"],
                            spec["seed"] + 90000 + epoch,
                            spec["missing_edge_fraction"],
                        )
                    selection_seconds += time.perf_counter() - selection_started
                    selected_history.append(indices)
                    update_total += len(indices)
                    if indices:
                        evidence = world.evidence(indices)
                        result = await call(
                            spec,
                            "update",
                            epoch,
                            [
                                {"role": "system", "content": UPDATE_PROMPT},
                                {"role": "user", "content": json.dumps(evidence)},
                            ],
                        )
                        logs.append(result)
                        updated = parse_object(result["content"])
                        for i in indices:
                            value = updated.get(str(i))
                            if isinstance(value, str):
                                world.cache[str(i)] = value
                                valid_updates += 1
                                correct_updates += value == world.truth[str(i)]
                        beliefs.update(evidence, world.cache)
                observation = world.public()
                observation.update(
                    round=turn,
                    actions_remaining=32 - world.attempts,
                    recent_feedback=history,
                    knowledge_epoch=turn // 4,
                )
                result = await call(
                    spec,
                    "act",
                    turn,
                    [
                        {"role": "system", "content": ACTOR_PROMPT},
                        {"role": "user", "content": json.dumps(observation)},
                    ],
                )
                logs.append(result)
                actions = parse_object(result["content"]).get("actions", [])
                if not isinstance(actions, list):
                    actions = []
                # A malformed/missing action spends its slot; no free retries.
                feedback = []
                for slot in range(4):
                    if len(world.done) == world.n:
                        break
                    item = actions[slot] if slot < len(actions) else None
                    reply = world.action(item)
                    beliefs.observe(item, reply, world.parents, world.cache)
                    if reply.get("reason", "").startswith("invalid"):
                        invalid_actions += 1
                    feedback.append(reply)
                history.extend(feedback)
                completed_rounds.append(len(world.done))
                if len(world.done) == world.n:
                    break
            row = {
                **spec,
                "study": study,
                "belief_history": belief_history,
                "selection_seconds": selection_seconds,
                "completed": len(world.done),
                "completion": len(world.done) / world.n,
                "success": int(len(world.done) == world.n),
                "attempts": world.attempts,
                "stale_errors": len(world.failures),
                "invalid_actions": invalid_actions,
                "updates": update_total,
                "valid_updates": valid_updates,
                "correct_updates": correct_updates,
                "selected": selected_history,
                "round_completion": completed_rounds,
                "calls": len(logs),
                "update_calls": sum(r["kind"] == "update" for r in logs),
                "prompt_tokens": sum(
                    (r["usage"] or {}).get("prompt_tokens", 0) for r in logs
                ),
                "completion_tokens": sum(
                    (r["usage"] or {}).get("completion_tokens", 0) for r in logs
                ),
                "missing_usage": sum(r["usage"] is None for r in logs),
                "api_errors": sum("error_type" in r for r in logs),
                "latency_seconds": sum(r["latency_seconds"] for r in logs),
                "feedback": history,
            }
            episode_file.write(json.dumps(row, sort_keys=True) + "\n")
            episode_file.flush()
            completed.add(spec["episode_id"])
            if len(completed) % 10 == 0 or len(completed) == len(episodes):
                print(
                    f"Completed {len(completed)}/{len(episodes)} episodes; calls {used_calls}/{config['max_calls']}",
                    flush=True,
                )

    try:
        await asyncio.gather(*(episode(spec) for spec in episodes))
    finally:
        call_file.close()
        episode_file.close()
        await client.close()
    print(f"Finished {len(episodes)} episodes in {output}", flush=True)
