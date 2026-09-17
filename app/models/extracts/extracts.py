from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey
from app.database import Base

class Extract(Base):
    __tablename__ = "extracts"

    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_name = Column(String(500), nullable=False)
    unit_number = Column(Integer, nullable=False)
    contractor_name = Column(String(500), nullable=False)
    customer_name = Column(String(500), nullable=True)
    job_title = Column(String(500), nullable=False)
    sub_total = Column(Numeric(12, 2), nullable=False)
    total_taxes = Column(Numeric(12, 2), nullable=False)
    total_deductions = Column(Numeric(12, 2), nullable=False)
    total_payments = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    approved = Column(Boolean, nullable=False)