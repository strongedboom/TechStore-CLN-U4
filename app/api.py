"""API REST de TechStore U4 (FastAPI).

Los endpoints solo buscan el pedido, llaman al método de Order y traducen
las excepciones del dominio a códigos HTTP. Las reglas de negocio viven en
app/domain.py y app/specifications.py, no aquí.

Mapeo de errores:
  404 -> el pedido no existe
  409 -> transición de estado no permitida (InvalidOrderTransition)
  422 -> datos inválidos o regla incumplida (InvalidOrderData, OrderItemLimitExceeded)
"""
from decimal import Decimal, InvalidOperation

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cargar_csv import load_fixture, rows
from app.domain import (
    InvalidOrderData,
    InvalidOrderTransition,
    Money,
    OrderItem,
    OrderItemLimitExceeded,
)
from app.specifications import discount_rate

app = FastAPI(title="TechStore U4")

# Repositorio en memoria: se reinicia al reiniciar el servidor.
orders = load_fixture()


def reset_orders():
    """Vuelve a cargar los fixtures (útil para pruebas y para Swagger)."""
    orders.clear()
    orders.update(load_fixture())


class ShipRequest(BaseModel):
    tracking_number: str = ""


class CancelRequest(BaseModel):
    reason: str = ""


class ItemRequest(BaseModel):
    sku: str
    quantity: int


def _get_order(order_id: str):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="No existe")
    return order


def _run(action, *args):
    """Ejecuta una operación del dominio y traduce sus excepciones a HTTP."""
    try:
        action(*args)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (InvalidOrderData, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _serialize(order):
    rate = discount_rate(order)
    total = order.total.amount
    return {
        "id": order.id,
        "customer_id": order.customer.id,
        "status": order.status.value,
        "units": order.units,
        "total": str(total),
        "discount_rate": str(rate),
        "total_with_discount": str(total - total * rate),
        "currency": order.total.currency,
        "tracking_number": order.tracking_number,
        "items": [
            {
                "sku": i.sku,
                "quantity": i.quantity,
                "unit_price": str(i.unit_price.amount),
                "subtotal": str(i.subtotal.amount),
            }
            for i in order.items
        ],
        "events": [e.name for e in order.events],
    }


@app.get("/orders")
def list_orders():
    return [
        {"id": o.id, "status": o.status.value, "units": o.units, "total": str(o.total.amount)}
        for o in orders.values()
    ]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    return _serialize(_get_order(order_id))


@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = _get_order(order_id)
    _run(order.confirm)
    return {"id": order.id, "status": order.status.value}


@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, body: ShipRequest):
    order = _get_order(order_id)
    _run(order.ship, body.tracking_number)
    return {"id": order.id, "status": order.status.value,
            "tracking_number": order.tracking_number}


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelRequest):
    order = _get_order(order_id)
    _run(order.cancel, body.reason)
    return {"id": order.id, "status": order.status.value}


@app.post("/orders/{order_id}/deliver")
def deliver_order(order_id: str):
    order = _get_order(order_id)
    _run(order.deliver)
    return {"id": order.id, "status": order.status.value}


@app.post("/orders/{order_id}/return")
def return_order(order_id: str):
    order = _get_order(order_id)
    _run(order.return_order)
    return {"id": order.id, "status": order.status.value}


@app.post("/orders/{order_id}/items", status_code=201)
def add_item(order_id: str, body: ItemRequest):
    """Ampliación opcional: agrega un SKU del catálogo (el precio sale de productos.csv)."""
    order = _get_order(order_id)
    catalog = {r["sku"]: r["precio_mxn"] for r in rows("productos.csv")}
    if body.sku not in catalog:
        raise HTTPException(status_code=404, detail="SKU inexistente")
    try:
        price = Money(Decimal(catalog[body.sku]))
    except InvalidOperation:  # pragma: no cover - catálogo corrupto
        raise HTTPException(status_code=422, detail="Precio inválido en catálogo")

    def _add():
        order.add_item(OrderItem(body.sku, body.quantity, price))

    _run(_add)
    return _serialize(order)
