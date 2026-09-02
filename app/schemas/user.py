from pydantic import BaseModel

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str
    password: str
    role: str

class UserLogin(BaseModel):
    username: str
    password: str

class EditUser(BaseModel):
    username: str = None
    password: str = None