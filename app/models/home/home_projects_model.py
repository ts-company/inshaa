from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)