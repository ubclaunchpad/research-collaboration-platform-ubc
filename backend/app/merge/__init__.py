"""Merges department listing, OpenAlex and prof page data into one researcher.

- rules.py: which source wins each field
- identity.py: which existing researcher a new bundle of records belongs to
- store.py: upserts, the review list, and approving review items
- sample.py: runs it all on the RES-25 sample

See README.md in this folder.
"""

from app.merge.rules import FIELD_PRIORITY, resolve
from app.merge.store import IngestResult, ResearcherStore, SourceRecord

__all__ = [
    "FIELD_PRIORITY",
    "IngestResult",
    "ResearcherStore",
    "SourceRecord",
    "resolve",
]
