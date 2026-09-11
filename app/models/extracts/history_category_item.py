from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from app.database import Base

class ExtractCategoryItemHistory(Base):
    __tablename__ = "extract_category_item_histories"

    id = Column(Integer, primary_key=True, index=True)
    extract_category_history_id = Column(Integer, ForeignKey("extract_category_histories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    unit_type = Column(String(50), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(Numeric(12, 2), nullable=False)
    completion_perc = Column(Numeric(5, 4), nullable=False)
    total = Column(Numeric(14, 2), nullable=False)