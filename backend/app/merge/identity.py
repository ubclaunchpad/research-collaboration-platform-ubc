"""Decides which existing researcher (if any) a bundle of source records is.

Checks run in this order:

1. A record in the bundle is already linked to a researcher (same source and
   key as a previous run). This is what makes re-runs upsert.
2. Strong identifiers: ORCID, OpenAlex author id, email.
3. Name + department.

Anything that isn't clear goes to review instead of being merged:
- identifiers that point at two different researchers
- an ORCID that disagrees with the matched researcher's ORCID
- an email match where the names don't match (shared addresses such as
  head@cs.ubc.ca)
- a name that only loosely matches ("Laks Lakshmanan" vs "Laks V.S. Lakshmanan")
- a name match in a different or unknown department
- more than one researcher with the same name
"""

import re
import unicodedata
from dataclasses import dataclass, field

_ORCID_RE = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", re.IGNORECASE)


def normalize_email(value: object) -> str | None:
    if not isinstance(value, str) or "@" not in value:
        return None
    return value.strip().lower()


def normalize_orcid(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    found = _ORCID_RE.search(value)
    return found.group(1).upper() if found else None


def normalize_openalex(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().rstrip("/").rsplit("/", 1)[-1].upper()


_HONORIFICS = frozenset({"dr", "prof", "professor", "mr", "mrs", "ms"})


def name_tokens(value: object) -> tuple[str, ...]:
    """ "Dr. Mathias Lécuyer" -> ("mathias", "lecuyer")."""
    if not isinstance(value, str):
        return ()
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    plain = re.sub(r"[^a-zA-Z\s]", " ", plain)
    tokens = plain.lower().split()
    while tokens and tokens[0] in _HONORIFICS:
        tokens.pop(0)
    return tuple(tokens)


def normalize_department(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(value.lower().replace("&", "and").split())


def compare_names(a: tuple[str, ...], b: tuple[str, ...]) -> str | None:
    """Return "exact", "loose" or None.

    loose means same surname and the first names agree (equal or one is an
    initial), e.g. "K. Leyton-Brown" vs "Kevin Leyton-Brown".
    """
    if not a or not b:
        return None
    if a == b:
        return "exact"
    if a[-1] != b[-1]:
        return None
    first_a, first_b = a[0], b[0]
    if first_a == first_b or (
        min(len(first_a), len(first_b)) == 1 and first_a[0] == first_b[0]
    ):
        return "loose"
    return None


@dataclass
class Identity:
    """Everything about a person that helps tell them apart."""

    keys: set[tuple[str, str]] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    orcids: set[str] = field(default_factory=set)
    openalex_ids: set[str] = field(default_factory=set)
    emails: set[str] = field(default_factory=set)
    names: set[tuple[str, ...]] = field(default_factory=set)
    departments: set[str] = field(default_factory=set)

    def add(self, source: str, key: str, fields: dict) -> None:
        self.keys.add((source, key))
        self.sources.add(source)
        for value, normalize, bucket in (
            (fields.get("orcid"), normalize_orcid, self.orcids),
            (fields.get("openalex_id"), normalize_openalex, self.openalex_ids),
            (fields.get("email"), normalize_email, self.emails),
            (fields.get("department"), normalize_department, self.departments),
        ):
            normalized = normalize(value)
            if normalized:
                bucket.add(normalized)
        tokens = name_tokens(fields.get("full_name"))
        if tokens:
            self.names.add(tokens)

    @classmethod
    def of(cls, records: list[tuple[str, str, dict]]) -> Identity:
        identity = cls()
        for source, key, fields in records:
            identity.add(source, key, fields)
        return identity

    def name_match(self, other: Identity) -> str | None:
        results = {compare_names(a, b) for a in self.names for b in other.names}
        if "exact" in results:
            return "exact"
        if "loose" in results:
            return "loose"
        return None


@dataclass
class Decision:
    action: str  # "link", "new" or "review"
    reason: str
    researcher_id: str | None = None
    candidates: list[str] = field(default_factory=list)


def _orcid_conflict(a: Identity, b: Identity) -> bool:
    return bool(a.orcids and b.orcids and not (a.orcids & b.orcids))


def decide(bundle: Identity, researchers: dict[str, Identity]) -> Decision:
    if len(bundle.orcids) > 1:
        return Decision("review", "records in this bundle disagree on ORCID")

    linked = {r for r, c in researchers.items() if bundle.keys & c.keys}
    by_id = {
        r
        for r, c in researchers.items()
        if bundle.orcids & c.orcids or bundle.openalex_ids & c.openalex_ids
    }
    by_email = {r for r, c in researchers.items() if bundle.emails & c.emails}

    hits = linked | by_id | by_email
    if len(hits) > 1:
        return Decision(
            "review",
            "identifiers point to different researchers",
            candidates=sorted(hits),
        )
    if hits:
        (rid,) = hits
        match = researchers[rid]
        if _orcid_conflict(bundle, match):
            return Decision("review", "ORCID differs", candidates=[rid])
        if rid in linked:
            return Decision("link", "same source record as before", rid)
        if rid in by_id:
            return Decision("link", "ORCID or OpenAlex id matches", rid)
        if not bundle.name_match(match):
            return Decision(
                "review", "email matches but name does not", candidates=[rid]
            )
        return Decision("link", "email matches", rid)

    exact: list[str] = []
    unsure: list[str] = []
    for rid, match in sorted(researchers.items()):
        name = bundle.name_match(match)
        if not name:
            continue
        same_dept = bool(bundle.departments & match.departments)
        if name == "exact" and same_dept and not _orcid_conflict(bundle, match):
            exact.append(rid)
        else:
            unsure.append(rid)

    if len(exact) == 1 and not unsure:
        rid = exact[0]
        overlap = bundle.sources & researchers[rid].sources
        if overlap:
            # Same name, same department, but they already have a record from
            # this source under a different key: maybe two different people.
            return Decision(
                "review",
                f"name matches but researcher already has a "
                f"{sorted(overlap)[0]} record",
                candidates=[rid],
            )
        return Decision("link", "name and department match", rid)
    if exact or unsure:
        return Decision(
            "review", "low-confidence name match", candidates=sorted(exact + unsure)
        )
    return Decision("new", "no matching researcher")
