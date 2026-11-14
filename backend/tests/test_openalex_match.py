import pytest

from app.openalex.client import OpenAlexClient
from app.openalex.match import (
    UBC_ID,
    abstract_text,
    decide,
    fetch_profile,
    match_researcher,
    names_match,
)


def author(id_, name, institution=UBC_ID, alts=()):
    return {
        "id": id_,
        "display_name": name,
        "display_name_alternatives": list(alts),
        "orcid": None,
        "works_count": 10,
        "last_known_institutions": [{"id": institution}],
        "affiliations": [],
    }


def test_names_match_handles_accents_initials_and_surname():
    cand = author("A1", "Mathias Lecuyer")
    assert names_match("Mathias Lécuyer", cand)
    assert names_match("Mathias Lécuyer", author("A2", "M. Lécuyer"))
    assert not names_match("Mathias Lécuyer", author("A3", "Mathias Smith"))


def test_decide_matches_single_ubc_author():
    d = decide(
        "Jeff Clune", [author("A1", "Jeff Clune"), author("A2", "Jeff Clune", "I999")]
    )
    assert d.status == "matched" and d.author["id"] == "A1"


@pytest.mark.parametrize(
    "candidates,reason",
    [
        ([author("A1", "Jeff Clune", "I999")], "no same-name author at UBC"),
        (
            [author("A1", "Jeff Clune"), author("A2", "Jeff Clune")],
            "several same-name authors at UBC",
        ),
        ([], "no same-name author at UBC"),
    ],
)
def test_decide_flags_unsure_cases(candidates, reason):
    d = decide("Jeff Clune", candidates)
    assert d.status == "review" and d.reason == reason and d.author is None


def test_decide_flags_disagreement_with_known_id():
    d = decide("Jeff Clune", [author("A1", "Jeff Clune")], known_id="A9")
    assert d.status == "review"


def test_abstract_text_rebuilds_word_order():
    assert abstract_text({"world": [1], "hello": [0]}) == "hello world"
    assert abstract_text(None) == ""


def work(title, coauthor="A2"):
    return {
        "id": "W" + title,
        "title": title,
        "publication_year": 2020,
        "doi": None,
        "cited_by_count": 5,
        "abstract_inverted_index": {"abstract": [0]},
        "topics": [{"display_name": "Machine learning"}],
        "keywords": [{"display_name": "bandits"}],
        "authorships": [
            {"author": {"id": "A1", "display_name": "Jeff Clune"}},
            {"author": {"id": coauthor, "display_name": "Co Author"}},
        ],
    }


def fake_client(routes):
    def fetch(url):
        for fragment, payload in routes.items():
            if fragment in url:
                return payload
        raise AssertionError(url)

    return OpenAlexClient("me@example.com", fetch=fetch)


def test_fetch_profile_collects_papers_topics_coauthors():
    client = fake_client(
        {"/works": {"results": [work("a"), work("b")], "meta": {"next_cursor": None}}}
    )
    profile = fetch_profile(client, author("A1", "Jeff Clune"))
    assert [p["title"] for p in profile["papers"]] == ["a", "b"]
    assert profile["topics"] == ["Machine learning"]
    assert profile["coauthors"] == [{"id": "A2", "name": "Co Author", "papers": 2}]


def test_match_researcher_flags_without_fetching_works():
    client = fake_client(
        {"/authors": {"results": [author("A1", "Jeff Clune", "I999")]}}
    )
    out = match_researcher(client, {"id": 7, "full_name": "Jeff Clune"})
    assert out["status"] == "review" and out["candidates"][0]["at_ubc"] is False


def test_client_requires_contact_email():
    with pytest.raises(ValueError):
        OpenAlexClient("")


def test_client_sends_mailto():
    seen = []
    client = OpenAlexClient("me@example.com", fetch=lambda u: seen.append(u) or {})
    client.get("authors", search="x")
    assert "mailto=me%40example.com" in seen[0]
