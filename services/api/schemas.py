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

# ---------- ORDERS ----------
class OrderCreate(BaseModel):
    vehicle: str
    service_date: date
    notes: str | None = None

class OrderOut(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str
    vehicle: str
    service_date: date
    status: str
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
