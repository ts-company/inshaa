from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from app.database import Base

class ExtractHistory(Base):
    __tablename__ = "extract_histories"

    id = Column(Integer, primary_key=True, index=True)
    extract_id = Column(Integer, ForeignKey("extracts.id", ondelete="CASCADE"), nullable=False)
    updated_at = Column(DateTime, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project_name = Column(String(500), nullable=False)
    contract = Column(String(500), nullable=False)
    unit_number = Column(String(100), nullable=False)
    contractor_name = Column(String(500), nullable=False)
    customer_name = Column(String(500), nullable=True)
    job_title = Column(String(500), nullable=False)
    sub_total = Column(Numeric(12, 2), nullable=False)
    total_taxes = Column(Numeric(12, 2), nullable=False)
    total_deductions = Column(Numeric(12, 2), nullable=False)
    total_payments = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)