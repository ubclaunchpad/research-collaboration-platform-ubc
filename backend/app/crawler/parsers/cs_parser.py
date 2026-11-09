"""
Parser for the Computer Science department's faculty page.
"""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import Professor

# Base URL to resolve relative profile links
BASE_URL = "https://www.cs.ubc.ca"


def parse_cs_department(html_content: str) -> list[Professor]:
    soup = BeautifulSoup(html_content, "html.parser")
    professors = []

    table_bodies = soup.select("table.views-table tbody")

    if not table_bodies:
        return []

    for table_body in table_bodies:
        rows = table_body.find_all("tr")

        for row in rows:
            # 1. Name & Profile URL
            name_tag = row.find("a", class_="contact-content-name")
            if not name_tag:
                continue  # Skip empty or malformed rows

            name = name_tag.get_text(strip=True)
            raw_url = name_tag.get("href", "")
            profile_url = urljoin(BASE_URL, raw_url)

            # 2. Title
            title_tag = row.find("span", class_="contact-content-job-title")
            title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

            # 3. Emails
            emails = []
            email_tags = row.find_all(
                "a", href=lambda href: href and href.startswith("mailto:")
            )
            if email_tags:
                # Extract text from every mailto link into a list
                emails = [tag.get_text(strip=True) for tag in email_tags]

            # 4. Lab Name (Research Groups)
            lab_names = []
            lab_td = row.find("td", headers="view-field-research-groups-table-column")
            if lab_td:
                # Find all anchor tags inside the cell and extract their text into a list
                lab_links = lab_td.find_all("a")
                if lab_links:
                    lab_names = [link.get_text(strip=True) for link in lab_links]

            prof = Professor(
                name=name,
                title=title,
                department="Computer Science",
                profile_url=profile_url,
                emails=emails,
                lab_names=lab_names,
            )
            professors.append(prof)

    return professors
