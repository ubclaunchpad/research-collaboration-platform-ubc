"""Which source wins for each field.

Every field of the merged researcher record lists the sources allowed to fill
it, best first. The first source with a non-empty value wins. Sources not in
the list are ignored for that field, and fields not in the table are dropped.
The order records arrive in never matters.

To change who wins a field, edit FIELD_PRIORITY. tests/merge/test_rules.py
pins the important ones.
"""

from dataclasses import dataclass, field

DEPT_LISTING = "dept_listing"
OPENALEX = "openalex"
PROF_PAGE = "prof_page"

SOURCES: tuple[str, ...] = (DEPT_LISTING, OPENALEX, PROF_PAGE)

FIELD_PRIORITY: dict[str, tuple[str, ...]] = {
    # Who they are: the department listing is the official roster.
    "full_name": (DEPT_LISTING, OPENALEX, PROF_PAGE),
    "title": (DEPT_LISTING, PROF_PAGE),
    "department": (DEPT_LISTING,),
    "email": (DEPT_LISTING, PROF_PAGE),
    "profile_url": (DEPT_LISTING,),
    "personal_page": (DEPT_LISTING, PROF_PAGE),
    "google_scholar": (DEPT_LISTING, PROF_PAGE),
    "research_areas": (DEPT_LISTING,),
    "research_groups": (DEPT_LISTING, PROF_PAGE),
    # What they publish: OpenAlex.
    "openalex_id": (OPENALEX, DEPT_LISTING),
    "orcid": (OPENALEX, PROF_PAGE, DEPT_LISTING),
    "papers": (OPENALEX,),
    "topics": (OPENALEX,),
    "keywords": (OPENALEX,),
    # What they say they work on: their own page.
    "interests": (PROF_PAGE, DEPT_LISTING),
}

# Only these sources may create a new researcher. A paper author or a web page
# that doesn't match anyone we know goes to review instead.
CREATES_RESEARCHER: frozenset[str] = frozenset({DEPT_LISTING})


def is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list | tuple | dict | set):
        return len(value) == 0
    return False


def _same(a: object, b: object) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().casefold() == b.strip().casefold()
    return a == b


@dataclass
class Resolved:
    record: dict[str, object] = field(default_factory=dict)
    # field -> source that supplied the winning value
    provenance: dict[str, str] = field(default_factory=dict)
    # field -> values from other sources that disagreed and lost
    conflicts: dict[str, list[dict[str, object]]] = field(default_factory=dict)


def resolve(records: list[tuple[str, str, dict]]) -> Resolved:
    """Build one record from (source, key, fields) tuples using FIELD_PRIORITY.

    If one researcher has several records from the same source, the one with
    the smallest key wins ties, so the result is always the same.
    """
    by_source: dict[str, list[dict]] = {}
    for source, _key, fields in sorted(records, key=lambda r: (r[0], r[1])):
        by_source.setdefault(source, []).append(fields)

    out = Resolved()
    for name, priority in FIELD_PRIORITY.items():
        candidates = [
            (source, fields[name])
            for source in priority
            for fields in by_source.get(source, [])
            if not is_empty(fields.get(name))
        ]
        if not candidates:
            continue
        winner_source, winner = candidates[0]
        out.record[name] = winner
        out.provenance[name] = winner_source
        losers = [
            {"source": s, "value": v} for s, v in candidates[1:] if not _same(v, winner)
        ]
        if losers:
            out.conflicts[name] = losers
    return out
