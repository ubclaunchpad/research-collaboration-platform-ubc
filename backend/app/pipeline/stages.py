"""The 5 steps of the pipeline.

Every step function gets two things:
- professor: the professor's name
- context: the results of the steps that already ran, e.g. context["listing"]

It returns its own result, which has to be JSON-friendly (dicts, lists,
strings, numbers) so we can save it. If something goes wrong, just raise an
error and the runner will record it and retry later.

These are placeholders for now. Once the real scraping code is ready, pass
the real functions into PipelineRunner instead.
"""

from __future__ import annotations

from typing import Protocol

STAGES: tuple[str, ...] = ("listing", "api", "pages", "merge", "save")


class StageFunc(Protocol):
    def __call__(self, professor: str, context: dict[str, object]) -> object: ...


def fetch_listing(professor: str, context: dict[str, object]) -> object:
    """Find the professor's profile / list of papers."""
    raise NotImplementedError("plug in the real listing source for " + professor)


def fetch_api(professor: str, context: dict[str, object]) -> object:
    """Look the professor up in an outside API (e.g. OpenAlex)."""
    raise NotImplementedError("plug in the real API lookup for " + professor)


def fetch_pages(professor: str, context: dict[str, object]) -> object:
    """Scrape the professor's lab/profile pages."""
    raise NotImplementedError("plug in the real page scraper for " + professor)


def merge(professor: str, context: dict[str, object]) -> object:
    """Combine the results from listing, api and pages into one record."""
    raise NotImplementedError("plug in the real merge logic for " + professor)


def save(professor: str, context: dict[str, object]) -> object:
    """Save the combined record (e.g. to Supabase)."""
    raise NotImplementedError("plug in the real save step for " + professor)


def default_stage_funcs() -> dict[str, StageFunc]:
    return {
        "listing": fetch_listing,
        "api": fetch_api,
        "pages": fetch_pages,
        "merge": merge,
        "save": save,
    }
