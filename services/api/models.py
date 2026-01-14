from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    customer_name = Column(String, nullable=False)
    vehicle = Column(String, nullable=False)

    service_date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="created")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
