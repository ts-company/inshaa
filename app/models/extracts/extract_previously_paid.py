from sqlalchemy import Column, Integer, ForeignKey, Numeric, DateTime
from app.database import Base

class ExtractPreviouslyPaid(Base):
    __tablename__ = "extract_previously_paid"

    id = Column(Integer, primary_key=True, index=True)
    extract_id = Column(Integer, ForeignKey("extracts.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)