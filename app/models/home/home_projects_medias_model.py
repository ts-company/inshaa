from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from app.database import Base

class ProjectMedia(Base):
    __tablename__ = "cv_projects_medias"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("cv_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    public_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)