from abc import ABC, abstractclassmethod
from pydantic import BaseModel
from typing import Literal
from model import *
import json

class adapter(ABC):
    
    @abstractclassmethod
    def fetch(self, client):
        pass
    
    @abstractclassmethod
    def normalize(self, response) -> Researcher | Lab | Publication:
        pass
    
    def store(self, 
              response: Researcher | Lab | Publication,
              source: Literal["Dept_List", "OpenAlex", "Semantic_Scholar", "Prof_Pages"]):
        try:
            data = response.model_dump()
            data["source"] = source
            print("store successed")
        except e:
            raise ValidationError("response isn't one of Researcher, Lab or Publication from schema")
        
    
    