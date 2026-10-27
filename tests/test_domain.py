from decimal import Decimal

import pytest

from app.domain import (
    Customer,
    InvalidOrderData,
    InvalidOrderTransition,
    Money,
    Order,
    OrderItem,
    OrderItemLimitExceeded,
    OrderStatus,
)
from app.specifications import (
    ActivePromotionSpec,
    MinimumAmountSpec,
    MinimumUnitsSpec,
    VIPCustomerSpec,
    any_discount,
    discount_rate,
    five_percent,
    ten_percent,
)
from cargar_csv import load_fixture


@pytest.fixture
def orders():
    return load_fixture()


def names(order):
    return [e.name for e in order.events]


# ---------- Value Objects ----------
def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))


def test_money_no_finito():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("NaN"))


def test_money_add_devuelve_objeto_nuevo():
    a, b = Money(Decimal("10")), Money(Decimal("5"))
    c = a.add(b)
    assert c.amount == Decimal("15") and a.amount == Decimal("10")


def test_money_add_monedas_distintas():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("1"), "MXN").add(Money(Decimal("1"), "USD"))


def test_money_es_inmutable():
    m = Money(Decimal("1"))
    with pytest.raises(Exception):
        m.amount = Decimal("2")


@pytest.mark.parametrize("qty", [0, -1])
def test_orderitem_cantidad_invalida(qty):
    with pytest.raises(InvalidOrderData):
        OrderItem("SKU001", qty, Money(Decimal("10")))


def test_orderitem_sku_vacio():
    with pytest.raises(InvalidOrderData):
        OrderItem("  ", 1, Money(Decimal("10")))


# ---------- Carga y totales ----------
def test_se_cargan_16_pedidos_en_draft(orders):
    assert len(orders) == 16
    assert all(o.status == OrderStatus.DRAFT for o in orders.values())


def test_pedido_o001_inicia_draft(orders):
    assert orders["O001"].status.value == "DRAFT"
    assert orders["O001"].units == 4
    assert orders["O001"].total.amount == Decimal("2100.00")


@pytest.mark.parametrize(
    "pid,units,total",
    [("O001", 4, "2100.00"), ("O006", 1, "18000.00"), ("O010", 2, "500.00")],
)
def test_actividad_corta_totales(orders, pid, units, total):
    assert orders[pid].units == units
    assert orders[pid].total.amount == Decimal(total)


# ---------- Límite de 20 unidades ----------
def test_20_unidades_exactas_permitidas(orders):
    assert orders["O008"].units == 20


def test_21_unidades_rechazadas_sin_modificar_items(orders):
    o = orders["O009"]
    antes = (len(o.items), o.units)
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU003", 2, Money(Decimal("120"))))
    assert (len(o.items), o.units) == antes


def test_limite_cuenta_unidades_no_renglones():
    o = Order(Customer("C1"), "X1")
    for _ in range(5):  # 5 renglones de 4 unidades = 20 unidades
        o.add_item(OrderItem("SKU001", 4, Money(Decimal("1"))))
    assert len(o.items) == 5 and o.units == 20
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU001", 1, Money(Decimal("1"))))


def test_add_item_solo_en_draft(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.add_item(OrderItem("SKU001", 1, Money(Decimal("1"))))


def test_add_item_solo_mxn(orders):
    with pytest.raises(InvalidOrderData):
        orders["O013"].add_item(OrderItem("SKU001", 1, Money(Decimal("1"), "USD")))


# ---------- Specifications ----------
def test_descuento_vip_10(orders):
    assert ten_percent.is_satisfied_by(orders["O001"])
    assert discount_rate(orders["O001"]) == Decimal("0.10")


def test_descuento_alterno_5(orders):
    assert five_percent.is_satisfied_by(orders["O006"])
    assert not ten_percent.is_satisfied_by(orders["O006"])
    assert discount_rate(orders["O006"]) == Decimal("0.05")


def test_promocion_activa_excluye_descuento(orders):
    assert orders["O005"].has_promotion
    assert not any_discount.is_satisfied_by(orders["O005"])
    assert discount_rate(orders["O005"]) == Decimal("0")


def test_umbral_estricto_500(orders):
    assert orders["O010"].total.amount == Decimal("500.00")
    assert not MinimumAmountSpec(Decimal("500")).is_satisfied_by(orders["O010"])
    assert discount_rate(orders["O010"]) == Decimal("0")


def test_vip_con_3_unidades_no_aplica(orders):
    assert orders["O011"].units == 3
    assert not MinimumUnitsSpec(4).is_satisfied_by(orders["O011"])
    assert discount_rate(orders["O011"]) == Decimal("0")


def test_no_vip_sin_descuento(orders):
    assert not VIPCustomerSpec().is_satisfied_by(orders["O002"])
    assert discount_rate(orders["O002"]) == Decimal("0")


def test_composicion_and_or_not(orders):
    o = orders["O005"]  # VIP, promo activa
    assert (VIPCustomerSpec() & ActivePromotionSpec()).is_satisfied_by(o)
    assert (VIPCustomerSpec() | ~ActivePromotionSpec()).is_satisfied_by(o)
    assert not (~ActivePromotionSpec()).is_satisfied_by(o)


def test_prioridad_10_sobre_5():
    o = Order(Customer("V", is_vip=True), "P1")
    o.add_item(OrderItem("SKU005", 2, Money(Decimal("3200"))))  # 6400, 2 unidades
    assert discount_rate(o) == Decimal("0.05")  # <4 unidades: solo 5 %
    o2 = Order(Customer("V", is_vip=True), "P2")
    o2.add_item(OrderItem("SKU005", 4, Money(Decimal("3200"))))  # 12800, 4 unidades
    assert discount_rate(o2) == Decimal("0.10")  # ambas aplican: gana 10 %


def test_specification_no_modifica_pedido(orders):
    o = orders["O001"]
    antes = (o.status, o.units, o.total.amount, list(o.events))
    discount_rate(o)
    assert (o.status, o.units, o.total.amount, list(o.events)) == antes


# ---------- Máquina de estados y eventos ----------
def test_confirmar_cliente_inactivo(orders):
    o = orders["O003"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT and o.events == []


def test_confirmar_pedido_vacio(orders):
    o = orders["O007"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT and o.events == []


def test_confirmacion_doble(orders):
    o = orders["O013"]
    o.confirm()
    assert o.status == OrderStatus.CONFIRMED and names(o) == ["OrderConfirmed"]
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert names(o) == ["OrderConfirmed"]


@pytest.mark.parametrize("guia", ["", "   ", None])
def test_envio_sin_guia(orders, guia):
    o = orders["O012"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.ship(guia)
    assert o.status == OrderStatus.CONFIRMED and names(o) == ["OrderConfirmed"]


def test_envio_desde_draft_no_permitido(orders):
    with pytest.raises(InvalidOrderTransition):
        orders["O012"].ship("G1")


def test_cancelacion_desde_confirmed(orders):
    o = orders["O013"]
    o.confirm()
    o.cancel("Cliente lo solicitó")
    assert o.status == OrderStatus.CANCELLED
    assert names(o) == ["OrderConfirmed", "OrderCancelled"]


def test_cancelacion_sin_motivo(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.cancel("  ")
    assert o.status == OrderStatus.CONFIRMED


def test_cancelacion_desde_shipped_rechazada(orders):
    o = orders["O014"]
    o.confirm()
    o.ship("GUIA-1")
    with pytest.raises(InvalidOrderTransition):
        o.cancel("tarde")
    assert o.status == OrderStatus.SHIPPED
    assert names(o) == ["OrderConfirmed", "OrderShipped"]


def test_flujo_entrega(orders):
    o = orders["O016"]
    o.confirm()
    o.ship("GUIA-2")
    o.deliver()
    assert o.status == OrderStatus.DELIVERED
    assert names(o) == ["OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_flujo_devolucion(orders):
    o = orders["O015"]
    o.confirm()
    o.ship("GUIA-3")
    o.return_order()
    assert o.status == OrderStatus.RETURNED
    assert names(o) == ["OrderConfirmed", "OrderShipped", "OrderReturned"]


@pytest.mark.parametrize("metodo", ["deliver", "return_order"])
def test_entrega_y_devolucion_exigen_shipped(orders, metodo):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        getattr(o, metodo)()
    assert o.status == OrderStatus.CONFIRMED


def test_estados_finales_no_aceptan_mas_transiciones(orders):
    o = orders["O016"]
    o.confirm()
    o.ship("G")
    o.deliver()
    for op in (o.confirm, o.deliver, o.return_order, lambda: o.ship("G"),
               lambda: o.cancel("x")):
        with pytest.raises(InvalidOrderTransition):
            op()
    assert len(o.events) == 3


def test_eventos_incluyen_id_y_fecha_utc(orders):
    o = orders["O013"]
    o.confirm()
    ev = o.events[0]
    assert ev.order_id == "O013" and ev.occurred_at.tzinfo is not None
