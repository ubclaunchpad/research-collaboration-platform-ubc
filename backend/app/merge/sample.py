"""Runs the merge on the RES-25 sample (sample_data/researchers_sample.json).

The sample stores each researcher as one row that mixes department listing
fields with OpenAlex papers. Here we split each row back into the records the
pipeline would really produce (one dept_listing record, one openalex record)
and ingest them as one bundle per researcher.

    cd backend
    uv run python -m app.merge.sample ../sample_data/researchers_sample.json \\
        --db merged.db --out merged.json

Running it again on the same --db changes nothing.
"""

import argparse
import json
import sys
from pathlib import Path

from app.merge.rules import DEPT_LISTING, OPENALEX
from app.merge.store import IngestResult, ResearcherStore, SourceRecord

LISTING_FIELDS = (
    "full_name",
    "title",
    "department",
    "email",
    "research_areas",
    "research_groups",
    "profile_url",
    "personal_page",
    "google_scholar",
)


def bundles_from_sample(rows: list[dict]) -> list[list[SourceRecord]]:
    bundles = []
    for row in rows:
        bundle = [
            SourceRecord(
                DEPT_LISTING,
                row["profile_url"],
                {f: row.get(f) for f in LISTING_FIELDS},
            )
        ]
        if row.get("openalex_id"):
            bundle.append(
                SourceRecord(
                    OPENALEX,
                    row["openalex_id"],
                    {
                        "openalex_id": row["openalex_id"],
                        "full_name": row["full_name"],
                        "papers": row.get("papers", []),
                    },
                )
            )
        bundles.append(bundle)
    return bundles


def run(store: ResearcherStore, sample_path: str | Path) -> list[IngestResult]:
    rows = json.loads(Path(sample_path).read_text())
    return [store.ingest(bundle) for bundle in bundles_from_sample(rows)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", help="path to researchers_sample.json")
    parser.add_argument("--db", default="merged.db", help="SQLite file to write")
    parser.add_argument("--out", help="also write the merged records to this JSON")
    args = parser.parse_args(argv)

    with ResearcherStore(args.db) as store:
        results = run(store, args.sample)
        counts = store.counts()
        if args.out:
            Path(args.out).write_text(
                json.dumps(store.export(), indent=2, ensure_ascii=False) + "\n"
            )

    by_status: dict[str, int] = {}
    for result in results:
        by_status[result.status] = by_status.get(result.status, 0) + 1
    print(f"this run: {by_status}")
    print(f"in store: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
