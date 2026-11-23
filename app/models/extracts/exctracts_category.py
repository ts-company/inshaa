from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base

class ExtractCategory(Base):
    __tablename__ = "extract_categories"

    id = Column(Integer, primary_key=True)
    extract_id = Column(Integer, ForeignKey("extracts.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)