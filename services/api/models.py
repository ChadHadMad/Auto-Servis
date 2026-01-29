from sqlalchemy import Column, String, Date, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="customer")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    orders = relationship(
        "Order",
        back_populates="customer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    vehicles = relationship(
        "Vehicle",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner = relationship("User", back_populates="vehicles")

    make = Column(String, nullable=False)
    model = Column(String, nullable=False)
    plate = Column(String, nullable=False)
    year = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    customer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    customer = relationship("User", back_populates="orders")

    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_ref = relationship("Vehicle")

    customer_name = Column(String, nullable=False)
    vehicle = Column(String, nullable=False)
    service_date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="scheduled")

    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
