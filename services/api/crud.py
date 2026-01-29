from datetime import date
from sqlalchemy.orm import Session
from uuid import UUID as UUIDType

from models import Order, User


# ---------- USERS ----------
def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: UUIDType) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, email: str, password_hash: str, role: str = "customer", name: str | None = None) -> User:
    user = User(email=email, password_hash=password_hash, role=role, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def update_user_role(db: Session, user_id: UUIDType, new_role: str) -> User | None:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.role = new_role
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: UUIDType) -> bool:
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


# ---------- ORDERS ----------
def create_order(db: Session, customer_id: UUIDType, customer_name: str, vehicle: str, service_date: date, notes: str | None = None) -> Order:
    order = Order(
        customer_id=customer_id,
        customer_name=customer_name,
        vehicle=vehicle,
        service_date=service_date,
        status="created",
        notes=notes,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_orders(
    db: Session,
    status: str | None = None,
    service_date: date | None = None,
    customer_id: UUIDType | None = None,
) -> list[Order]:
    query = db.query(Order)

    if customer_id is not None:
        query = query.filter(Order.customer_id == customer_id)

    if status:
        query = query.filter(Order.status == status)

    if service_date:
        query = query.filter(Order.service_date == service_date)

    return query.order_by(Order.created_at.desc()).all()


def get_order_by_id(db: Session, order_id):
    return db.query(Order).filter(Order.id == order_id).first()


def update_order_status(db: Session, order_id, new_status: str) -> Order | None:
    order = get_order_by_id(db, order_id)
    if not order:
        return None
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order_id) -> Order | None:
    return update_order_status(db, order_id, "cancelled")
