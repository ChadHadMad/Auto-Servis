<<<<<<< HEAD
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from uuid import UUID
from sqlalchemy import text
import time
from db import engine, get_db
from models import Base
from schemas import OrderCreate, OrderOut
import crud

app = FastAPI()

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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/orders", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    return crud.create_order(db, payload.customer_name, payload.vehicle, payload.service_date)

@app.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: str | None = Query(default=None),
    service_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return crud.get_orders(db, status=status, service_date=service_date)

@app.put("/orders/{order_id}/status", response_model=OrderOut)
def update_status(order_id: UUID, status: str, db: Session = Depends(get_db)):
    updated = crud.update_order_status(db, order_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")
    return updated

@app.delete("/orders/{order_id}", response_model=OrderOut)
def cancel_order(order_id: UUID, db: Session = Depends(get_db)):
    cancelled = crud.cancel_order(db, order_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Order not found")
    return cancelled
=======
import os
from fastapi import FastAPI, Query, Depends
from datetime import date as Date
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from enum import Enum
from uuid import UUID

from db import get_db
from crud import get_orders

app = FastAPI()


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class OrderCreate(BaseModel):
    customer_name: str
    vehicle: str
    status: OrderStatus
    service_date: Date


class OrderOut(BaseModel):
    id: UUID
    status: OrderStatus
    service_date: Date

    class Config:
        from_attributes = True


@app.get("/health")
def health():
    api_name = os.getenv("API_NAME", "unknown")
    return {"status": "ok", "api": api_name}


@app.post("/orders")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    return {"msg": "order created"} 


@app.get("/orders", response_model=List[OrderOut])
def list_orders(
    status: str | None = Query(default=None),
    service_date: Date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_orders(db, status, service_date)
>>>>>>> 4872ed1 (Popravljen load balancing i startanje API1 i API2 kada se pokrene docker)
