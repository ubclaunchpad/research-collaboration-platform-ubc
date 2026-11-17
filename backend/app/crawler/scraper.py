"""
Orchestrates the scraping process for a given URL and saves the extracted data.
"""

import json
from pathlib import Path

import requests
from parsers.base import BaseDepartmentParser
from parsers.cs_parser import CSParser

PARSERS_REGISTRY: dict[str, BaseDepartmentParser] = {
    "cs": CSParser(),
}

BASE_DIR = Path(__file__).resolve().parent


def get_html(url: str, dept_id: str, force_refresh: bool = False) -> str:
    """Fetches HTML content from a URL with caching."""

    cache_dir = BASE_DIR / "data" / "raw"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{dept_id}_raw.html"

    if cache_file.exists() and not force_refresh:
        print(f"Loading {dept_id} from local cache...")
        return cache_file.read_text(encoding="utf-8")

    print(f"Fetching {dept_id} from live URL...")
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()

    html = response.text
    cache_file.write_text(html, encoding="utf-8")
    return html


def export_to_json(professors: list, dept_id: str):
    """Exports structured data to JSON."""
    out_dir = BASE_DIR / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{dept_id}_professors.json"

    if not professors:
        print("No data to write.")
        return

    data = [prof.to_dict() for prof in professors]

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(professors)} records to {out_file}")


def main():
    pilot_dept = "cs"
    pilot_url = "https://www.cs.ubc.ca/people/faculty"

    # set force_refresh = True to refetch the HTML from the live URL instead of using cached data
    html_content = get_html(pilot_url, pilot_dept, force_refresh=False)

    parser = PARSERS_REGISTRY.get(pilot_dept)
    if not parser:
        raise ValueError(f"No parser registered for {pilot_dept}")

    professors = parser.parse(html_content)

    export_to_json(professors, pilot_dept)


if __name__ == "__main__":
    main()
