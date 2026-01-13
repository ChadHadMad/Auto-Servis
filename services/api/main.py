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
