import pytest
from fastapi.testclient import TestClient

from app import api
from app.api import app


@pytest.fixture(autouse=True)
def fixtures_limpios():
    """Cada prueba parte de los 16 pedidos en DRAFT."""
    api.reset_orders()
    yield
    api.reset_orders()


@pytest.fixture
def client():
    return TestClient(app)


def test_get_pedido(client):
    r = client.get("/orders/O001")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "DRAFT"
    assert body["units"] == 4
    assert body["total"] == "2100.00"
    assert body["discount_rate"] == "0.10"


def test_get_pedido_inexistente_404(client):
    assert client.get("/orders/NOPE").status_code == 404


def test_confirmar_inexistente_404(client):
    assert client.post("/orders/NOPE/confirm").status_code == 404


def test_confirmar_exito(client):
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 200
    assert r.json() == {"id": "O013", "status": "CONFIRMED"}


def test_confirmar_dos_veces_409(client):
    assert client.post("/orders/O013/confirm").status_code == 200
    assert client.post("/orders/O013/confirm").status_code == 409
    assert client.get("/orders/O013").json()["events"] == ["OrderConfirmed"]


def test_confirmar_sin_articulos_422(client):
    assert client.post("/orders/O007/confirm").status_code == 422


def test_confirmar_cliente_inactivo_422(client):
    assert client.post("/orders/O003/confirm").status_code == 422


def test_envio_sin_guia_422(client):
    client.post("/orders/O012/confirm")
    r = client.post("/orders/O012/ship", json={"tracking_number": ""})
    assert r.status_code == 422
    assert client.get("/orders/O012").json()["status"] == "CONFIRMED"


def test_envio_con_guia(client):
    client.post("/orders/O012/confirm")
    r = client.post("/orders/O012/ship", json={"tracking_number": "G-100"})
    assert r.status_code == 200 and r.json()["status"] == "SHIPPED"


def test_cancelar_desde_shipped_409(client):
    client.post("/orders/O014/confirm")
    client.post("/orders/O014/ship", json={"tracking_number": "G-1"})
    r = client.post("/orders/O014/cancel", json={"reason": "tarde"})
    assert r.status_code == 409


def test_cancelar_exito(client):
    client.post("/orders/O013/confirm")
    r = client.post("/orders/O013/cancel", json={"reason": "ya no lo quiere"})
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


def test_entregar_y_devolver(client):
    for pid in ("O016", "O015"):
        client.post(f"/orders/{pid}/confirm")
        client.post(f"/orders/{pid}/ship", json={"tracking_number": "G"})
    assert client.post("/orders/O016/deliver").json()["status"] == "DELIVERED"
    assert client.post("/orders/O015/return").json()["status"] == "RETURNED"


def test_entregar_desde_draft_409(client):
    assert client.post("/orders/O013/deliver").status_code == 409


def test_agregar_item_201(client):
    r = client.post("/orders/O013/items", json={"sku": "SKU003", "quantity": 2})
    assert r.status_code == 201
    assert r.json()["units"] == 3


def test_agregar_item_excede_20_unidades_422(client):
    r = client.post("/orders/O009/items", json={"sku": "SKU003", "quantity": 2})
    assert r.status_code == 422
    assert client.get("/orders/O009").json()["units"] == 19


def test_agregar_item_a_pedido_confirmado_409(client):
    client.post("/orders/O013/confirm")
    r = client.post("/orders/O013/items", json={"sku": "SKU003", "quantity": 1})
    assert r.status_code == 409


def test_agregar_sku_inexistente_404(client):
    r = client.post("/orders/O013/items", json={"sku": "XXX", "quantity": 1})
    assert r.status_code == 404


def test_openapi_y_docs_disponibles(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
