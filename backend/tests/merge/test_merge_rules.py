"""Conflicting fields resolve by FIELD_PRIORITY, no matter the arrival order."""

import itertools

import pytest

from app.merge.rules import resolve
from app.merge.store import ResearcherStore, SourceRecord

LISTING = SourceRecord(
    "dept_listing",
    "https://www.cs.ubc.ca/people/joanna-mcgrenere",
    {
        "full_name": "Joanna McGrenere",
        "title": "Co-Head, Professor",
        "department": "Computer Science",
        "email": "head@cs.ubc.ca",
        "research_areas": ["Human-Computer Interaction"],
        "interests": [],
    },
)
OPENALEX = SourceRecord(
    "openalex",
    "https://openalex.org/A5016459516",
    {
        "full_name": "Joanna McGrenere",
        "openalex_id": "https://openalex.org/A5016459516",
        "orcid": "https://orcid.org/0000-0002-1234-5678",
        "papers": [{"title": "From OpenAlex", "year": 2020}],
        "topics": ["Human-Computer Interaction"],
        # OpenAlex isn't allowed to set these, so they must be ignored.
        "title": "Researcher",
        "email": "jm@openalex.example",
    },
)
PAGE = SourceRecord(
    "prof_page",
    "https://www.cs.ubc.ca/~joanna/",
    {
        "full_name": "Dr. Joanna McGrenere",
        "title": "Professor of Computer Science",
        "email": "joanna@cs.ubc.ca",
        "interests": ["accessibility", "personalization"],
        "papers": [{"title": "From her page", "year": 2024}],
    },
)


def as_tuples(*records):
    return [r.as_tuple() for r in records]


def test_each_field_comes_from_its_priority_source():
    out = resolve(as_tuples(PAGE, OPENALEX, LISTING))

    # name / title / email: dept listing
    assert out.record["full_name"] == "Joanna McGrenere"
    assert out.record["title"] == "Co-Head, Professor"
    assert out.record["email"] == "head@cs.ubc.ca"
    assert out.provenance["email"] == "dept_listing"
    # papers / topics: OpenAlex
    assert out.record["papers"] == [{"title": "From OpenAlex", "year": 2020}]
    assert out.record["topics"] == ["Human-Computer Interaction"]
    assert out.provenance["papers"] == "openalex"
    # interests: prof page (the listing's empty list doesn't count)
    assert out.record["interests"] == ["accessibility", "personalization"]
    assert out.provenance["interests"] == "prof_page"


def test_losing_values_are_kept_as_conflicts():
    out = resolve(as_tuples(LISTING, OPENALEX, PAGE))

    assert out.conflicts["email"] == [
        {"source": "prof_page", "value": "joanna@cs.ubc.ca"}
    ]
    assert out.conflicts["title"] == [
        {"source": "prof_page", "value": "Professor of Computer Science"}
    ]
    # OpenAlex's email/title aren't in their priority lists, so not conflicts
    assert "jm@openalex.example" not in str(out.conflicts)
    # same value from two sources isn't a conflict
    assert "topics" not in out.conflicts


def test_lower_priority_source_fills_gaps():
    listing = SourceRecord("dept_listing", LISTING.key, {**LISTING.fields, "title": ""})
    out = resolve(as_tuples(listing, PAGE))
    assert out.record["title"] == "Professor of Computer Science"
    assert out.provenance["title"] == "prof_page"


def test_unknown_fields_are_dropped():
    page = SourceRecord("prof_page", PAGE.key, {**PAGE.fields, "shoe_size": 42})
    assert "shoe_size" not in resolve(as_tuples(page)).record


@pytest.mark.parametrize("later", [(OPENALEX, PAGE), (PAGE, OPENALEX)])
def test_separate_runs_in_any_order_resolve_the_same(tmp_path, later):
    """Whichever source runs last must not win.

    Each pipeline run carries the listing plus one other source, like a
    per-professor run where one fetch failed and was retried later. The
    final record must not depend on which run came last.
    """
    with ResearcherStore(tmp_path / "db.sqlite") as store:
        store.ingest([LISTING])
        store.ingest([LISTING, later[0]])
        store.ingest([LISTING, later[1]])
        store.ingest([LISTING])  # listing again, last
        (researcher,) = store.researchers()

    assert researcher["email"] == "head@cs.ubc.ca"
    assert researcher["title"] == "Co-Head, Professor"
    assert researcher["papers"] == [{"title": "From OpenAlex", "year": 2020}]
    assert researcher["interests"] == ["accessibility", "personalization"]


def test_same_bundle_in_any_order_gives_same_record(tmp_path):
    exports = []
    for i, order in enumerate(itertools.permutations([LISTING, OPENALEX, PAGE])):
        with ResearcherStore(tmp_path / f"{i}.sqlite") as store:
            store.ingest(list(order))
            exports.append(store.export())
    assert all(e == exports[0] for e in exports)
