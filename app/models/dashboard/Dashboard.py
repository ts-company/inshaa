import gzip
import json
from sqlalchemy import Integer, Column, Date, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import LargeBinary, TypeDecorator
from app.database import Base


class CompressedJSON(TypeDecorator):
    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        payload = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return gzip.compress(payload, compresslevel=9)

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        return json.loads(gzip.decompress(value).decode("utf-8"))


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, nullable=False)
    filename = Column(Text)
    uploaded_at = Column(DateTime(timezone=True), nullable=False)
    xer_version = Column(Text)
    export_date = Column(Date)
    export_type = Column(Text)
    project_name = Column(Text)
    export_user = Column(Text)
    database_name = Column(Text)
    currency = Column(Text)
    row_counts = Column(JSONB)
    data = Column(CompressedJSON, nullable=False)