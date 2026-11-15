"""Pipeline that crawls a department one professor at a time.

Each professor goes through 5 steps: listing -> api -> pages -> merge -> save.
We save the progress of every step to a small database, so:
- if the script stops halfway, running it again picks up where it left off
- if one professor fails, the rest of the department still gets crawled
- a failed step is retried a few times before we give up on it
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
