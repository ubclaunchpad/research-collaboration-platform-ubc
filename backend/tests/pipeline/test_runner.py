import pytest

from app.pipeline.runner import PipelineRunner
from app.pipeline.stages import STAGES
from app.pipeline.store import JobStore


def recording_stage_funcs(calls, fail_on=None):
    """Fake step functions that log each call to `calls`.

    Any (professor, step) pair in `fail_on` raises an error instead.
    """
    fail_on = fail_on or set()

    def make(stage):
        def fn(professor, context):
            calls.append((professor, stage))
            if (professor, stage) in fail_on:
                raise RuntimeError(f"{stage} failed for {professor}")
            return {"stage": stage, "professor": professor, "seen": dict(context)}

        return fn

    return {stage: make(stage) for stage in STAGES}


def test_full_run_completes_all_stages_in_order(tmp_path):
    calls = []
    with JobStore(tmp_path / "jobs.db") as store:
        runner = PipelineRunner(store, recording_stage_funcs(calls))
        summary = runner.run("CS", ["Alice"])

    assert summary.failed == []
    outcome = summary.outcomes[0]
    assert outcome.completed_stages == list(STAGES)
    assert calls == [("Alice", stage) for stage in STAGES]


def test_rerun_skips_completed_stages_unless_forced(tmp_path):
    calls = []
    db_path = tmp_path / "jobs.db"
    with JobStore(db_path) as store:
        runner = PipelineRunner(store, recording_stage_funcs(calls))
        runner.run("CS", ["Alice"])
    assert len(calls) == len(STAGES)

    # Simulate a restart: new store + runner, same db file.
    with JobStore(db_path) as store:
        runner = PipelineRunner(store, recording_stage_funcs(calls))
        summary = runner.run("CS", ["Alice"])
    assert summary.outcomes[0].completed_stages == list(STAGES)
    assert len(calls) == len(STAGES)  # nothing ran again

    with JobStore(db_path) as store:
        runner = PipelineRunner(store, recording_stage_funcs(calls))
        runner.run("CS", ["Alice"], force=True)
    assert len(calls) == 2 * len(STAGES)  # force=True ran every step again


def test_failed_stage_retries_until_limit_then_stays_failed(tmp_path):
    calls = []
    db_path = tmp_path / "jobs.db"
    fail_on = {("Alice", "api")}

    for _ in range(3):
        with JobStore(db_path) as store:
            runner = PipelineRunner(
                store, recording_stage_funcs(calls, fail_on=fail_on), max_attempts=3
            )
            summary = runner.run("CS", ["Alice"])

    outcome = summary.outcomes[0]
    assert outcome.failed_stage == "api"
    assert outcome.completed_stages == ["listing"]
    api_calls = [c for c in calls if c == ("Alice", "api")]
    assert len(api_calls) == 3  # 1 try per run, 3 runs

    # 4th run: out of retries, so api shouldn't run again.
    with JobStore(db_path) as store:
        runner = PipelineRunner(
            store, recording_stage_funcs(calls, fail_on=fail_on), max_attempts=3
        )
        summary = runner.run("CS", ["Alice"])

    outcome = summary.outcomes[0]
    assert outcome.skipped is True
    assert outcome.failed_stage == "api"
    assert len([c for c in calls if c == ("Alice", "api")]) == 3  # unchanged

    with JobStore(db_path) as store:
        job = store.get("CS", "Alice", "api")
        assert job.status == "failed"
        assert job.exhausted


def test_one_broken_professor_does_not_block_others(tmp_path):
    calls = []
    with JobStore(tmp_path / "jobs.db") as store:
        runner = PipelineRunner(
            store, recording_stage_funcs(calls, fail_on={("Carol", "pages")})
        )
        summary = runner.run("CS", ["Carol", "Dave"])

    by_name = {o.professor: o for o in summary.outcomes}
    assert by_name["Carol"].failed_stage == "pages"
    assert by_name["Dave"].ok
    assert by_name["Dave"].completed_stages == list(STAGES)


def test_resume_after_a_crash_continues_from_last_completed_stage(tmp_path):
    db_path = tmp_path / "jobs.db"
    calls = []

    def crashing_pages(professor, context):
        calls.append((professor, "pages"))
        raise KeyboardInterrupt("process killed mid-stage")

    funcs = recording_stage_funcs(calls)
    funcs["pages"] = crashing_pages

    with JobStore(db_path) as store:
        runner = PipelineRunner(store, funcs)
        with pytest.raises(KeyboardInterrupt):
            runner.run("CS", ["Alice"])

    # listing and api finished and were saved before the crash.
    with JobStore(db_path) as store:
        assert store.get("CS", "Alice", "listing").status == "done"
        assert store.get("CS", "Alice", "api").status == "done"
        assert store.get("CS", "Alice", "pages").status == "running"

    # Restart with a working pages step.
    calls.clear()
    with JobStore(db_path) as store:
        runner = PipelineRunner(store, recording_stage_funcs(calls))
        summary = runner.run("CS", ["Alice"])

    outcome = summary.outcomes[0]
    assert outcome.ok
    assert outcome.completed_stages == list(STAGES)
    # listing and api were skipped, not run again.
    assert calls == [("Alice", "pages"), ("Alice", "merge"), ("Alice", "save")]


def test_merge_stage_receives_prior_stage_results_as_context(tmp_path):
    seen_context = {}

    def listing(professor, context):
        return {"papers": ["p1"]}

    def api(professor, context):
        return {"citations": 10}

    def pages(professor, context):
        return {"bio": "..."}

    def merge(professor, context):
        seen_context.update(context)
        return {"merged": True}

    def save(professor, context):
        return {"saved": True}

    with JobStore(tmp_path / "jobs.db") as store:
        runner = PipelineRunner(
            store,
            {
                "listing": listing,
                "api": api,
                "pages": pages,
                "merge": merge,
                "save": save,
            },
        )
        runner.run("CS", ["Alice"])

    assert seen_context == {
        "listing": {"papers": ["p1"]},
        "api": {"citations": 10},
        "pages": {"bio": "..."},
    }
