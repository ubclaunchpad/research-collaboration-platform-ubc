# Researcher merge

Combines the department listing, OpenAlex and prof page records for a researcher into one record. Conflicts resolve by fixed rules, so the result doesn't depend on which source ran last. RES-83.

## Field rules

Every field lists the sources allowed to fill it, best first. The first non-empty value wins. Fields not in the table are dropped. The table lives in `FIELD_PRIORITY` in [rules.py](rules.py).

| Fields | Winner, then fallbacks |
|---|---|
| `full_name` | dept listing, OpenAlex, prof page |
| `title`, `email`, `personal_page`, `google_scholar`, `research_groups` | dept listing, prof page |
| `department`, `profile_url`, `research_areas` | dept listing only |
| `papers`, `topics`, `keywords` | OpenAlex only |
| `openalex_id` | OpenAlex, dept listing |
| `orcid` | OpenAlex, prof page, dept listing |
| `interests` | prof page, dept listing |

Each merged record also has:

- `provenance`: which source each field came from
- `conflicts`: values from other sources that disagreed and lost
- `sources`: the source records behind it

## Identity matching

Records come in **bundles**: everything one pipeline run fetched for one professor. A bundle is matched to an existing researcher in this order:

1. One of its records was linked before, meaning the same source and key. This is how re-runs upsert.
2. ORCID or OpenAlex author id.
3. Email, but only if the names are also compatible. Shared addresses such as `head@cs.ubc.ca` exist.
4. Exact name **and** the same department.

These cases go to the **review list** and are not merged:

- The identifiers point at two different researchers.
- The ORCIDs disagree.
- An email matches but the name doesn't.
- The name only loosely matches ("L. Lakshmanan" vs "Laks V.S. Lakshmanan").
- The name matches but the department is different or missing.
- The name matches but the researcher already has a record from that source.
- No match was found and the bundle has no department listing. Only the listing can create a new researcher.

Re-ingesting the same bundle updates its review item instead of adding another. `store.approve(review_id, researcher_id)` merges an item into a researcher; leave out `researcher_id` to create a new one. After approval, later runs merge that record directly.

## Storage

SQLite (`ResearcherStore`) has three tables:

- `researchers`
- `source_records`, keyed by `(source, key)`
- `review_items`

IDs are uuid5 values derived from the data, so a fresh database gives the same IDs. The key is the profile URL for listings, the author id for OpenAlex, and the page URL for prof pages.

## Run on the RES-25 sample

    cd backend
    uv run python -m app.merge.sample ../sample_data/researchers_sample.json --db merged.db --out merged.json

The first run reports `created: 10`. Running it again reports `merged: 10`, and the store and `merged.json` stay identical.

## Use from the pipeline (RES-82)

The `merge` stage builds `SourceRecord`s from `context["listing"]`, `context["api"]` and `context["pages"]`. The `save` stage then calls `store.ingest(bundle)`. Leave out the OpenAlex record when RES-69 flagged the author for `review`.

## Test

    uv run pytest tests/merge
