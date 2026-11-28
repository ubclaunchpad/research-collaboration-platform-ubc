"""Matches researchers to their OpenAlex author record and pulls their works."""

import json
import os
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from app.openalex.client import OpenAlexClient

UBC_ID = "https://openalex.org/I141945490"
MAX_WORKS = 100
AUTHOR_FIELDS = (
    "id,display_name,display_name_alternatives,orcid,works_count,"
    "last_known_institutions,affiliations"
)
WORK_FIELDS = (
    "id,title,publication_year,doi,cited_by_count,abstract_inverted_index,"
    "topics,keywords,authorships"
)


def normalize(name: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    for ch in ".,-":
        plain = plain.replace(ch, " ")
    return plain.lower().split()


def names_match(wanted: str, candidate: dict) -> bool:
    # same surname and a matching given name or initial
    want = normalize(wanted)
    for alt in [
        candidate["display_name"],
        *candidate.get("display_name_alternatives", []),
    ]:
        got = normalize(alt)
        if not got or got[-1] != want[-1]:
            continue
        if (
            got[0] == want[0]
            or got[0][0] == want[0][0]
            and min(len(got[0]), len(want[0])) == 1
        ):
            return True
    return False


def at_ubc(candidate: dict) -> bool:
    institutions = candidate.get("last_known_institutions") or []
    affiliations = [a["institution"] for a in candidate.get("affiliations") or []]
    return any(i["id"] == UBC_ID for i in [*institutions, *affiliations])


@dataclass
class Decision:
    status: str
    reason: str
    author: dict | None = None
    candidates: list[dict] = field(default_factory=list)


def decide(name: str, candidates: list[dict], known_id: str | None = None) -> Decision:
    # only match when exactly one same-name candidate is at UBC, flag the rest
    named = [c for c in candidates if names_match(name, c)]
    ubc = [c for c in named if at_ubc(c)]
    if len(ubc) != 1:
        reason = (
            "no same-name author at UBC"
            if not ubc
            else "several same-name authors at UBC"
        )
        return Decision("review", reason, candidates=named)
    pick = ubc[0]
    if known_id and pick["id"] != known_id:
        return Decision(
            "review", f"disagrees with known id {known_id}", candidates=named
        )
    return Decision("matched", "unique same-name author at UBC", pick, named)


def abstract_text(index: dict | None) -> str:
    if not index:
        return ""
    words = [(pos, word) for word, poss in index.items() for pos in poss]
    return " ".join(word for _, word in sorted(words))


def fetch_profile(client: OpenAlexClient, author: dict) -> dict:
    works = client.get(
        "works",
        filter=f"author.id:{author['id']}",
        sort="cited_by_count:desc",
        select=WORK_FIELDS,
        **{"per-page": MAX_WORKS},
    )["results"]
    coauthors: dict[str, dict] = {}
    topics: dict[str, int] = {}
    keywords: dict[str, int] = {}
    for w in works:
        for a in w["authorships"]:
            ref = a["author"]
            if ref["id"] != author["id"]:
                entry = coauthors.setdefault(
                    ref["id"], {"name": ref["display_name"], "papers": 0}
                )
                entry["papers"] += 1
        for t in w.get("topics") or []:
            topics[t["display_name"]] = topics.get(t["display_name"], 0) + 1
        for k in w.get("keywords") or []:
            keywords[k["display_name"]] = keywords.get(k["display_name"], 0) + 1
    return {
        "papers": [
            {
                "title": w["title"],
                "year": w["publication_year"],
                "doi": w["doi"],
                "citations": w["cited_by_count"],
                "abstract": abstract_text(w.get("abstract_inverted_index")),
            }
            for w in works
        ],
        "topics": sorted(topics, key=topics.get, reverse=True),
        "keywords": sorted(keywords, key=keywords.get, reverse=True),
        "coauthors": sorted(
            ({"id": i, **v} for i, v in coauthors.items()), key=lambda c: -c["papers"]
        ),
    }


def match_researcher(client: OpenAlexClient, prof: dict) -> dict:
    result = client.get(
        "authors", search=prof["full_name"], select=AUTHOR_FIELDS, **{"per-page": 15}
    )
    decision = decide(prof["full_name"], result["results"], prof.get("openalex_id"))
    out = {
        "researcher_id": prof["id"],
        "full_name": prof["full_name"],
        "status": decision.status,
        "reason": decision.reason,
    }
    if decision.author:
        out.update(
            author_id=decision.author["id"],
            orcid=decision.author.get("orcid"),
            **fetch_profile(client, decision.author),
        )
    else:
        out["candidates"] = [
            {
                "id": c["id"],
                "name": c["display_name"],
                "orcid": c.get("orcid"),
                "works": c["works_count"],
                "at_ubc": at_ubc(c),
            }
            for c in decision.candidates
        ]
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python -m app.openalex.match RESEARCHERS.json OUT.json")
        return 2
    mailto = os.environ.get("OPENALEX_MAILTO", "")
    if not mailto:
        print("set OPENALEX_MAILTO to a contact email (OpenAlex polite pool)")
        return 2
    client = OpenAlexClient(mailto)
    profs = json.loads(Path(argv[1]).read_text())
    results = [match_researcher(client, p) for p in profs]
    Path(argv[2]).write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    flagged = [r["full_name"] for r in results if r["status"] == "review"]
    print(
        f"{len(results) - len(flagged)} matched, {len(flagged)} flagged for review: {flagged}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
