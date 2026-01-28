import os
import time
from datetime import date
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
    OrderCreate, OrderOut,
)

from auth import hash_password, verify_password, create_access_token, get_current_user, require_role

from mq import publish_status_event
from cache import get_json, set_json, delete


app = FastAPI()

Instrumentator().instrument(app).expose(app)

CACHE_KEY_ALL_ORDERS = "orders:all"
CACHE_TTL_SECONDS = 30


@app.on_event("startup")
def on_startup():
    for _ in range(30):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception:
            time.sleep(1)

    try:
        Base.metadata.create_all(bind=engine)
    except IntegrityError:
        pass

    admin_email = os.getenv("ADMIN_EMAIL", "admin@autoservis.com")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")

    db = next(get_db())
    try:
        existing = crud.get_user_by_email(db, admin_email)
        if not existing:
            crud.create_user(
                db,
                admin_email,
                hash_password(admin_pass),
                role="admin"
            )
            print("[startup] Admin user created")
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
    user = crud.create_user(db, payload.email, hash_password(payload.password), role="customer")
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


# ---------- ORDERS ----------
@app.post("/orders", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db), user=Depends(require_role("customer"))):
    created = crud.create_order(db, user.id, payload.customer_name, payload.vehicle, payload.service_date)
    delete(CACHE_KEY_ALL_ORDERS)
    return created


@app.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: str | None = Query(default=None),
    service_date: date | None = Query(default=None),
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
