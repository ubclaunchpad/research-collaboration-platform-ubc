from abc import ABC, abstractclassmethod
from pathlib import Path
from typing import Literal


class adapter(ABC):
    @abstractclassmethod
    async def fetch(self, client):
        pass

    @abstractclassmethod
    def normalize(self, response):
        pass

    def store(
        self,
        response: bytes,
        source: Literal["Dept_List", "OpenAlex", "Semantic_Scholar", "Prof_Pages"],
    ):

        if source not in ["Dept_List", "OpenAlex", "Semantic_Scholar", "Prof_Pages"]:
            raise ValueError(
                f"source must be one of {['Dept_List', 'OpenAlex', 'Semantic_Scholar', 'Prof_Pages']}"
            )
        directory = Path("source") / source
        directory.mkdir(parents=True, exist_ok=True)

        file_path = directory / source
        file_path.write_bytes(response)
