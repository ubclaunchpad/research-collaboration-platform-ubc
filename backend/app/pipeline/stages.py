"""Stage definitions for the per-professor crawl pipeline.

Each stage function takes (professor, context) where `context` is a dict of
the JSON-serializable results of every stage that already ran for that
professor in this run (keyed by stage name), and returns this stage's own
JSON-serializable result. Raise on failure; the runner records the error and
retries on a later run.

The implementations below are placeholders wiring the five stages together
end to end. Swap them out (pass your own mapping into PipelineRunner) once
the real listing/API/page-scraping logic exists.
"""

from __future__ import annotations

from typing import Protocol

STAGES: tuple[str, ...] = ("listing", "api", "pages", "merge", "save")


class StageFunc(Protocol):
    def __call__(self, professor: str, context: dict[str, object]) -> object: ...


def fetch_listing(professor: str, context: dict[str, object]) -> object:
    """Discover the professor's publication/profile listing."""
    raise NotImplementedError("plug in the real listing source for " + professor)


def fetch_api(professor: str, context: dict[str, object]) -> object:
    """Query an external API (e.g. a publications API) for this professor."""
    raise NotImplementedError("plug in the real API lookup for " + professor)


def fetch_pages(professor: str, context: dict[str, object]) -> object:
    """Scrape the professor's lab/profile pages."""
    raise NotImplementedError("plug in the real page scraper for " + professor)


def merge(professor: str, context: dict[str, object]) -> object:
    """Combine the listing/api/pages results into one record."""
    raise NotImplementedError("plug in the real merge logic for " + professor)


def save(professor: str, context: dict[str, object]) -> object:
    """Persist the merged record (e.g. to Supabase)."""
    raise NotImplementedError("plug in the real save step for " + professor)


def default_stage_funcs() -> dict[str, StageFunc]:
    return {
        "listing": fetch_listing,
        "api": fetch_api,
        "pages": fetch_pages,
        "merge": merge,
        "save": save,
    }
