from pydantic import BaseModel

class AddNotes(BaseModel):
    text: str
