from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from app.database import Base

class ExtractTaxesHistory(Base):
    __tablename__ = "extract_tax_histories"

    id = Column(Integer, primary_key=True, index=True)
    extract_history_id = Column(Integer, ForeignKey("extract_histories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 4), nullable=False)