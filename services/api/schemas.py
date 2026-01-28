from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from uuid import UUID


# ---------- AUTH ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str

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
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class RoleUpdateIn(BaseModel):
    role: str

# ---------- ORDERS ----------
class OrderCreate(BaseModel):
    customer_name: str
    vehicle: str
    service_date: date

class OrderOut(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str
    vehicle: str
    service_date: date
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
