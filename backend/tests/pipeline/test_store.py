from app.pipeline.store import DONE, FAILED, PENDING, RUNNING, JobStore


def test_get_missing_job_is_none(tmp_path):
    with JobStore(tmp_path / "jobs.db") as store:
        assert store.get("CS", "Alice", "listing") is None


def test_mark_running_creates_row_and_increments_attempts(tmp_path):
    with JobStore(tmp_path / "jobs.db") as store:
        first = store.mark_running("CS", "Alice", "listing", max_attempts=3)
        assert first == 1
        job = store.get("CS", "Alice", "listing")
        assert job.status == RUNNING
        assert job.attempts == 1

        second = store.mark_running("CS", "Alice", "listing", max_attempts=3)
        assert second == 2
        assert store.get("CS", "Alice", "listing").attempts == 2


def test_mark_done_persists_result(tmp_path):
    with JobStore(tmp_path / "jobs.db") as store:
        store.mark_running("CS", "Alice", "listing", max_attempts=3)
        store.mark_done("CS", "Alice", "listing", {"papers": ["a", "b"]})
        job = store.get("CS", "Alice", "listing")
        assert job.status == DONE
        assert job.result == {"papers": ["a", "b"]}
        assert job.error is None


def test_mark_failed_records_error_and_not_exhausted_below_limit(tmp_path):
    with JobStore(tmp_path / "jobs.db") as store:
        store.mark_running("CS", "Alice", "api", max_attempts=3)
        store.mark_failed("CS", "Alice", "api", "timeout")
        job = store.get("CS", "Alice", "api")
        assert job.status == FAILED
        assert job.error == "timeout"
        assert job.attempts == 1
        assert not job.exhausted


def test_exhausted_once_attempts_reach_max(tmp_path):
    with JobStore(tmp_path / "jobs.db") as store:
        for _ in range(3):
            store.mark_running("CS", "Alice", "api", max_attempts=3)
            store.mark_failed("CS", "Alice", "api", "timeout")
        job = store.get("CS", "Alice", "api")
        assert job.attempts == 3
        assert job.exhausted


def test_seed_pending_creates_row_but_never_overwrites_progress(tmp_path):
    with JobStore(tmp_path / "jobs.db") as store:
        store.seed_pending("CS", "Alice", "listing", max_attempts=3)
        job = store.get("CS", "Alice", "listing")
        assert job.status == PENDING
        assert job.attempts == 0

        store.mark_running("CS", "Alice", "listing", max_attempts=3)
        store.mark_done("CS", "Alice", "listing", {"ok": True})

        store.seed_pending("CS", "Alice", "listing", max_attempts=3)
        job = store.get("CS", "Alice", "listing")
        assert job.status == DONE  # untouched by the later seed call


def test_list_jobs_filters_by_department(tmp_path):
    with JobStore(tmp_path / "jobs.db") as store:
        store.mark_running("CS", "Alice", "listing", max_attempts=3)
        store.mark_running("Physics", "Bob", "listing", max_attempts=3)
        assert [j.professor for j in store.list_jobs("CS")] == ["Alice"]
        assert {j.professor for j in store.list_jobs()} == {"Alice", "Bob"}
