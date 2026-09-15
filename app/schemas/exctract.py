from pydantic import BaseModel, conlist, Field
from decimal import Decimal
from typing import List

class PreviouslyPaid(BaseModel):
    details: str
    amount: Decimal

class AddExtractTax(BaseModel):
    title: str
    rate: Decimal = Field(..., max_digits=5, decimal_places=4)

class AddExtractDeduction(BaseModel):
    title: str
    amount: Decimal

class AddExtractCategoryItem(BaseModel):
    title: str
    unit_type: str
    amount: Decimal
    currency: Decimal
    completion_perc: Decimal = Field(..., max_digits=5, decimal_places=4)

class AddExtractCategoryItems(BaseModel):
    items: List[AddExtractCategoryItem]

class AddExtractCategory(BaseModel):
    title: str
    items: List[AddExtractCategoryItem]

class AddExtractCategories(BaseModel):
    categories: List[AddExtractCategory]

class AddExtract(BaseModel):
    project_name: str
    unit_number: int
    contractor_name: str = None
    job_title: str
    categories: List[AddExtractCategory]
    taxes: conlist(AddExtractTax, min_items=1)
    deductions: conlist(AddExtractDeduction, min_items=1)
    payments: List[PreviouslyPaid]


class UpdateAmount(BaseModel):
    amount: Decimal

class UpdateCurrency(BaseModel):
    currency: Decimal

class UpdateCompletion(BaseModel):
    completion: Decimal