"""
Parser for the Computer Science department's faculty page.
"""

from bs4 import BeautifulSoup

from .base import BaseDepartmentParser, Professor


class CSParser(BaseDepartmentParser):
    def __init__(self):
        super().__init__(
            department_name="Computer Science", base_url="https://www.cs.ubc.ca"
        )

    def parse(self, html_content: str) -> list[Professor]:
        soup = BeautifulSoup(html_content, "html.parser")
        professors = []

        tbodies = soup.select("table.views-table tbody")
        if not tbodies:
            return []

        for tbody in tbodies:
            for row in tbody.find_all("tr"):
                name_tag = row.find("a", class_="contact-content-name")
                if not name_tag:
                    continue

                name = name_tag.get_text(strip=True)
                profile_url = self.resolve_url(name_tag.get("href", ""))

                title_tag = row.find("span", class_="contact-content-job-title")
                title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

                emails = [
                    tag.get_text(strip=True)
                    for tag in row.find_all(
                        "a", href=lambda h: h and h.startswith("mailto:")
                    )
                ]

                lab_names = []
                lab_td = row.find(
                    "td", headers="view-field-research-groups-table-column"
                )
                if lab_td:
                    lab_names = [
                        link.get_text(strip=True) for link in lab_td.find_all("a")
                    ]

                professors.append(
                    Professor(
                        name=name,
                        title=title,
                        department=self.department_name,
                        profile_url=profile_url,
                        emails=emails,
                        lab_names=lab_names,
                    )
                )

        return professors
