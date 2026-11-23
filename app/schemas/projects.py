from pydantic import BaseModel


class AddProject(BaseModel):
    name: str
    code: str


class UpdateProject(BaseModel):
    name: str = None
    code: str = None