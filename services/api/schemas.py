from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID

class OrderCreate(BaseModel):
    customer_name: str
    vehicle: str
    service_date: date

class OrderOut(BaseModel):
    id: UUID
    customer_name: str
    vehicle: str
    service_date: date
    status: str
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy -> Pydantic
