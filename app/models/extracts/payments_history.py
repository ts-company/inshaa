from sqlalchemy import Column, Integer, ForeignKey, Numeric, String
from app.database import Base

class ExtractPreviouslyPaidHistory(Base):
    __tablename__ = "extract_previously_paid_history"

    id = Column(Integer, primary_key=True, index=True)
    extract_history_id = Column(Integer, ForeignKey("extract_histories.id", ondelete="CASCADE"), nullable=False)
    details = Column(String(500), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)