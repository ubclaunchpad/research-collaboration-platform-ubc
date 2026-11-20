"""Stores merged researchers, the source records behind them, and the review list.

Tables (SQLite, same approach as the pipeline job store):

- source_records: one row per (source, key), e.g. ("dept_listing", profile_url).
  Re-ingesting the same record updates the row instead of adding one.
- researchers: one merged record per person, rebuilt from their source
  records with rules.resolve every time one of them changes.
- review_items: bundles we weren't sure about. They are NOT merged. One row
  per bundle, so re-runs don't pile up duplicates. Use approve() to merge one
  by hand.

IDs are derived from the data (uuid5), so a fresh database gives the same IDs
every time.
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.merge.identity import Decision, Identity, decide
from app.merge.rules import CREATES_RESEARCHER, SOURCES, resolve

_NAMESPACE = uuid.UUID("5b0c3f8e-2d1a-4c6b-9f7e-1a2b3c4d5e6f")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS researchers (
    id TEXT PRIMARY KEY,
    record TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_records (
    source TEXT NOT NULL,
    key TEXT NOT NULL,
    researcher_id TEXT NOT NULL REFERENCES researchers(id),
    fields TEXT NOT NULL,
    PRIMARY KEY (source, key)
);
CREATE TABLE IF NOT EXISTS review_items (
    id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    candidates TEXT NOT NULL,
    bundle TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class SourceRecord:
    """What one source said about one person.

    key identifies the record within its source and must stay the same across
    runs: profile URL for listings, author id for OpenAlex, page URL for pages.
    """

    source: str
    key: str
    fields: dict

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}, got {self.source!r}")
        if not self.key:
            raise ValueError("key must not be empty")

    def as_tuple(self) -> tuple[str, str, dict]:
        return (self.source, self.key, self.fields)


@dataclass
class IngestResult:
    status: str  # "created", "merged" or "review"
    reason: str
    researcher_id: str | None = None
    review_id: str | None = None


def _dumps(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _bundle_id(bundle: list[SourceRecord]) -> str:
    keys = sorted(f"{r.source}:{r.key}" for r in bundle)
    return str(uuid.uuid5(_NAMESPACE, "\n".join(keys)))


def _new_researcher_id(bundle: list[SourceRecord]) -> str:
    rank = {s: i for i, s in enumerate(SOURCES)}
    first = min(bundle, key=lambda r: (rank[r.source], r.key))
    return str(uuid.uuid5(_NAMESPACE, f"{first.source}:{first.key}"))


class ResearcherStore:
    def __init__(self, db_path: str | Path = "researchers.db") -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> ResearcherStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ---- writing -----------------------------------------------------------

    def ingest(self, bundle: list[SourceRecord]) -> IngestResult:
        """Merge records that describe one person (e.g. one pipeline run)."""
        if not bundle:
            raise ValueError("bundle is empty")
        decision = decide(
            Identity.of([r.as_tuple() for r in bundle]), self._identities()
        )
        if decision.action == "new" and not CREATES_RESEARCHER & {
            r.source for r in bundle
        }:
            decision = Decision(
                "review", "no matching researcher and no department listing"
            )
        return self._apply(bundle, decision)

    def approve(self, review_id: str, researcher_id: str | None = None) -> str:
        """Merge a review item by hand.

        Pass researcher_id to merge it into that researcher, or leave it out to
        create a new researcher. Returns the researcher id.
        """
        row = self._conn.execute(
            "SELECT bundle FROM review_items WHERE id = ?", (review_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no review item {review_id}")
        bundle = [SourceRecord(**r) for r in json.loads(row["bundle"])]
        if researcher_id is None:
            decision = Decision("new", "approved as new researcher")
        else:
            if self.get(researcher_id) is None:
                raise KeyError(f"no researcher {researcher_id}")
            decision = Decision("link", "approved by reviewer", researcher_id)
        result = self._apply(bundle, decision)
        assert result.researcher_id is not None
        return result.researcher_id

    def _apply(self, bundle: list[SourceRecord], decision: Decision) -> IngestResult:
        review_id = _bundle_id(bundle)
        with self._conn:
            if decision.action == "review":
                self._conn.execute(
                    """
                    INSERT INTO review_items (id, reason, candidates, bundle)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        reason = excluded.reason,
                        candidates = excluded.candidates,
                        bundle = excluded.bundle
                    """,
                    (
                        review_id,
                        decision.reason,
                        _dumps(decision.candidates),
                        _dumps([r.__dict__ for r in bundle]),
                    ),
                )
                return IngestResult("review", decision.reason, review_id=review_id)

            if decision.action == "new":
                rid = _new_researcher_id(bundle)
                status = "created"
                self._conn.execute(
                    "INSERT OR IGNORE INTO researchers (id, record) VALUES (?, '{}')",
                    (rid,),
                )
            else:
                rid = decision.researcher_id
                status = "merged"

            # Records may move between researchers (e.g. after approve()), so
            # rebuild every researcher that loses one too.
            touched = {rid}
            for record in bundle:
                old = self._conn.execute(
                    "SELECT researcher_id FROM source_records "
                    "WHERE source = ? AND key = ?",
                    (record.source, record.key),
                ).fetchone()
                if old:
                    touched.add(old["researcher_id"])
                self._conn.execute(
                    """
                    INSERT INTO source_records (source, key, researcher_id, fields)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(source, key) DO UPDATE SET
                        researcher_id = excluded.researcher_id,
                        fields = excluded.fields
                    """,
                    (record.source, record.key, rid, _dumps(record.fields)),
                )
            self._conn.execute("DELETE FROM review_items WHERE id = ?", (review_id,))
            for researcher in sorted(touched):
                self._rebuild(researcher)
        return IngestResult(status, decision.reason, researcher_id=rid)

    def _rebuild(self, researcher_id: str) -> None:
        rows = self._conn.execute(
            "SELECT source, key, fields FROM source_records WHERE researcher_id = ?",
            (researcher_id,),
        ).fetchall()
        if not rows:
            self._conn.execute("DELETE FROM researchers WHERE id = ?", (researcher_id,))
            return
        resolved = resolve(
            [(r["source"], r["key"], json.loads(r["fields"])) for r in rows]
        )
        record = {
            **resolved.record,
            "provenance": resolved.provenance,
            "conflicts": resolved.conflicts,
            "sources": sorted(f"{r['source']}:{r['key']}" for r in rows),
        }
        self._conn.execute(
            "UPDATE researchers SET record = ? WHERE id = ?",
            (_dumps(record), researcher_id),
        )

    # ---- reading -----------------------------------------------------------

    def _identities(self) -> dict[str, Identity]:
        identities: dict[str, Identity] = {}
        for row in self._conn.execute(
            "SELECT researcher_id, source, key, fields FROM source_records"
        ):
            identities.setdefault(row["researcher_id"], Identity()).add(
                row["source"], row["key"], json.loads(row["fields"])
            )
        return identities

    def get(self, researcher_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT record FROM researchers WHERE id = ?", (researcher_id,)
        ).fetchone()
        return {"id": researcher_id, **json.loads(row["record"])} if row else None

    def researchers(self) -> list[dict]:
        rows = self._conn.execute("SELECT id, record FROM researchers ORDER BY id")
        return [{"id": r["id"], **json.loads(r["record"])} for r in rows]

    def review_items(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM review_items ORDER BY id")
        return [
            {
                "id": r["id"],
                "reason": r["reason"],
                "candidates": json.loads(r["candidates"]),
                "bundle": json.loads(r["bundle"]),
            }
            for r in rows
        ]

    def counts(self) -> dict[str, int]:
        return {
            table: self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("researchers", "source_records", "review_items")
        }

    def export(self) -> dict:
        """Everything in the store, in a stable order. Handy for diffs."""
        return {"researchers": self.researchers(), "review": self.review_items()}
