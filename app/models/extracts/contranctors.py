from sqlalchemy import Column, Integer, String
from app.database import Base

class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    code = Column(String(200), nullable=False, unique=True)