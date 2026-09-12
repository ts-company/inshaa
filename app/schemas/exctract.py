from pydantic import BaseModel, conlist
from decimal import Decimal
from typing import List

class PreviouslyPaid(BaseModel):
    details: str
    amount: Decimal

class AddExtractTax(BaseModel):
    title: str
    rate: Decimal

class AddExtractDeduction(BaseModel):
    title: str
    amount: Decimal

class AddExtractCategoryItem(BaseModel):
    title: str
    unit_type: str
    amount: Decimal
    currency: Decimal
    completion_perc: Decimal

class AddExtractCategoryItems(BaseModel):
    items: List[AddExtractCategoryItem]

class AddExtractCategory(BaseModel):
    title: str
    items: List[AddExtractCategoryItem]

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