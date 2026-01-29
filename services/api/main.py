import os
import time
from datetime import date as date_type
from uuid import UUID

from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import crud
from db import engine, get_db
from models import Base
from schemas import (
    RegisterIn, LoginIn, TokenOut, UserOut, RoleUpdateIn,
    VehicleCreate, VehicleOut,  AdminVehicleCreate,
    OrderCreate, OrderOut, AdminOrderCreate
)
from auth import hash_password, verify_password, create_access_token, get_current_user, require_role
from mq import publish_status_event
from cache import get_json, set_json, delete

app = FastAPI()
Instrumentator().instrument(app).expose(app)

CACHE_KEY_ALL_ORDERS = "orders:all"
CACHE_TTL_SECONDS = 30

ALLOWED_STATUSES = {"scheduled", "waiting", "on_lift", "done", "cancelled"}


@app.on_event("startup")
def on_startup():
    for _ in range(30):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception:
            time.sleep(1)

    Base.metadata.create_all(bind=engine)

    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@autoservis.com")
    admin_pass = os.getenv("SEED_ADMIN_PASSWORD", "admin123")

    db = next(get_db())
    try:
        existing = crud.get_user_by_email(db, admin_email)
        if not existing:
            try:
                crud.create_user(db, admin_email, hash_password(admin_pass), role="admin")
                print("[startup] Admin user created")
            except IntegrityError:
                db.rollback()
                print("[startup] Admin already created by another instance, skipping seed")
        else:
            print("[startup] Admin already exists, skipping seed")
    finally:
        db.close()


@app.get("/health")
def health():
    api_name = os.getenv("API_NAME", "unknown")
    return {"status": "ok", "api": api_name}


# ---------- AUTH ----------
@app.post("/auth/register", response_model=UserOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    user = crud.create_user(
        db,
        payload.email,
        hash_password(payload.password),
        role="customer",
        name=payload.name
    )
    return user


@app.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, role=user.role)


@app.get("/auth/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return user


# ---------- VEHICLES ----------
@app.post("/vehicles", response_model=VehicleOut)
def add_vehicle(payload: VehicleCreate, db: Session = Depends(get_db), user=Depends(require_role("customer"))):
    return crud.create_vehicle(db, user.id, payload.make, payload.model, payload.plate, payload.year)


@app.get("/vehicles", response_model=list[VehicleOut])
def my_vehicles(db: Session = Depends(get_db), user=Depends(require_role("customer"))):
    return crud.list_vehicles(db, user.id)


@app.delete("/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: UUID, db: Session = Depends(get_db), user=Depends(require_role("customer"))):
    ok = crud.delete_vehicle(db, user.id, vehicle_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"ok": True}

# ---------- ADMIN ----------
@app.get("/admin/users", response_model=list[UserOut])
def admin_list_users(db: Session = Depends(get_db), admin=Depends(require_role("admin"))):
    return crud.list_users(db)


@app.put("/admin/users/{user_id}/role", response_model=UserOut)
def admin_set_role(
    user_id: UUID,
    payload: RoleUpdateIn,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    if payload.role not in {"customer", "mechanic", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    if str(admin.id) == str(user_id) and payload.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot change your own admin role")

    updated = crud.update_user_role(db, user_id, payload.role)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@app.delete("/admin/users/{user_id}")
def admin_delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    if str(admin.id) == str(user_id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    ok = crud.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")

    delete(CACHE_KEY_ALL_ORDERS)
    return {"ok": True}


@app.post("/admin/orders", response_model=OrderOut)
def admin_create_order(
    payload: AdminOrderCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    if payload.service_date < date_type.today():
        raise HTTPException(status_code=400, detail="Service date cannot be in the past")

    customer = crud.get_user_by_email(db, payload.customer_email)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_name = customer.name or customer.email

    vehicle_text = payload.vehicle
    vehicle_id = None

    if payload.vehicle_id is not None:
        v = crud.get_vehicle_by_id(db, payload.vehicle_id)
        if not v or str(v.user_id) != str(customer.id):
            raise HTTPException(status_code=404, detail="Vehicle not found for this customer")

        vehicle_id = v.id
        vehicle_text = f"{v.make} {v.model}" + (f" ({v.plate})" if v.plate else "") + (f" - {v.year}" if v.year else "")

    if not vehicle_text:
        raise HTTPException(status_code=400, detail="Provide vehicle_id or vehicle")

    created = crud.create_order(
        db,
        customer.id,
        customer_name,
        vehicle_text,
        payload.service_date,
        notes=payload.notes,
        vehicle_id=vehicle_id,
    )

    delete(CACHE_KEY_ALL_ORDERS)
    return created

@app.get("/admin/vehicles", response_model=list[VehicleOut])
def admin_list_customer_vehicles(
    customer_email: str,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    customer = crud.get_user_by_email(db, customer_email)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return crud.list_vehicles(db, customer.id)


@app.post("/admin/vehicles", response_model=VehicleOut)
def admin_add_vehicle_for_customer(
    payload: AdminVehicleCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    customer = crud.get_user_by_email(db, payload.customer_email)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if not payload.plate or not payload.plate.strip():
        raise HTTPException(status_code=400, detail="Plate is required")

    return crud.create_vehicle(
        db,
        customer.id,
        payload.make.strip(),
        payload.model.strip(),
        payload.plate.strip(),
        payload.year,
    )


# ---------- ORDERS ----------
@app.post("/orders", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db), user=Depends(require_role("customer"))):
    if payload.service_date < date_type.today():
        raise HTTPException(status_code=400, detail="Service date cannot be in the past")

    v = crud.get_vehicle_by_id(db, payload.vehicle_id)
    if not v or str(v.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Vehicle not found")

    customer_name = user.name or user.email
    vehicle_text = f"{v.make} {v.model}" + (f" ({v.plate})" if v.plate else "") + (f" - {v.year}" if v.year else "")

    created = crud.create_order(
        db,
        user.id,
        customer_name,
        vehicle_text,
        payload.service_date,
        notes=payload.notes,
        vehicle_id=v.id,
    )

    delete(CACHE_KEY_ALL_ORDERS)
    return created


@app.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: str | None = Query(default=None),
    service_date: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    scope_customer_id = user.id if user.role == "customer" else None

    if status is None and service_date is None and scope_customer_id is None:
        cached = get_json(CACHE_KEY_ALL_ORDERS)
        if cached is not None:
            return cached

        result = crud.get_orders(db, customer_id=None)
        payload = [OrderOut.model_validate(o).model_dump() for o in result]
        set_json(CACHE_KEY_ALL_ORDERS, payload, ttl=CACHE_TTL_SECONDS)
        return payload

    return crud.get_orders(db, status=status, service_date=service_date, customer_id=scope_customer_id)


@app.put("/orders/{order_id}/status", response_model=OrderOut)
def update_status(
    order_id: UUID,
    status: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("mechanic", "admin")),
):
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    updated = crud.update_order_status(db, order_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")

    publish_status_event(
        {
            "event": "order_status_changed",
            "order_id": str(updated.id),
            "new_status": updated.status,
            "service_date": str(updated.service_date),
            "customer_name": updated.customer_name,
            "vehicle": updated.vehicle,
        }
    )

    delete(CACHE_KEY_ALL_ORDERS)
    return updated


@app.delete("/orders/{order_id}", response_model=OrderOut)
def cancel_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    order = crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if user.role == "customer" and str(order.customer_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    cancelled = crud.cancel_order(db, order_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Order not found")

    publish_status_event(
        {
            "event": "order_status_changed",
            "order_id": str(cancelled.id),
            "new_status": cancelled.status,
            "service_date": str(cancelled.service_date),
            "customer_name": cancelled.customer_name,
            "vehicle": cancelled.vehicle,
        }
    )

    delete(CACHE_KEY_ALL_ORDERS)
    return cancelled
