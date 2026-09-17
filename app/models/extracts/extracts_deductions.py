from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Boolean
from app.database import Base

class ExtractDeduction(Base):
    __tablename__ = "extract_deductions"

    id = Column(Integer, primary_key=True, index=True)
    extract_id = Column(Integer, ForeignKey("extracts.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 4), nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)