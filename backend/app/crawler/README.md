# Faculty Data Crawler

This directory contains a scraper and parsers for different department faculty sites. 
`scraper.py` fetches or loads the page HTML, passes it to a department
parser, and writes the parsed faculty records as JSON.

## Run the scraper

The backend manages Python dependencies with `uv`. From the backend directory,
install the project dependencies if you have not already:

```sh
uv sync
```

Then run the scraper:

```sh
cd backend/app/crawler
uv run python scraper.py
```

The first run fetches the CS faculty page and saves its HTML to
`data/raw/cs_raw.html`. Later runs use that cached HTML. To fetch the live page
again, change `force_refresh=False` to `force_refresh=True` in `main()` in
`scraper.py`, then rerun the command. The pilot department source URL and department ID are currently hardcoded in `main()`.

## `scraper.py`

`PARSERS_REGISTRY` maps department IDs to parser instances. It currently
registers `cs` with `CSParser`; add a parser here before selecting another
department in `main()`.

| Function | What it does |
|---|---|
| `get_html(url, dept_id, force_refresh=False)` | Reads `data/raw/{dept_id}_raw.html` if it exists and refresh is off. Otherwise makes an HTTP GET with a browser-style User-Agent, raises for an unsuccessful response, caches the response body as UTF-8 HTML, and returns it. |
| `export_to_json(professors, dept_id)` | Creates `data/output/`, converts each `Professor` to a dictionary with `to_dict()`, and writes an indented UTF-8 JSON array to `{dept_id}_professors.json`. If the list is empty, it prints a message and does not write a file. |
| `main()` | Sets the pilot department and URL, gets the HTML, looks up the parser, parses the page, and exports the results. It raises `ValueError` if the selected department has no registered parser. |

## `parsers/cs_parser.py`

`CSParser` implements the shared `BaseDepartmentParser` interface for UBC
Computer Science:

- `__init__()` sets the department name to `Computer Science` and the base URL
  to `https://www.cs.ubc.ca`.
- `parse(html_content)` parses HTML with Beautiful Soup. It looks for rows
  inside `table.views-table tbody`; if none are found, it returns an empty
  list. For each row, it requires a link with class
  `contact-content-name`, and extracts its text as the faculty name.
- The profile link is resolved against the CS base URL. The parser reads the
  title from `contact-content-job-title` (or uses `Unknown Title` when absent),
  collects the visible text of `mailto:` links as emails, and collects links
  from the research-groups table cell as lab names.
- Each matching row becomes a `Professor` with the department set to
  `Computer Science`; rows without a recognized name link are skipped.

The parser depends on the page retaining those HTML classes and table
structure. If the source page changes, the selectors may need to be updated.

## Shared parser types

`parsers/base.py` defines the pieces used by department parsers:

- `Professor` is the record type. `to_dict()` converts its dataclass fields to a
  dictionary for JSON export; `emails` and `lab_names` default to empty lists.
- `BaseDepartmentParser` is the abstract parser interface. Subclasses implement
  `parse(html_content)`.
- `resolve_url(raw_url)` joins a page-relative profile link to the parser's
  base URL.