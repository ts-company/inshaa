from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    code = Column(String(200), nullable=False, unique=True)