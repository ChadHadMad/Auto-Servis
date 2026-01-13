from sqlalchemy.orm import Session
from datetime import date
from models import Order

def create_order(db: Session, customer_name: str, vehicle: str, service_date: date):
    order = Order(
        customer_name=customer_name,
        vehicle=vehicle,
        service_date=service_date,
        status="created",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def get_orders(db: Session, status: str | None = None, service_date: date | None = None):
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)

    if service_date:
        query = query.filter(Order.service_date == service_date)

    return query.order_by(Order.created_at.desc()).all()

def get_order_by_id(db: Session, order_id):
    return db.query(Order).filter(Order.id == order_id).first()

def update_order_status(db: Session, order_id, new_status: str):
    order = get_order_by_id(db, order_id)
    if not order:
        return None
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order

def cancel_order(db: Session, order_id):
    # po planu: "otkazati narudžbu" — najčešće je bolje set status nego delete
    return update_order_status(db, order_id, "cancelled")
