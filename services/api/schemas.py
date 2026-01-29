from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from uuid import UUID


# ---------- AUTH ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    name: str | None = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class RoleUpdateIn(BaseModel):
    role: str

# ---------- VEHICLES ----------
class VehicleCreate(BaseModel):
    make: str
    model: str
    plate: str
    year: int | None = None

class VehicleOut(BaseModel):
    id: UUID
    user_id: UUID
    make: str
    model: str
    plate: str | None = None
    year: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True

class AdminVehicleCreate(BaseModel):
    customer_email: EmailStr
    make: str
    model: str
    plate: str
    year: int | None = None

# ---------- ORDERS ----------
class OrderCreate(BaseModel):
    vehicle_id: UUID
    service_date: date
    notes: str | None = None

class AdminOrderCreate(BaseModel):
    customer_email: EmailStr
    vehicle_id: UUID | None = None
    vehicle: str | None = None
    service_date: date
    notes: str | None = None

class OrderOut(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str
    vehicle: str
    vehicle_id: UUID | None = None
    service_date: date
    status: str
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
