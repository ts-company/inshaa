from pydantic import BaseModel
from typing import List

class SubCategory(BaseModel):
    text: str

class AddCategory(BaseModel):
    title: str
    sub_categories: List[SubCategory]

class EditCategory(BaseModel):
    sub_categories: List[SubCategory]