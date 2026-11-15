"""Runs the 5 pipeline steps for each professor, in order.

Before a step runs, we mark it as "running" in the JobStore.
If a step throws an error, we save the error, stop that professor for this
run, and move on to the next professor.

When you run the same department again:
- steps that are already "done" are skipped (use force=True to redo them)
- steps that failed or never finished are tried again, up to max_attempts
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from app.pipeline.stages import STAGES, StageFunc, default_stage_funcs
from app.pipeline.store import JobStore


@dataclass
class ProfessorOutcome:
    professor: str
    completed_stages: list[str] = field(default_factory=list)
    failed_stage: str | None = None
    error: str | None = None
    skipped: bool = False

    @property
    def ok(self) -> bool:
        return self.failed_stage is None


@dataclass
class RunSummary:
    department: str
    outcomes: list[ProfessorOutcome]

    @property
    def succeeded(self) -> list[ProfessorOutcome]:
        return [o for o in self.outcomes if o.ok]

    @property
    def failed(self) -> list[ProfessorOutcome]:
        return [o for o in self.outcomes if not o.ok]


class PipelineRunner:
    def __init__(
        self,
        store: JobStore,
        stage_funcs: Mapping[str, StageFunc] | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.store = store
        self.stage_funcs = dict(stage_funcs) if stage_funcs else default_stage_funcs()
        missing = set(STAGES) - self.stage_funcs.keys()
        if missing:
            raise ValueError(f"missing stage functions: {sorted(missing)}")
        self.max_attempts = max_attempts

    def run(
        self, department: str, professors: Iterable[str], force: bool = False
    ) -> RunSummary:
        outcomes = [
            self._run_professor(department, professor, force)
            for professor in professors
        ]
        return RunSummary(department=department, outcomes=outcomes)

    def _run_professor(
        self, department: str, professor: str, force: bool
    ) -> ProfessorOutcome:
        context: dict[str, object] = {}
        outcome = ProfessorOutcome(professor=professor)

        for stage in STAGES:
            self.store.seed_pending(department, professor, stage, self.max_attempts)

        for stage in STAGES:
            job = self.store.get(department, professor, stage)

            if job and job.status == "done" and not force:
                context[stage] = job.result
                outcome.completed_stages.append(stage)
                continue

            if job and job.exhausted and not force:
                outcome.failed_stage = stage
                outcome.error = job.error or "max attempts reached"
                outcome.skipped = True
                return outcome

            self.store.mark_running(department, professor, stage, self.max_attempts)
            try:
                result = self.stage_funcs[stage](professor, dict(context))
            except Exception as exc:  # noqa: BLE001 - one prof failing shouldn't stop the others
                self.store.mark_failed(department, professor, stage, str(exc))
                outcome.failed_stage = stage
                outcome.error = str(exc)
                return outcome

            self.store.mark_done(department, professor, stage, result)
            context[stage] = result
            outcome.completed_stages.append(stage)

        return outcome
