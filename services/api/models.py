from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
<<<<<<< HEAD
    customer_name = Column(String, nullable=False)
    vehicle = Column(String, nullable=False)
    service_date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="created")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
=======

    customer_name = Column(String(255), nullable=False)
    vehicle = Column(String(100), nullable=False)

    service_date = Column(Date, nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
>>>>>>> 4872ed1 (Popravljen load balancing i startanje API1 i API2 kada se pokrene docker)
