from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from app.database import Base

class ProjectMedia(Base):
    __tablename__ = "project_medias"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    public_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)