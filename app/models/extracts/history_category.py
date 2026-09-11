from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base

class ExtractCategoryHistory(Base):
    __tablename__ = "extract_category_histories"

    id = Column(Integer, primary_key=True, index=True)
    extract_history_id = Column(Integer, ForeignKey("extract_histories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)