"""Validate evidence, reproduce results, or run fresh inference experiments."""

import argparse
import asyncio
import json
from pathlib import Path

from .experiments import (
    ANALYSIS_PATH,
    EPISODES_PATH,
    RUNS_PATH,
    STUDIES_PATH,
    experiment_overview,
    load_studies,
    merged_transport,
    plan_run,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser(
        "experiments", help="Show the questions each experiment answers"
    )
    command.add_argument("--config", type=Path, default=STUDIES_PATH)
    command.add_argument("--json", action="store_true", dest="as_json")
    for name in ("validate", "reproduce"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, default=STUDIES_PATH)
        command.add_argument("--data", type=Path, default=EPISODES_PATH)
        if name != "validate":
            command.add_argument("--output", type=Path, default=ANALYSIS_PATH)
    command = commands.add_parser("run", help="Run or resume a fresh inference study")
    command.add_argument("--config", type=Path, default=STUDIES_PATH)
    command.add_argument("--study", required=True)
    command.add_argument("--output", type=Path)
    command.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "experiments":
            overview = experiment_overview(load_studies(args.config))
            if args.as_json:
                print(json.dumps(overview, indent=2))
            else:
                for experiment in overview:
                    print(
                        f"{experiment['experiment_name']} ({experiment['episode_count']:,} episodes)"
                    )
                    print(f"  {experiment['question']}")
                    for model in experiment["models"]:
                        budgets = ", ".join(map(str, model["record_budgets"]))
                        controls = ", ".join(map(str, model["control_budgets"]))
                        detail = f"; controls: {controls}" if controls else ""
                        print(
                            f"  {model['model_name']}: {model['episode_count']:,} episodes; records per update: {budgets}{detail}"
                        )
                    if experiment["reference_note"]:
                        print(f"  {experiment['reference_note']}")
                    print()
            return
        if args.command == "run":
            catalog = load_studies(args.config)
            if args.study not in catalog["studies"]:
                parser.error(
                    "unknown study; choose from " + ", ".join(catalog["studies"])
                )
            plan = plan_run(args.study, catalog)
            if args.dry_run:
                print(json.dumps(plan, indent=2))
                return
            from .runner import run

            asyncio.run(
                run(
                    args.study,
                    catalog["studies"][args.study],
                    merged_transport(catalog, catalog["studies"][args.study]),
                    catalog["request_options"],
                    args.output if args.output is not None else RUNS_PATH / args.study,
                )
            )
        else:
            from .validation import validate

            validation = validate(data=args.data, config=args.config)
            if args.command == "validate":
                print(json.dumps(validation, indent=2))
                return
            # Never write analysis artifacts into the input directories.
            output = args.output.resolve()
            if any(
                output == path.resolve().parent or output in path.resolve().parents
                for path in (args.data, args.config)
            ):
                parser.error(
                    "choose an output directory separate from the evidence and configuration"
                )
            from .analysis import analyze

            result = analyze(args.data, args.config, args.output)
            print(json.dumps({"validation": validation, "results": result}, indent=2))
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
