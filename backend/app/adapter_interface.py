import json
import os
from abc import ABC, abstractclassmethod
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
        response: dict,
        source: Literal["Dept_List", "OpenAlex", "Semantic_Scholar", "Prof_Pages"],
    ):

        if source not in ["Dept_List", "OpenAlex", "Semantic_Scholar", "Prof_Pages"]:
            raise ValueError(
                f"source must be one of {['Dept_List', 'OpenAlex', 'Semantic_Scholar', 'Prof_Pages']}"
            )
        response["source"] = source
        os.makedirs("source", exist_ok=True)
        with open(f"source/{source}", mode="w", encoding="utf-8") as f:
            json.dump(response, f, indent=4)
