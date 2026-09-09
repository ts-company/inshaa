from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from app.database import Base

class ExtractTaxes(Base):
    __tablename__ = "extract_taxes"

    id = Column(Integer, primary_key=True, index=True)
    extract_id = Column(Integer, ForeignKey("extracts.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 4), nullable=False)