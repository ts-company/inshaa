from sqlalchemy import Column, Integer, String
from app.database import Base

class CvCategory(Base):
    __tablename__ = "cv_categories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50), nullable=False)