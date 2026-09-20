from pydantic import BaseModel

class CandidateApply(BaseModel):
    name: str
    email: str
    phone_number: str
    age: int