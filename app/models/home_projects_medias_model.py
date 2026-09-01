from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class ProjectMedia(Base):
    __tablename__ = "project_medias"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False)