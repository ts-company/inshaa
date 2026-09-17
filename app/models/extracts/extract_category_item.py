from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from app.database import Base

class ExtractCategoryItem(Base):
    __tablename__ = "extract_category_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("extract_categories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    unit_type = Column(String(50), nullable=False)
    prev_amount = Column(Numeric(9, 2), nullable=False)
    current_amount = Column(Numeric(9, 2), nullable=False)
    total_amount = Column(Numeric(9, 2), nullable=False)
    currency = Column(Numeric(12, 2), nullable=False)
    completion_perc = Column(Numeric(5, 4), nullable=False)
    total = Column(Numeric(14, 2), nullable=False)