# Sample data

10 real UBC Computer Science researchers, with three well-cited papers each. It is a rough sample for testing Matching, Backend and Frontend. It is not clean or complete.

Profile fields are facts from the public UBC CS faculty pages (https://www.cs.ubc.ca/people/faculty). Emails, research areas and Google Scholar links are left out on purpose, since the repo is public and we don't copy text from UBC pages. Papers come from OpenAlex (https://openalex.org), matched by name and UBC affiliation, because the UBC pages do not list papers. Pulled on 2026-10-24.

## Files

- `researchers.csv`: one row per researcher
- `papers.csv`: one row per paper, linked to a researcher by `researcher_id`
- `researchers_sample.json`: the same data in one file, with papers nested under each researcher

## researchers.csv

| Column | Meaning |
|---|---|
| `researcher_id` | Row id used only in this sample, links to `papers.csv` |
| `full_name` | Name as shown on the UBC CS page |
| `title` | Job title on the UBC CS page |
| `department` | Always Computer Science in this sample |
| `research_groups` | Research groups listed on the page, separated by `; ` (can be empty) |
| `profile_url` | UBC CS profile page |
| `personal_page` | Researcher's own site, empty if none is listed |
| `openalex_id` | Author id in OpenAlex |

## papers.csv

| Column | Meaning |
|---|---|
| `researcher_id` | Which researcher wrote it (see `researchers.csv`) |
| `title` | Paper title |
| `year` | Publication year |
| `doi` | DOI link, empty if OpenAlex has none |
| `citations` | Citation count in OpenAlex when pulled |

## Known rough edges

- Papers are the 3 most cited per person, so they skew old. They are not a list of current work.
- For research topics, use OpenAlex topics (see `app/openalex`), not UBC page text.
