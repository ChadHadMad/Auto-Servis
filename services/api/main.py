from fastapi import FastAPI
from models import Order

app = FastAPI()

@app.post("/orders")
def create_order(order: dict):
    return {"msg": "order created"}

@app.get("/orders")
def list_orders():
    return []

@app.put("/orders/{id}/status")
def update_status(id: str, status: str):
    return {"msg": "status updated"}

@app.delete("/orders/{id}")
def cancel_order(id: str):
    return {"msg": "order cancelled"}
