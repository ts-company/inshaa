from sqlalchemy import Column, Integer, String
from app.database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False)
    phone_number = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    picture_id = Column(String, nullable=True)
    cv_id = Column(String, nullable=True)