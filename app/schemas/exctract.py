from pydantic import BaseModel, Field
from decimal import Decimal
from typing import List

class PreviouslyPaid(BaseModel):
    details: str
    amount: Decimal = Field(..., max_digits=12, decimal_places=2)

class AddExtractTax(BaseModel):
    title: str
    rate: Decimal = Field(..., max_digits=5, decimal_places=4)

class AddExtractDeduction(BaseModel):
    title: str
    rate: Decimal = Field(None, max_digits=5, decimal_places=4)
    amount: Decimal = Field(None, max_digits=12, decimal_places=2)

class AddExtractCategoryItem(BaseModel):
    title: str
    unit_type: str
    prev_amount: Decimal
    current_amount: Decimal
    total_amount: Decimal
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
    contractor_name: str
    customer_name: str = None
    job_title: str
    categories: List[AddExtractCategory]
    taxes: List[AddExtractTax]
    deductions: List[AddExtractDeduction]
    payments: List[PreviouslyPaid]


class UpdateAmount(BaseModel):
    amount: Decimal

class UpdateCurrency(BaseModel):
    currency: Decimal

class UpdateCompletion(BaseModel):
    completion: Decimal = Field(..., max_digits=5, decimal_places=4)

class UpdateAccounting(BaseModel):
    taxes: List[AddExtractTax]
    deductions: List[AddExtractDeduction]
    payments: List[PreviouslyPaid]