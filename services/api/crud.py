def get_orders(db: Session, status, service_date):
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)

    if service_date:
        query = query.filter(Order.service_date == service_date)

    return query.all()