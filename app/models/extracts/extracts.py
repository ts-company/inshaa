from sqlalchemy import Column, Integer, String, Numeric
from app.database import Base

class Extract(Base):
    __tablename__ = "extracts"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(500), nullable=False)
    unit_number = Column(Integer, nullable=False)
    contractor_name = Column(String(500), nullable=True)
    sub_total = Column(Numeric(12, 2), nullable=False)
    total_taxes = Column(Numeric(12, 2), nullable=False)
    total_deductions = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)