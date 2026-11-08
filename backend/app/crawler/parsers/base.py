"""
Base parser class for all department sites.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional

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