"""Run the whole pipeline for a department with one command.

Examples:

    uv run python -m app.pipeline.cli "Computer Science" \\
        --professors "Alice Smith,Bob Lee"

    uv run python -m app.pipeline.cli "Computer Science" \\
        --professors-file roster.json --force

--professors-file is a JSON file with a list of names.
For now you pass in the professor names yourself. Getting them from the
real UBC directory will be its own ticket.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.pipeline.runner import PipelineRunner
from app.pipeline.store import JobStore


def _load_professors(args: argparse.Namespace) -> list[str]:
    if args.professors_file:
        data = json.loads(Path(args.professors_file).read_text())
        return [str(name) for name in data]
    if args.professors:
        return [name.strip() for name in args.professors.split(",") if name.strip()]
    raise SystemExit("pass --professors or --professors-file")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("department")
    parser.add_argument("--professors", help="comma-separated professor names")
    parser.add_argument("--professors-file", help="path to a JSON list of names")
    parser.add_argument(
        "--db-path", default="pipeline_state.db", help="job tracking SQLite file"
    )
    parser.add_argument(
        "--force", action="store_true", help="re-run stages already marked done"
    )
    parser.add_argument(
        "--max-attempts", type=int, default=3, help="retry limit per stage"
    )
    args = parser.parse_args(argv)

    professors = _load_professors(args)

    with JobStore(args.db_path) as store:
        runner = PipelineRunner(store, max_attempts=args.max_attempts)
        summary = runner.run(args.department, professors, force=args.force)

    for outcome in summary.outcomes:
        if outcome.ok:
            print(f"ok      {outcome.professor}: {', '.join(outcome.completed_stages)}")
        else:
            print(
                f"failed  {outcome.professor}: stuck at {outcome.failed_stage} "
                f"({outcome.error})"
            )

    return 1 if summary.failed else 0


if __name__ == "__main__":
    sys.exit(main())
