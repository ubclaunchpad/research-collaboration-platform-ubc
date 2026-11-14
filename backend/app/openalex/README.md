# OpenAlex matcher

Matches each researcher to their OpenAlex author record and pulls their papers, topics, keywords and co-authors. RES-69.

## Matching rule

A researcher is matched only when exactly one author with the same name is affiliated with UBC. Anything else is flagged `review` with a reason: no UBC author, several UBC authors, or a result that disagrees with an `openalex_id` already in the input. Nothing is guessed.

## Run

OpenAlex asks for a contact email (the polite pool), so it is read from the environment and never stored in the repo.

    cd backend
    export OPENALEX_MAILTO=you@example.com
    uv run python -m app.openalex.match ../sample_data/researchers_sample.json matches.json

Each output row has `status`, `reason`, and for matches `author_id`, `orcid`, `papers` (title, year, DOI, abstract, citations, the 100 most cited, one request, since paging past page 1 needs an OpenAlex API key), `topics`, `keywords` and `coauthors`.

## Test

    uv run pytest tests/test_openalex_match.py
