"""
Base parser class for all department sites.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from urllib.parse import urljoin


@dataclass
class Professor:
    name: str
    title: str
    department: str
    profile_url: str
    emails: list[str] = field(default_factory=list)
    lab_names: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class BaseDepartmentParser(ABC):
    def __init__(self, department_name: str, base_url: str):
        self.department_name = department_name
        self.base_url = base_url

    @abstractmethod
    def parse(self, html_content: str) -> list[Professor]:
        pass

    # Shared helper method available to all child parsers
    def resolve_url(self, raw_url: str) -> str:
        return urljoin(self.base_url, raw_url)
