from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, DateTime
from app.database import Base

class Extract(Base):
    __tablename__ = "extracts"

    id = Column(Integer, primary_key=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    contract = Column(String(500), nullable=False)
    unit_number = Column(String(100), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractors.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String(500), nullable=True)
    job_title = Column(String(500), nullable=False)
    sub_total = Column(Numeric(12, 2), nullable=False)
    total_taxes = Column(Numeric(12, 2), nullable=False)
    total_deductions = Column(Numeric(12, 2), nullable=False)
    total_payments = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    approved = Column(Boolean, nullable=False)
    approval_date = Column(DateTime, nullable=True)
    parent_id = Column(Integer, ForeignKey("extracts.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)