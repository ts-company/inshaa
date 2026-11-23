from pydantic import BaseModel

class AddContractor(BaseModel):
    name: str
    code: str

class UpdateContractor(BaseModel):
    name: str = None
    code: str = None