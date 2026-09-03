from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base

class CvSubCategory(Base):
    __tablename__ = "cv_sub_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("cv_categories.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(200), nullable=False)