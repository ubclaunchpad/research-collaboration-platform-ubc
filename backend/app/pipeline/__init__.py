"""Per-professor crawl pipeline: listing -> api -> pages -> merge -> save.

Each stage of each professor is tracked as a job row (see store.JobStore) so
a run can be killed and resumed, a broken professor doesn't block the rest
of the department, and failed stages retry up to a limit before being left
for manual review.
"""

from app.pipeline.runner import PipelineRunner, ProfessorOutcome, RunSummary
from app.pipeline.stages import STAGES
from app.pipeline.store import JobRecord, JobStore

__all__ = [
    "STAGES",
    "JobRecord",
    "JobStore",
    "PipelineRunner",
    "ProfessorOutcome",
    "RunSummary",
]
