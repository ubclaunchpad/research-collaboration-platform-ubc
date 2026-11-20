"""Identity matching, upserts and the review list."""

import pytest

from app.merge.store import ResearcherStore, SourceRecord


@pytest.fixture
def store(tmp_path):
    with ResearcherStore(tmp_path / "db.sqlite") as s:
        yield s


def listing(key="https://cs/kevin", **fields):
    base = {
        "full_name": "Kevin Leyton-Brown",
        "department": "Computer Science",
        "email": "kevinlb@cs.ubc.ca",
        "title": "Professor",
    }
    return SourceRecord("dept_listing", key, {**base, **fields})


def openalex(key="https://openalex.org/A1", **fields):
    base = {"full_name": "Kevin Leyton-Brown", "openalex_id": key}
    return SourceRecord("openalex", key, {**base, **fields})


def page(key="https://cs/~kevinlb", **fields):
    return SourceRecord("prof_page", key, {"full_name": "Kevin Leyton-Brown", **fields})


# ---- upserts ---------------------------------------------------------------


def test_reingesting_the_same_records_does_not_duplicate(store):
    first = store.ingest([listing(), openalex()])
    before = store.export()
    second = store.ingest([listing(), openalex()])

    assert first.status == "created"
    assert second.status == "merged"
    assert second.researcher_id == first.researcher_id
    assert store.export() == before
    assert store.counts() == {
        "researchers": 1,
        "source_records": 2,
        "review_items": 0,
    }


def test_updated_source_record_replaces_old_values(store):
    store.ingest([listing()])
    store.ingest([listing(title="Distinguished Professor")])
    (researcher,) = store.researchers()
    assert researcher["title"] == "Distinguished Professor"
    assert store.counts()["source_records"] == 1


# ---- matching ----------------------------------------------------------------


def test_orcid_links_records_even_when_names_differ(store):
    rid = store.ingest([listing(orcid="0000-0001-2345-6789"), openalex()]).researcher_id
    result = store.ingest(
        [page(full_name="K. L-B", orcid="https://orcid.org/0000-0001-2345-6789")]
    )
    assert (result.status, result.researcher_id) == ("merged", rid)


def test_email_links_when_name_is_compatible(store):
    rid = store.ingest([listing()]).researcher_id
    result = store.ingest(
        [page(full_name="Dr. Kevin Leyton-Brown", email="KevinLB@cs.ubc.ca")]
    )
    assert (result.status, result.researcher_id) == ("merged", rid)
    assert result.reason == "email matches"


def test_name_and_department_link_when_no_identifiers(store):
    rid = store.ingest([listing(key="https://cs/a")]).researcher_id
    result = store.ingest([page(key="https://x/b", department="Computer Science")])
    assert (result.status, result.researcher_id) == ("merged", rid)


def test_new_listing_creates_new_researcher(store):
    store.ingest([listing()])
    result = store.ingest(
        [
            listing(
                key="https://cs/cc",
                full_name="Cristina Conati",
                email="conati@cs.ubc.ca",
            )
        ]
    )
    assert result.status == "created"
    assert len(store.researchers()) == 2


# ---- review list ----------------------------------------------------------------


def review_reason(store, result):
    assert result.status == "review"
    assert store.counts()["review_items"] >= 1
    (item,) = [i for i in store.review_items() if i["id"] == result.review_id]
    return item["reason"]


def test_loose_name_match_goes_to_review(store):
    store.ingest([listing(full_name="Laks V.S. Lakshmanan", email="laks@cs.ubc.ca")])
    result = store.ingest(
        [page(full_name="L. Lakshmanan", department="Computer Science")]
    )
    assert review_reason(store, result) == "low-confidence name match"


def test_same_name_other_department_goes_to_review(store):
    store.ingest([listing()])
    result = store.ingest(
        [listing(key="https://econ/kevin", department="Economics", email=None)]
    )
    assert review_reason(store, result) == "low-confidence name match"
    assert len(store.researchers()) == 1


def test_name_without_department_goes_to_review(store):
    store.ingest([listing()])
    result = store.ingest([page()])  # no department, no identifiers
    assert review_reason(store, result) == "low-confidence name match"


def test_shared_email_with_different_name_goes_to_review(store):
    store.ingest([listing(full_name="Joanna McGrenere", email="head@cs.ubc.ca")])
    result = store.ingest(
        [
            listing(
                key="https://cs/other-head",
                full_name="Some Other Head",
                email="head@cs.ubc.ca",
            )
        ]
    )
    assert review_reason(store, result) == "email matches but name does not"


def test_orcid_conflict_goes_to_review(store):
    store.ingest([listing(), openalex(orcid="0000-0001-0000-0001")])
    result = store.ingest(
        [page(email="kevinlb@cs.ubc.ca", orcid="0000-0009-9999-9999")]
    )
    assert review_reason(store, result) == "ORCID differs"


def test_identifiers_pointing_at_two_people_go_to_review(store):
    store.ingest([listing()])
    store.ingest(
        [
            listing(
                key="https://cs/cc",
                full_name="Cristina Conati",
                email="conati@cs.ubc.ca",
            )
        ]
    )
    result = store.ingest(
        [
            page(email="kevinlb@cs.ubc.ca", orcid=None),
            openalex(),
            page(key="p2", email="conati@cs.ubc.ca"),
        ]
    )
    assert review_reason(store, result) == "identifiers point to different researchers"


def test_unmatched_openalex_author_goes_to_review_not_new_researcher(store):
    result = store.ingest([openalex()])
    assert review_reason(store, result) == (
        "no matching researcher and no department listing"
    )
    assert store.researchers() == []


def test_review_items_are_not_merged_and_not_duplicated(store):
    store.ingest([listing(full_name="Laks V.S. Lakshmanan", email="laks@cs.ubc.ca")])
    before = store.researchers()
    bundle = [page(full_name="L. Lakshmanan", department="Computer Science")]
    store.ingest(bundle)
    store.ingest(bundle)

    assert store.researchers() == before
    assert store.counts()["review_items"] == 1
    assert store.counts()["source_records"] == 1


def test_approve_merges_review_item(store):
    rid = store.ingest(
        [listing(full_name="Laks V.S. Lakshmanan", email="laks@cs.ubc.ca")]
    ).researcher_id
    result = store.ingest(
        [
            page(
                full_name="L. Lakshmanan",
                department="Computer Science",
                interests=["data mining"],
            )
        ]
    )
    (item,) = store.review_items()
    assert item["candidates"] == [rid]

    assert store.approve(result.review_id, rid) == rid
    assert store.review_items() == []
    assert store.get(rid)["interests"] == ["data mining"]
    # after approval the page record is linked, so re-runs merge directly
    again = store.ingest(
        [
            page(
                full_name="L. Lakshmanan",
                department="Computer Science",
                interests=["data mining"],
            )
        ]
    )
    assert (again.status, again.researcher_id) == ("merged", rid)
    assert store.review_items() == []
