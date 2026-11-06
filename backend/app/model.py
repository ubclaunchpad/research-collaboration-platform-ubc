from pydantic import BaseModel

class Researcher(BaseModel):
    name: str
    department: str | None = None      # a Enum is usually preferred, but I am not too sure of the format
    profile_url: str | None = None
    email: str | None = None
    phone: str | None = None
    lab: list[Lab] | None = None
    research_interest: list[str] | None = None
    research_history: list[Publication | str] | None = None
    
class Lab(BaseModel):
    name: str
    contact: str
    lab_web: str | None = None
    department: str | None = None
    research_focus: list[str]
    leaders: list[str] | None = None
    ongoing_projects: list[str] | None = None
    
    
class Publication(BaseModel):
    title: str
    authors: list[str]
    publish_year: int | None = None
    research_keywords: list[str] = None
    
