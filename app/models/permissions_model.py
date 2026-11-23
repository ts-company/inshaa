from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey
from app.database import Base

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "type", name="unique_user_permission"),
    )