from sqlalchemy import Column, Integer, String, Float, ForeignKey, Numeric
from app.database import Base

class ExtractDeductionHistory(Base):
    __tablename__ = "extract_deduction_histories"

    id = Column(Integer, primary_key=True, index=True)
    extract_history_id = Column(Integer, ForeignKey("extract_histories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)